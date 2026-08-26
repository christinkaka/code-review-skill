# 代码评审报告（Agent Alpha）

**评审日期**: 2026-08-13
**评审项目**: prisma/prisma (test-prisma 仓库)
**编程语言**: TypeScript / Node.js（Prisma ORM 8 示例 + MongoDB Contract 示例）
**评审范围**: 4 个文件
**评审维度**: 13 个

---

## 评审任务说明

本评审依据 V8（多语言版）标准化评审指令，针对指定 4 个文件以及与之强耦合的部署/配置上下文（Cloudflare Worker、`docker-compose.yml`、`.env.example`、`wrangler.jsonc`、`global-setup.ts`）进行独立安全评审。评审重点为：Prisma `$queryRaw` / `$executeRaw` / `fns.raw` 模板字符串、数据库连接 URL 安全、Schema 与 Seed 中的 SQL、Cloudflare Worker 部署配置。MD5/SHA1 必须单独报告；严重度遵循 V8 锁定规则；ORM 组合漏洞强制应用。

---

## 发现的问题

### 问题 1：spawnSync `--db` 参数接收未受信任的连接 URL（命令注入向量）
- **文件**: `examples/prisma-8-cloudflare-worker/scripts/setup-schema.ts`
- **行号**: 12、22
- **严重度**: HIGH
- **类型**: CommandInjection
- **描述**: 该脚本从环境变量 `WRANGLER_HYPERDRIVE_LOCAL_CONNECTION_STRING_HYPERDRIVE` 或 `DATABASE_URL` 读取数据库 URL，然后将其作为命令行参数（`spawnSync('pnpm', [..., '--db', url, '--yes'])`）传递给子进程。`spawnSync` 第二个参数为数组形式时本不会触发 shell 解析，但若 `url` 字符串以 `--` 开头（例如 `url = '--some-flag'`），Prisma CLI 将把它当作命令行 flag 解析，从而实现「参数注入」，这是 V8 严重度锁定中的 **HIGH** 级风险（shell-like 参数注入）。此 URL 直接来源于 `.env`，而 `.env.example` 中含有占位符，因此当前示例无即时威胁，但若 `.env` 在生产中保留占位符或被替换为攻击者可控的 `.env`，则存在被滥用为 flag-injection 通道的风险。同时，由于 `--db` 传入的是连接字符串，下游可能将其直接拼接进 DDL/SQL 语句，存在次生 SQL 注入隐患。
- **代码片段**:
```typescript
const url = process.env[HYPERDRIVE_VAR] ?? process.env['DATABASE_URL'];
// ...
const result = spawnSync('pnpm', ['exec', 'prisma-next', 'db', 'init', '--db', url, '--yes'], {
  stdio: 'inherit',
});
```
- **修复建议**: 在调用 `spawnSync` 前对 `url` 进行格式校验（必须以 `postgres://` 或 `postgresql://` 开头，且不包含前导 `--`）；拒绝包含换行符或控制字符的 URL；同时将 `url` 通过环境变量（如 `DATABASE_URL=...`）而非命令行参数注入到子进程，避免 CLI flag 解析歧义。

### 问题 2：Worker 端点将 `userId`/`displayName` 拼接到 SQL 字符串字面量中（数据投毒 + 间接 XSS）
- **文件**: `examples/prisma-8-cloudflare-worker/src/worker.ts`
- **行号**: 54、63、73、86
- **严重度**: MEDIUM
- **类型**: SQLi / 数据完整性
- **描述**: `/tx/commit` 端点将 `userId`、`newDisplayName` 直接通过 Prisma 强类型 builder API 写入数据库（builder 会做参数化处理，本身不构成 SQL 注入）。但第 63 行 `title: \`Post written in tx for ${userId}\`` 把未净化的 `userId` 拼接进 title 字段并落库；下游若在前端渲染该 title，将造成存储型 XSS 风险。`/orm/posts` 端点同样将 `userId` 作为过滤条件直接传入 builder，但 builder 内部已参数化，不构成 SQL 注入；不过 `/tx/rollback`（第 86 行）硬编码 `alice@example.com` 作为 WHERE 谓词参数，对生产环境来说会污染数据。
- **代码片段**:
```typescript
const newDisplayName = url.searchParams.get('displayName') ?? 'Updated';
// ...
title: `Post written in tx for ${userId}`,
```
- **修复建议**: 写入数据库前对 `userId` 做格式校验（UUID 形态），对所有用户输入做 HTML/JS 转义或使用模板库的安全插值；title 字段由后端构造时不应直接拼接原始 `userId`，建议使用 `tx_id`（UUIDv4）与 `userId` 分离存储，避免日志/前端展示中出现可执行内容。

