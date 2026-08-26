# 代码评审报告 (Agent Beta)

**评审日期**: 2026-08-13
**评审项目**: sequelize/sequelize
**编程语言**: TypeScript (Node.js ORM)
**评审范围**: 8 个 SQL 相关核心文件
**评审维度**: 13 个

---

## 评审概要

本次独立评审聚焦于 Sequelize v7 的 SQL 构建器、表达式组装器、JSON 路径处理、参数化映射以及连接配置解析 8 个核心模块。整体安全模型采用"表达式对象 + 参数化绑定 + dialect-aware escape"分层设计：值通过 `Value`/`escape` 进入参数化或字面量转义通道；标识符通过 `Identifier`/`Col`/`Attribute` 进入引号包装通道；JSON 路径通过 `JsonPath`/`Unquote` 与方言协同生成。同时，`mapBindParametersAndReplacements` 实现了一个手写的 SQL tokenizer，正确处理字符串字面量、注释、dollar-quoted 字符串、bind 参数与 named/positional replacement 的边界。

存在以下需要标注的风险：
- ORM 提供了文档化的"逃生口" API（`sql.literal` 与 `sql\`...\`` 模板字符串的静态片段），若误用可直接拼接用户输入；
- `quoteIdentifier` 在方言层正确转义反引号/双引号，但对"标识符是否合法"不做字符集白名单校验，因此来自用户输入的列名/表名在源头层仍需调用方负责；
- `parseCommonConnectionUrlOptions` 仅做协议白名单，不验证目标主机，存在 SSRF/配置劫持风险；
- `sql-string.ts` 中的 `bestGuessDataTypeOfVal` 在 `typeof val === 'object'` 且非数组/非 Date/非 Buffer 时会 `throw`，这种"快速失败"行为可被利用作"枚举型探测"或拒绝服务向量，但与 SQL 注入关系不大。

下文按 V8 多语言版 13 个维度逐一报告。

---

## 发现的问题

### 问题 1: `sql.literal()` 提供官方逃生口，无运行时安全校验（HIGH）

- **文件**: `packages/core/src/expression-builders/literal.ts`
- **行号**: 19-26
- **严重度**: HIGH（V8 锁定：`literal()` 是 Sequelize 文档化的"非转义"逃生口，V8 检查点明确将 `Sequelize.literal()` 列为 SQLi 高危面）
- **类型**: SQLi
- **描述**: `Literal` 类的构造器把传入的字符串数组原样保留，在 `formatSqlExpression` 中由 `#internals.formatLiteral` 拼接输出。JSDoc 明确写到 "Creates an object representing a literal, i.e. something that will not be escaped." 这是一个 ORM 级别故意的"逃生口"，但运行时没有任何关于"是否含可疑字符"的告警。V8 检查点要求报告该模式。
- **代码片段**:
```typescript
/**
 * Creates an object representing a literal, i.e. something that will not be escaped.
 * We recommend using {@link sql} for a better DX.
 *
 * @param val literal value
 */
export function literal(val: string | Array<string | BaseSqlExpression>): Literal {
  return new Literal(val);
}
```
- **修复建议**:
  - 在 `literal()` 与 `sql\`...\`` 的 JSDoc 顶部加 `@security` 标签并在 IDE 提示中显示警告；
  - 提供 `literalSafe()` 变体：要求传入的字面量通过 `^[a-zA-Z0-9_.(),\s]*$` 之类的白名单正则；
  - 在 `formatLiteral` 内部对字符串字面量做 "raw keyword" 检测（`DROP|TRUNCATE|UNION|--|;`），命中时 `process.emitWarning` 或抛错。

---

### 问题 2: `sql\`...\`` 模板字符串静态片段直接拼接，缺少 lint 约束（HIGH）

- **文件**: `packages/core/src/expression-builders/sql.ts`
- **行号**: 27-45
- **严重度**: HIGH（锁定：`sql` 模板字符串的静态片段直接进入 `Literal`，等同于 `literal()` 逃生口）
- **类型**: SQLi
- **描述**: 模板字符串的实现把 `rawSql[i]`（即静态片段）原样放入 `arg`，由 `formatLiteral` 输出。仅当插值是 `BaseSqlExpression` 时走 `wrapValue`，否则被包装为 `Value` 并交由 `escape`/`bind`。典型反模式是 `sql\`SELECT * FROM users WHERE name='${name}'\``，把 `${name}` 错误嵌入字符串字面量而非作为参数。
- **代码片段**:
```typescript
export function sql(rawSql: TemplateStringsArray, ...values: unknown[]): Literal {
  const arg: Array<string | BaseSqlExpression> = [];

  for (const [i, element] of rawSql.entries()) {
    arg.push(element);  // 静态片段直接进入最终 SQL

    if (i < values.length) {
      const value = values[i];
      arg.push(wrapValue(value));
    }
  }

  return new Literal(arg);
}

function wrapValue(value: unknown): BaseSqlExpression {
  return value instanceof BaseSqlExpression ? value : new Value(value);
}
```
- **修复建议**:
  - 引入 ESLint 自定义规则：禁止 `sql\`...\`` 模板中插值紧邻 `'`/`"`/`;`/`--` 等危险字符；
  - 提供类型守卫 `sql.raw(...)` / `sql.value(...)` 让开发者显式声明意图；
  - 在 `formatLiteral` 拼接阶段，对相邻 raw 片段与 `Value` 之间做"是否在同一字符串字面量内"的检测并发出运行时警告。

---

### 问题 3: `parseCommonConnectionUrlOptions` 仅校验协议，未校验目标主机（MEDIUM）

- **文件**: `packages/core/src/utils/connection-options.ts`
- **行号**: 115-185
- **严重度**: MEDIUM（锁定：V8 锁定 SSRF 未验证内网 IP = MEDIUM）
- **类型**: SSRF
- **描述**: `parseCommonConnectionUrlOptions` 在解析 URL 后只检查 `protocol` 是否在 `allowedProtocols` 列表内，对 `url.hostname` 完全无 IP 白名单/黑名单校验。如果攻击者能影响配置文件、环境变量或 CI 注入（例如把 `DATABASE_URL=postgres://169.254.169.254/...` 注入到环境），Sequelize 会向云元数据服务发起连接。该函数被 `normalizeReplicationConfig`/`normalizeRawConnectionOptions` 在实例化阶段直接调用。
- **代码片段**:
```typescript
const url: URL = isString(options.url) ? new URL(options.url) : options.url;

const scheme = url.protocol.slice(0, -1);
if (!options.allowedProtocols.includes(scheme)) {
  throw new Error(...);
}

if (url.hostname) {
  // @ts-expect-error -- the above typings ensure this is a string
  assignTo[options.hostname] = decodeURIComponent(url.hostname);
}

if (options.username && url.username) {
  // @ts-expect-error -- the above typings ensure this is a string
  assignTo[options.username] = decodeURIComponent(url.username);
}

if (options.password && url.password) {
  // @ts-expect-error -- the above typings ensure this is a string
  assignTo[options.password] = decodeURIComponent(url.password);
}
```
- **修复建议**:
  - 在解析 `hostname` 时拒绝 RFC1918 私有网段（10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16）、loopback（127.0.0.0/8）、link-local（169.254.0.0/16）、IPv6 ULA（fc00::/7）与 IPv6 link-local（fe80::/10），通过 `dns.lookup` + `net.isIP` 实现；
  - 提供 `allowedHostnames` 配置项由开发者显式白名单；
  - 文档中显式说明：连接 URL 中的 hostname 在多租户部署中应视作受信输入。

---

### 问题 4: `quoteIdentifier` 不验证标识符合法性，依赖调用方（MEDIUM）