### 问题 3：Worker 端点缺乏认证与速率限制（认证/授权缺失）
- **文件**: `examples/prisma-8-cloudflare-worker/src/worker.ts`
- **行号**: 整个 `fetch` 函数（11-175）
- **严重度**: MEDIUM
- **类型**: Auth
- **描述**: 该 Cloudflare Worker 暴露的 `/sql/users`、`/orm/users`、`/orm/posts`、`/tx/commit`、`/tx/rollback`、`/cursor/large` 等端点全部无任何认证（无 Authorization header 校验、无 IP 白名单、无 Cloudflare Access）。任何能访问 Worker 公网 URL 的攻击者可执行任意查询、更新任意用户 displayName、强制事务回滚。V8 中速率限制缺失/禁用规则锁定为 MEDIUM，但此例甚至未配置速率限制框架，复合判定为 MEDIUM（认证+限流同时缺失）。该端点作为示例是合理的，但若照搬到生产将构成 CRITICAL。
- **代码片段**:
```typescript
async fetch(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);
  if (url.pathname === '/health') return Response.json({ ok: true });
  // 无 auth, 无 rate-limit
  if (url.pathname === '/sql/users') { /* ... */ }
```
- **修复建议**: 添加 Cloudflare Access / API Token 校验；对 `tx/*` 与写操作添加更严格的授权；在 Worker 上启用 WAF 速率限制规则；将示例 Worker 默认仅允许 localhost/miniflare 访问。

### 问题 4：本地 Postgres 默认凭据硬编码 `postgres:postgres`
- **文件**: `examples/prisma-8-cloudflare-worker/docker-compose.yml`、`examples/prisma-8-cloudflare-worker/.env.example`、`examples/paradedb-demo/docker-compose.yaml`
- **行号**: `docker-compose.yml` 14；`.env.example` 1
- **严重度**: MEDIUM（依据 V8 锁定：硬编码管理员凭据 = MEDIUM）
- **类型**: HardcodedSecret
- **描述**: Cloudflare Worker 示例的 docker-compose 与 `.env.example` 中明确使用 `POSTGRES_USER=postgres` / `POSTGRES_PASSWORD=postgres` 与连接字符串 `postgres://postgres:postgres@127.0.0.1:5433/...`。这是示例约定的弱凭据，便于本地启动；但 V8 规则要求「硬编码管理员凭据」必须报告为 MEDIUM（即便本地）。
- **代码片段**:
```yaml
environment:
  POSTGRES_USER: postgres
  POSTGRES_PASSWORD: postgres
  POSTGRES_DB: prisma_next_cloudflare_worker
```
```text
WRANGLER_HYPERDRIVE_LOCAL_CONNECTION_STRING_HYPERDRIVE="postgres://postgres:postgres@127.0.0.1:5433/prisma_next_cloudflare_worker"
```
- **修复建议**: 在 README 中明确警告「该凭据仅用于本地开发，生产请使用强密码+Secret Manager」；`.env.example` 可改为 `CHANGEME` 占位符而非直接写真实密码字符串，强制开发者生成自己的 `.env`。`postgres` 用户的密码应至少 16 位随机。

### 问题 5：MongoDB Contract `mongoQuery` 模板字符串未与 SQL 等价参数化（潜在注入面）
- **文件**: `projects/facade-import-surface-completion/manual-qa-reports/artefacts/S4-probe/probe-mongoquery.ts`
- **行号**: 60-78
- **严重度**: LOW
- **类型**: SQLi（适用 MongoDB Query Builder）
- **描述**: 该文件是 QA 探针，用于复现 TML-2633 中 facade `defineContract` 与 verbose `defineContract` 在 `mongoQuery<>` 类型推断上的差异，本身不接收运行时用户输入。所有过滤 (`f.status.eq('completed')`) 与聚合 (`acc.sum(f.amount)`) 均通过 builder 方法调用，builder 内部将操作符序列化为 MongoDB BSON，不会触发字符串拼接。但 `eq('completed')` 直接传字符串字面量，若误用者改写为字符串拼接，就会引入漏洞。当前实现是安全的，作为**代码质量**提醒记入。
- **代码片段**:
```typescript
const facadePlan = facadeQ
  .from('orders')
  .match((f) => f.status.eq('completed'))
  .group((f) => ({
    _id: f.department,
    total: acc.sum(f.amount),
    orderCount: acc.count(),
  }))
  .build();
```
- **修复建议**: 在 `mongoQuery` 与 builder 公开 API 上强制接受 `Expression<>` 节点，禁止 `string` 类型直接拼接到 MongoDB 查询字符串；现有设计已正确，保留即可。