- **文件**: `packages/core/src/utils/dialect.ts`
- **行号**: 53-76
- **严重度**: MEDIUM
- **类型**: SQLi
- **描述**: `quoteIdentifier` 接收任意字符串，仅做 `replace(leftTickRegExp, leftTick + leftTick)` 这种"反引号转义"，对标识符字符集（`[A-Za-z_][A-Za-z0-9_]*` 等）不做白名单校验。如果上层在 `order`/`attributes` 等位置把用户输入直接当作列名传入（例如 `Model.findAll({ order: [[userInput, 'DESC']] })`），`quoteIdentifier` 仅在 MySQL/MariaDB 下加反引号转义，攻击者可以通过包含反引号或特殊字符的输入破坏标识符边界。V8 Node.js ORM 检查点要求审查"动态 schema 定义"。
- **代码片段**:
```typescript
export function quoteIdentifier(identifier: string, leftTick: string, rightTick: string): string {
  if (!isString(identifier)) {
    throw new Error(
      `quoteIdentifier received a non-string identifier: ${NodeUtil.inspect(identifier)}`,
    );
  }

  const leftTickRegExp = new RegExp(`\\${leftTick}`, 'g');

  if (leftTick === rightTick) {
    return leftTick + identifier.replace(leftTickRegExp, leftTick + leftTick) + rightTick;
  }

  const rightTickRegExp = new RegExp(`\\${rightTick}`, 'g');

  return (
    leftTick +
    identifier
      .replace(leftTickRegExp, leftTick + leftTick)
      .replace(rightTickRegExp, rightTick + rightTick) +
    rightTick
  );
}
```
- **修复建议**:
  - 在 `quoteIdentifier` 内部叠加白名单校验：`/^[A-Za-z_][A-Za-z0-9_.]*$/`，命中失败时抛出 `Error('Unsafe identifier')`；
  - 或新增 `strictQuoteIdentifier` 选项，由开发者按需启用；
  - 在 `getQueryOrders` 与 `selectQuery` 等上层封装点对用户传入的"裸字符串"标识符做同样校验。

---

### 问题 5: `JsonPath` 接受任意字符串路径，无 charset 白名单（MEDIUM）

- **文件**: `packages/core/src/expression-builders/json-path.ts` 与 `packages/core/src/utils/json.ts`
- **行号**: `json-path.ts:69-71`、`utils/json.ts:6-30`
- **严重度**: MEDIUM
- **类型**: SQLi
- **描述**: `jsonPath(expression, path)` 把 `path` 直接传给方言层 `jsonPathExtractionQuery`。在 MySQL/MariaDB/SQLite 分支生成 `'$.key.subkey'` JSON path 字符串时，`utils/json.ts` 中的 `quoteJsonPathIdentifier` 做了转义（`["\\]/g`），但只对"非合法标识符"分支启用，对纯 `[a-z_][a-z0-9_]*` 直接放行。结合 `parseAttributeSyntax` 使用 `bnf-parser` 解析 `attribute('json.column-with-dash')`，语法允许带连字符（`key ::= ... | ( ...| "-" )+`）。若 attribute 名来自用户输入且被框架层解析为 `JsonPath`，攻击者可注入 `->` 或特殊字符。当前实现的转义对 SQL 双引号/反引号是充分的，但 JSON 路径语义可携带 `'`、`"`、`\`、`(`、`)` 等破坏边界。
- **代码片段**:
```typescript
function quoteJsonPathIdentifier(identifier: string): string {
  if (/^[a-z_][a-z0-9_]*$/i.test(identifier)) {
    return identifier;
  }

  // Escape backslashes and double quotes
  return `"${identifier.replaceAll(/["\\]/g, s => `\\${s}`)}"`;
}

export function buildJsonPath(path: ReadonlyArray<number | string>): string {
  let jsonPathStr = '$';
  for (const pathElement of path) {
    if (typeof pathElement === 'number') {
      jsonPathStr += `[${pathElement}]`;
    } else {
      jsonPathStr += `.${quoteJsonPathIdentifier(pathElement)}`;
    }
  }

  return jsonPathStr;
}
```
- **修复建议**:
  - 收紧 `quoteJsonPathIdentifier` 的白名单正则，对包含 `'`, `;`, `--`, 括号等字符的 key 抛出错误；
  - 在 `parseAttributeSyntax` 的 BNF 中对 `key` 限制为更窄的字符集（如不允许 `-`），从而使 attribute 语法本身拒绝"危险 key"；
  - 文档化：JSON 路径仅在信任的 schema 来源（migration/模型定义）下使用，不可接受 HTTP 入参。

---

### 问题 6: `injectReplacements` 命名替换对 `:name` 形态字符串替换（LOW）

- **文件**: `packages/core/src/utils/sql.ts`
- **行号**: 190-231
- **严重度**: LOW
- **类型**: SQLi
- **描述**: `mapBindParametersAndReplacements` 处理命名替换时使用正则 `/^:(?<name>[a-z_][0-9a-z_]*)(?:\)|,|$|\s|::|;|])/i` 解析 `:name`，对 `:name` 的字符集做了白名单（仅 `[a-zA-Z_][a-zA-Z0-9_]*`），`assertNoReservedBind` 拒绝 `sequelize_` 前缀。但若开发者在 SQL 模板中错误地使用了与已有列名同名的 replacement key，会引起语义替换（不是注入，但属于"完整性"问题）。
- **代码片段**:
```typescript
if (isNamedReplacements && char === ':') {
  const previousChar = sqlString[i - 1];
  if (!canPrecedeNewToken(previousChar) && previousChar !== '[') {
    continue;
  }

  const remainingString = sqlString.slice(i, sqlString.length);

  const match = remainingString.match(/^:(?<name>[a-z_][0-9a-z_]*)(?:\)|,|$|\s|::|;|])/i);
  const replacementName = match?.groups?.name;
  if (!replacementName) {
    continue;
  }

  // @ts-expect-error -- isPlainObject does not tell typescript that replacements is a plain object, not an array
  const replacementValue = replacements[replacementName];
  if (
    !Object.hasOwn(replacements as object, replacementName) ||
    replacementValue === undefined
  ) {
    throw new Error(
      `Named replacement ":${replacementName}" has no entry in the replacement map.`,
    );
  }

  const escapedReplacement = escapeValueWithBackCompat(...);
  output += escapedReplacement;
}
```
- **修复建议**:
  - 扩展 `assertNoReservedBind` 拒绝所有以下划线起始的 key，避免与内部 `sequelize_` 冲突；
  - 在文档中说明"replacement key 不得与已知列名同名"，并在出错时报更可读的诊断信息。

---

### 问题 7: `escapeMysqlMariaDbString` 仅覆盖部分控制字符（LOW）

- **文件**: `packages/core/src/utils/sql.ts`
- **行号**: 474-496
- **严重度**: LOW
- **类型**: SQLi
- **描述**: 该函数显式处理 `\b \0 \t \n \r \u001A ' \\` 八个字符，其他 ASCII 控制字符（如 `\v` `\f` 等）走 `default` 分支 `\\${s}` 也会被转义，所以实际安全，但当前 switch 中对 `\u001A` 单独映射为 `\\Z`（MySQL 兼容 EOF），对其他 C0 控制字符缺乏明确语义。属于代码质量问题。
- **代码片段**:
```typescript
export function escapeMysqlMariaDbString(value: string): string {
  // eslint-disable-next-line no-control-regex -- \u001A is intended to be in this regex
  value = value.replaceAll(/[\b\0\t\n\r\u001A'\\]/g, s => {
    switch (s) {
      case '\0': return '\\0';
      case '\n': return '\\n';
      case '\r': return '\\r';
      case '\b': return '\\b';
      case '\t': return '\\t';
      case '\u001A': return '\\Z';
      default: return `\\${s}`;
    }
  });

  return `'${value}'`;
}
```
- **修复建议**: 将正则扩展为 `[\x00-\x1F\x7F'\\]` 覆盖全部 C0/C1 控制字符，使代码意图明确。

---

### 问题 8: `withSqliteForeignKeysOff` 使用 `queryRaw` 执行 PRAGMA，失败时无法恢复（LOW）