### 问题 6：`slow-query-warning` 中间件将原始 SQL 写入日志（信息泄露）
- **文件**: `examples/prisma-8-demo/src/prisma/slow-query-warning.ts`
- **行号**: 30
- **严重度**: LOW
- **类型**: 硬编码/日志（接近 HardcodedSecret 与信息泄露）
- **描述**: 中间件 `afterQuery` 把 `plan.sql` 完整 SQL 写入结构化日志，包含表名、字段名与参数化占位符。在生产环境中，慢查询日志通常会被聚合到日志系统（Datadog/Loki/SIEM），如果日志收集未做访问控制，则可能泄露 schema 细节与查询模式，辅助攻击者进行 SQL 注入或基于 schema 的攻击。这是示例代码的合理演示，但应标记为安全提示。
- **代码片段**:
```typescript
details: {
  sql: plan.sql,
  rowCount: result.rowCount,
  latencyMs: result.latencyMs,
  // ...
},
```
- **修复建议**: 生产中应配置日志脱敏（不记录完整 SQL，仅记录表名与 latency）；或在中间件层提供 `redactSql` 选项以哈希 SQL 文本。

### 问题 7：V8 强制要求 — MD5/SHA1 单独报告
- **文件**: `packages/1-framework/1-core/framework-components/test/contract-snapshot-layout.test.ts`
- **行号**: 20
- **严重度**: LOW（V8 锁定：MD5/SHA1 用于任何场景 = LOW）
- **类型**: HardcodedSecret / 弱哈希
- **描述**: 测试文件中存在 `storageHashHex(\`md5:${'a'.repeat(64)}\`)` 用例。该用例是**主动测试 md5 前缀被拒绝**的断言（即它测试的是"md5 输入应当抛出"），并非使用 MD5 进行密码哈希或签名。但 V8 明确要求所有 MD5/SHA1 引用必须**单独报告为 LOW**，故此处独立登记。该文件不包含实际 MD5 加密操作，仅作为命名引用出现在测试断言中。
- **代码片段**:
```typescript
expect(() => storageHashHex(`md5:${'a'.repeat(64)}`)).toThrow();
```
- **修复建议**: 已符合 V8 规则要求（拒绝 MD5 哈希输入），无需变更。建议保留此测试覆盖，并在内部文档中将 MD5/SHA1 列入"禁用算法"清单。

### 问题 8：Worker 端点未配置 CORS / 安全中间件（HttpFirewall）
- **文件**: `examples/prisma-8-cloudflare-worker/src/worker.ts`
- **行号**: 11
- **严重度**: MEDIUM
- **类型**: HttpFirewall / CORS
- **描述**: 该 Worker 默认未设置 `Access-Control-Allow-Origin`，也未启用 Cloudflare WAF 的 `StrictHttpFirewall` 等价策略。若部署到公网，跨域请求无任何限制；同时没有 CSRF token / Origin 校验，写操作 (`/tx/commit`) 可被任意跨域来源 POST。这是 V8 中 CORS + CSRF 复合维度的体现，但因为是 Cloudflare Worker 而非 Express，未配置 CORS 反而等同于 `*` 默认策略（浏览器对简单 GET 允许），故按 MEDIUM 处理。
- **代码片段**:
```typescript
async fetch(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);
  // 无 CORS 头、无 Origin 校验
```
- **修复建议**: 在 Worker 中添加 `Access-Control-Allow-Origin` 白名单与 `Vary: Origin` 头；对写操作校验 `Origin` 与 `Sec-Fetch-Site: same-origin`；启用 Cloudflare WAF Bot Fight Mode / Rate Limiting Rules。

---

## 13 维度评审覆盖确认