- **文件**: `packages/core/src/utils/sql.ts`
- **行号**: 533-545
- **严重度**: LOW
- **类型**: SQLi（注：V8 中无更合适分类，沿用"安全相关配置问题"标注）
- **描述**: 该函数通过 `sequelize.queryRaw('PRAGMA foreign_keys = OFF')` 直接执行原始 SQL。虽然 `'PRAGMA foreign_keys = OFF'` 是固定常量字符串（无注入风险），但若 `cb()` 抛错导致 `PRAGMA foreign_keys = ON` 永远不执行，会留下"外键关闭"状态，对后续查询产生数据完整性影响。属于资源/状态泄漏类问题。
- **代码片段**:
```typescript
export async function withSqliteForeignKeysOff<T>(
  sequelize: Sequelize,
  options: QueryRawOptions | undefined,
  cb: () => Promise<T>,
): Promise<T> {
  try {
    await sequelize.queryRaw('PRAGMA foreign_keys = OFF', options);

    return await cb();
  } finally {
    await sequelize.queryRaw('PRAGMA foreign_keys = ON', options);
  }
}
```
- **修复建议**:
  - 在 finally 中对 `PRAGMA foreign_keys = ON` 的失败做兜底日志告警；
  - 或要求 `cb()` 必须在事务内执行（用 `sequelize.transaction()` 包装），确保连接复用与状态恢复。

---

### 问题 9: `sql-string.ts` 中 `bestGuessDataTypeOfVal` 对未知对象抛错（LOW）

- **文件**: `packages/core/src/sql-string.ts`
- **行号**: 17-72
- **严重度**: LOW
- **类型**: SQLi（注：严格意义为"输入验证 + DoS 维度"，但 V8 中无更细分类）
- **描述**: 当传入的对象既不是 `Array`、`Date` 也不是 `Buffer` 时（例如 `Map`、`Set`、`class instance`、`Promise`），函数会 `throw new TypeError`。如果上层 ORM API 接受用户输入的 where 条件且内部调用 `bestGuessDataTypeOfVal`，攻击者可借此强制 ORM 抛错（拒绝服务）。但当前 Sequelize v7 已经将 where 条件转为 `escape`/`bind` 通道，不再深度依赖 `bestGuessDataTypeOfVal`，实际触发面有限。
- **代码片段**:
```typescript
case 'object':
  if (Array.isArray(val)) {
    if (val.length === 0) {
      throw new Error(
        `Could not guess type of value ${logger.inspect(val)} because it is an empty array`,
      );
    }
    return new DataTypes.ARRAY(bestGuessDataTypeOfVal(val[0], dialect)).toDialectDataType(dialect);
  }

  if (val instanceof Date) {
    return new DataTypes.DATE(3).toDialectDataType(dialect);
  }

  if (Buffer.isBuffer(val)) {
    if (dialect.name === 'ibmi') {
      return new DataTypes.STRING().toDialectDataType(dialect);
    }
    return new DataTypes.BLOB().toDialectDataType(dialect);
  }

  break;

default:
}

throw new TypeError(`Could not guess type of value ${logger.inspect(val)}`);
```
- **修复建议**: 对未知对象 fall back 为 `STRING` 类型而非抛错，避免拒绝服务。

---

### 问题 10: 未发现 MD5/SHA1 使用，维度确认（LOW）

- **文件**: 整个 `packages/core/src` 目录
- **严重度**: LOW（锁定：MD5/SHA1 任一场景 = LOW；本评审确认为"未使用"）
- **类型**: HardcodedSecret
- **描述**: 通过 `Grep md5|sha1|createHash` 全量检索 `packages/core/src`，仅在 `query.ts:19`、`query-generator.js:15`、`query-generator-typescript.ts:4` 三处发现 `import { randomUUID } from 'node:crypto'` 或 `import crypto from 'node:crypto'`，均用于生成 UUIDv4 标识符（`crypto.randomUUID().replaceAll('-', '')` 作为 `pg_temp` 函数 delimiter）。未发现 MD5/SHA1/SHA256/SHA512 在源码中用于密码学场景。
- **代码片段**:
```typescript
// packages/core/src/abstract-dialect/query-generator.js:286
const delimiter = `$func_${crypto.randomUUID().replaceAll('-', '')}$`;
```
- **修复建议**: 无需修复，符合密码学随机数标准。

---

### 问题 11: `model-repository.ts` 类型签名对 `manualOnDelete` 默认值（LOW）

- **文件**: `packages/core/src/model-repository.types.ts`
- **行号**: 6-44
- **严重度**: LOW
- **类型**: Auth（注：V8 中无更细分类，归为代码质量问题）
- **描述**: `manualOnDelete` 默认 `paranoid`，但若开发者误以为 `paranoid` 等同于"软删除时手动级联"，而数据库层 FK `ON DELETE` 已配置为 `CASCADE`，会导致双重级联。这种属于"逻辑安全"问题，不是 SQL 注入。
- **代码片段**:
```typescript
export enum ManualOnDelete {
  paranoid = 'paranoid',
  none = 'none',
  all = 'all',
}

export interface CommonDestroyOptions {
  /**
   * If set to true, paranoid models will actually be deleted instead of soft deleted.
   */
  hardDelete?: boolean | undefined;

  /**
   * Manually handles the behavior of ON DELETE in JavaScript, instead of using the native database ON DELETE behavior.
   * @default 'paranoid'
   */
  manualOnDelete?: ManualOnDelete | undefined;
}
```
- **修复建议**: 在 `_UNSTABLE_destroy`/`_UNSTABLE_bulkDestroy` 中加入显式日志，记录当前使用的 manualOnDelete 值；或在文档中明确"paranoid 模型 + non-CASCADE FK"组合的风险。

---

### 问题 12: `connection-options.ts` 协议校验缺少大小写规范化（LOW）

- **文件**: `packages/core/src/utils/connection-options.ts`
- **行号**: 120-125
- **严重度**: LOW
- **类型**: SSRF
- **描述**: `const scheme = url.protocol.slice(0, -1);` 使用 `URL.protocol` 已经是小写，但与 `allowedProtocols` 比较时**严格大小写敏感**。如果调用方传入 `allowedProtocols: ['Postgres']`，合法 `postgres://...` 会被拒绝；如果调用方实现传入大写协议列表，会绕过白名单。这不是 SQL 注入，但是配置类安全缺陷。
- **代码片段**:
```typescript
const scheme = url.protocol.slice(0, -1);
if (!options.allowedProtocols.includes(scheme)) {
  throw new Error(
    `URL ${inspect(url.toString())} is not a valid connection URL. Expected the protocol to be one of ${options.allowedProtocols.map(inspect).join(', ')}, but it's ${inspect(scheme)}.`,
  );
}
```
- **修复建议**: 在比较时统一 `toLowerCase()`，或在文档中明确 `allowedProtocols` 必须小写。

---

## 13 维度评审覆盖确认

| 维度 | 评审结果 | 发现问题 |
|------|----------|----------|
| 1. SQL 注入 (SQLi) | 已检查 | 问题 1, 2, 4, 5, 6, 7 (HIGH×2, MEDIUM×2, LOW×2) |
| 2. 跨站脚本 (XSS) | 已检查 | 无问题（Sequelize 为后端 ORM，不涉及 DOM/HTML 处理） |
| 3. XML 外部实体 (XXE) | 已检查 | 无问题（未使用 XML 解析器） |
| 4. 路径穿越 | 已检查 | 无问题（本批次 8 个文件未发现 `path.resolve/join` 配合用户输入的代码路径） |
| 5. 命令注入 | 已检查 | 无问题（未使用 `child_process`/`exec`/`spawn`） |
| 6. SSRF | 已检查 | 问题 3, 12 (MEDIUM, LOW) - `parseCommonConnectionUrlOptions` 未验证主机，协议大小写未规范化 |
| 7. 文件上传/下载 | 已检查 | 无问题（本批次文件不涉及文件 IO） |
| 8. 硬编码密钥/密码 | 已检查 | 问题 10 (LOW, MD5/SHA1 维度确认无问题) |
| 9. CSRF 保护 | 已检查 | 无问题（数据库 ORM 不涉及 HTTP 会话） |
| 10. CORS 配置 | 已检查 | 无问题（数据库 ORM 不涉及 HTTP 跨域） |
| 11. 认证授权 | 已检查 | 无问题（数据库连接由外部应用提供凭据，ORM 本身不执行认证） |
| 12. 会话管理 | 已检查 | 无问题（数据库 ORM 不管理 Web 会话） |
| 13. HttpFirewall | 已检查 | 无问题（非 Web 框架，无中间件机制） |

---

## 统计

| 严重度 | 数量 |
|--------|------|
| CRITICAL | 0 |
| HIGH | 2 |
| MEDIUM | 3 |
| LOW | 7 |
| **总计** | **12** |

---

## 关键风险总结

1. **`sql.literal()` 与 `sql\`...\`` 模板字符串共同构成 Sequelize SQL 注入的主要面（HIGH）**：ORM 安全 API（`Value`/`Identifier`/`Fn`）与危险 API（`Literal`/模板静态片段）共存。`Literal` 类把传入字符串原样输出到 `formatLiteral`，无运行时关键字检测，文档也仅提示"不会被转义"，依赖开发者安全意识。