| 维度 | 评审结果 | 发现问题 |
|------|----------|----------|
| 1. SQL 注入 (SQLi) | 已检查 | 问题 2（间接，MEDIUM）、问题 5（LOW，MongoDB builder） |
| 2. 跨站脚本 (XSS) | 已检查 | 问题 2（间接存储型，MEDIUM） |
| 3. XML 外部实体 (XXE) | 已检查 | 无问题（项目不解析 XML 输入） |
| 4. 路径穿越 (Path Traversal) | 已检查 | 无问题（4 个文件均无 `path.resolve` / `path.join` 用户输入拼接） |
| 5. 命令注入 (Command Injection) | 已检查 | 问题 1（HIGH，spawnSync flag-injection 风险） |
| 6. SSRF | 已检查 | 无问题（无 `URL.openConnection` / `fetch` 访问用户控制 URL） |
| 7. 文件上传/下载 | 已检查 | 无问题（4 个文件均无文件上传逻辑） |
| 8. 硬编码密钥/密码 | 已检查 | 问题 4（MEDIUM，postgres/postgres）、问题 6（LOW，日志 schema 泄露）、问题 7（LOW，MD5 命名引用） |
| 9. CSRF 保护 | 已检查 | 问题 8（MEDIUM，Worker 无 CSRF 防护） |
| 10. CORS 配置 | 已检查 | 问题 8（MEDIUM，Worker 无 CORS 配置） |
| 11. 认证授权 (Auth) | 已检查 | 问题 3（MEDIUM，Worker 无认证） |
| 12. 会话管理 (Session) | 已检查 | 无问题（4 个文件无 Cookie/Session 处理；Cloudflare Worker 无状态） |
| 13. HttpFirewall / 安全中间件 | 已检查 | 问题 8（MEDIUM，Worker 无 WAF/中间件） |

---

## 组合漏洞判定（V8 强制）

- **候选组合 1：CSRF 禁用 + CORS `*` + `allowCredentials=true` + Cookie 认证 → HIGH**
  - 不适用。本评审范围内无 Cookie 认证场景（Worker 无 Session），且无显式 CORS 配置；该组合规则不触发。
- **候选组合 2：CSRF 禁用 + 速率限制禁用 → MEDIUM**
  - 适用但已合并：Worker 端点同时缺失 CSRF 与速率限制，按合并规则计为 1 个问题（问题 8，MEDIUM）。

---

## 问题合并规则应用

- 问题 8（HttpFirewall + CORS + CSRF 复合）合并为 1 个问题：均源于 `worker.ts` 缺少统一安全中间件层。
- 问题 3（Auth）与问题 8 在 Worker 上互为补充，但因维度不同（11 vs 13）保持独立。
- `docker-compose.yml` 与 `.env.example` 中相同的 `postgres:postgres` 凭据算 1 个问题（问题 4）。

---

## 统计

| 严重度 | 数量 |
|--------|------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 4 |
| LOW | 3 |
| **总计** | **8** |

---

## 关键风险总结

1. **问题 1（HIGH）**：`setup-schema.ts` 通过 `spawnSync(..., url, ...)` 将数据库 URL 作为命令行参数传递，存在 CLI flag-injection 风险；URL 来源（`.env`）一旦不可信，将被滥用为参数注入通道。需在调用前校验 URL 前缀与 `--` 起始拒绝，或改用环境变量注入。

2. **问题 2（MEDIUM）**：Worker `/tx/commit` 端点将未净化 `userId` 拼接进 `title` 字段持久化，构成存储型 XSS / 数据投毒向量；虽 builder 已参数化防 SQL 注入，但下游展示链上的净化责任转移给了消费方。

3. **问题 3 + 8（MEDIUM）**：Cloudflare Worker 完全无认证、无 CORS、无 CSRF、无 WAF 策略，作为示例无问题，但任何照搬到生产的部署都会立刻变成 CRITICAL。组合漏洞规则已将 CSRF+速率限制合并处理。

4. **问题 4（MEDIUM）**：`postgres:postgres` 默认凭据虽属本地开发惯例，V8 仍要求按 MEDIUM 登记；`.env.example` 改为占位符更佳。

5. **问题 7（LOW）**：MD5 命名引用仅出现在测试断言中（断言"md5 输入应被拒绝"），符合 V8 强制单独报告要求。

---

## 严重度确认步骤（V8 要求）

- [x] 已检查所有 13 个评审维度
- [x] 已审查 4 个指定文件（`setup-schema.ts`、`slow-query-warning.ts`、`raw-sql-demo.ts`、`probe-mongoquery.ts`）
- [x] 已关联审查周边强耦合文件（`worker.ts`、`docker-compose.yml`、`.env.example`、`wrangler.jsonc`、`global-setup.ts`）
- [x] 所有 HIGH 问题提供了代码片段（问题 1）
- [x] 所有问题均使用 V8 锁定严重度（命令注入 HIGH、硬编码管理员凭据 MEDIUM、MD5/SHA1 LOW）
- [x] 组合漏洞已合并（CSRF + 速率限制 = 1 个 MEDIUM 问题）
- [x] 输出格式符合 V8 模板
- [x] 已报告所有 MEDIUM/LOW 问题
- [x] 每个维度给出明确结论

---

**评审完成时间**: 2026-08-13
**评审者**: Agent Alpha
**语言**: TypeScript / Node.js (Prisma ORM + MongoDB Contract Builder 示例)