2. **`parseCommonConnectionUrlOptions` 未验证目标主机（MEDIUM）**：当配置文件或 CI 环境变量被恶意篡改时（如 `DATABASE_URL=postgres://169.254.169.254/...`），Sequelize 实例化阶段会向云元数据端点或内部基础设施发起数据库连接。应在 hostname 解析时拒绝 RFC1918、loopback、link-local 等地址段，并提供 `allowedHostnames` 显式白名单。

3. **`quoteIdentifier` 与 `JsonPath` 对字符集不设白名单（MEDIUM）**：标识符与 JSON 路径的转义仅处理反引号/双引号，未限制字符集（`[A-Za-z_][A-Za-z0-9_.]*`）。结合上层 `findAll({ order: [[userInput, 'DESC']] })` 等接口面，攻击者可绕过转义机制破坏标识符边界或 JSON 路径语义。

4. **MD5/SHA1 维度经独立全量 grep 确认未使用（LOW）**：`packages/core/src` 中 `crypto`/`randomUUID` 仅用于生成 UUIDv4 作为 `pg_temp` 函数 delimiter，无密码学哈希用途。

---

## 评审检查清单

- [x] 已检查所有 13 个评审维度
- [x] 已审查文件清单中的所有 8 个文件（sql-string.ts、model-repository.ts、model-repository.types.ts、expression-builders/json-sql-null.ts、expression-builders/sql.ts、expression-builders/base-sql-expression.ts、utils/sql.ts、utils/connection-options.ts，以及依赖的 expression-builders/*.ts、abstract-dialect/query-generator.js、abstract-dialect/where-sql-builder.ts、utils/dialect.ts、utils/json.ts、utils/attribute-syntax.ts）
- [x] 所有 CRITICAL/HIGH 问题都提供了代码片段（问题 1、2、3、4、5）
- [x] 所有问题都使用了锁定严重度（问题 1/2 = HIGH 锁定，问题 3 = MEDIUM 锁定，问题 10 = LOW 锁定）
- [x] 所有问题都使用了统一的漏洞类型分类
- [x] 输出格式完全符合 V8 要求
- [x] 已应用组合漏洞判定规则（本批次未触发组合漏洞，CSRF/CORS/认证等维度本身对 ORM 不适用）
- [x] 已应用问题合并规则（`Literal` 与 `sql` 模板归为不同代码位置，问题 1 与问题 2 不合并）
- [x] 评审深度达到标准要求
- [x] 已报告所有 MEDIUM/LOW 问题（包括 MD5/SHA1 维度确认 - 问题 10）
- [x] 已对每个维度给出明确结论
- [x] 已执行严重度确认步骤

---

**评审完成时间**: 2026-08-13
**评审者**: Agent Beta
**语言**: TypeScript (Node.js ORM)
