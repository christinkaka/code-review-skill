# 规约库与检测模式

---

## 规约库

### 安全规约覆盖（12 类）

| 安全类别 | CWE 编号 | 规则文件 | 风险等级 | 检测说明 |
|----------|----------|----------|----------|----------|
| 越权访问 | CWE-862 / CWE-863 | `security/authorization.md` | CRITICAL | 接口缺少鉴权注解，水平/垂直越权模式 |
| XXE | CWE-611 | `security/xxe.md` | HIGH | XML 解析器未禁用外部实体 |
| XSS | CWE-79 | `security/xss.md` | HIGH | 未转义用户输入直接输出到 HTML/JS |
| 目录穿越 | CWE-22 | `security/path-traversal.md` | HIGH | 文件路径拼接用户输入未做规范化 |
| 提权/命令注入 | CWE-250 / CWE-78 | `security/privilege-escalation.md` | CRITICAL | 低权限执行高权限操作，命令注入 |
| 签名绕过 | CWE-345 / CWE-347 | `security/signature-bypass.md` | CRITICAL | 签名验证不完整，密钥硬编码 |
| SQL 注入 | CWE-89 | `security/sql-injection.md` | CRITICAL | 字符串拼接 SQL，占位符滥用 |
| SSRF | CWE-918 | `security/ssrf.md` | HIGH | 用户可控 URL 未做白名单限制 |
| 硬编码密钥 | CWE-798 | `security/hardcoded-secrets.md` | HIGH | 密码/Token 硬编码在源码中 |
| 反序列化 | CWE-502 | `security/deserialization.md` | CRITICAL | 不安全的反序列化操作 |
| 日志注入 | CWE-117 | `security/log-injection.md` | MEDIUM | 日志中未转义用户输入 |
| 弱随机数 | CWE-330 | `security/weak-randomness.md` | MEDIUM | 安全敏感场景使用弱随机数 |

### 设计规约（3 类）

| 规约类别 | 规则文件 | 检测说明 |
|----------|----------|----------|
| 架构合规 | `design/architecture.md` | 分层依赖检查，循环引用检测 |
| API 设计 | `design/api-design.md` | RESTful 规范，命名规范，返回值规范 |
| 数据库设计 | `design/database.md` | N+1 查询检测，事务管理，索引建议 |

### 实现规约（4 类）

| 规约类别 | 规则文件 | 检测说明 |
|----------|----------|----------|
| 命名规范 | `implementation/naming.md` | 常量/变量/方法命名约定 |
| 异常处理 | `implementation/error-handling.md` | 空 catch 块，裸 except，异常吞没 |
| 并发安全 | `implementation/concurrency.md` | 线程安全，竞态条件，死锁风险 |
| 空指针防护 | `implementation/null-safety.md` | 未判空调用，自动拆箱，Optional 使用 |

### 测试案例

每个规约都有对应的测试案例，位于 `references/test-cases/` 目录：

```
test-cases/
├── security/
│   ├── xxe-test.md           # XXE 违规/正确代码样本
│   ├── xss-test.md           # XSS 违规/正确代码样本
│   └── ...
├── design/
│   ├── architecture-test.md  # 架构合规测试
│   └── ...
└── implementation/
    ├── naming-test.md        # 命名规范测试
    └── ...
```

每个测试案例包含：
- **违规代码样本**：应该被检测到的代码
- **正确代码样本**：不应该被检测到的代码
- **预期命中规则**：明确标注应该命中的规则 ID

### 自定义规则

在 `references/rules/custom.md` 中添加规则，用 `---` 分隔不同规则：

```markdown
# 我的规则 - 简要描述

> 一句话说明

```yaml
id: custom-my-rule
languages: [java]
severity: WARNING
category: custom
```


---

## 检测模式

```pattern
Statement $STMT = ...;
...
$STMT.execute("..." + $VAR + "...");
```

```pattern-not
PreparedStatement $PS = ...;
...
$PS.execute(...);
```
```

**规则文件分类**：

| 类别 | 目录 | 说明 |
|------|------|------|
| 安全规则 | `references/security/` | SQL 注入、XXE、XSS 等 12 类 |
| 设计规则 | `references/design/` | 架构合规、API 设计、数据库设计 |
| 实现规则 | `references/implementation/` | 命名、异常、并发、空指针 |
| 自定义规则 | `references/rules/custom.md` | 用户自定义业务规则 |
| 规则生成指南 | `references/RULE-GENERATOR-GUIDE.md` | 指导如何编写新规则 |

**使用方法**：

```bash
# 查看编译状态
python scripts/rule_compiler.py --status

# 编译所有规则
python scripts/rule_compiler.py --compile

# 强制重新编译
python scripts/rule_compiler.py --compile --force
```

**性能提升**：

| 加载方式 | 耗时 | 说明 |
|----------|------|------|
| 从缓存加载 | ~8ms | 优先使用 |
| 解析 Markdown | ~17ms | 缓存失效时回退 |
| **性能提升** | **~50%** | - |

**缓存目录结构**：

```
references/
├── RULE-GENERATOR-GUIDE.md    # 规则生成指南（不编译）
├── security/
│   ├── sql-injection.md       # 原始 Markdown（人可读）
│   └── ...
├── design/
│   └── ...
├── implementation/
│   └── ...
├── prompts/                   # 提示词模板（不编译）
├── test-cases/                # 测试案例（不编译）
├── compiled/                  # 编译后的缓存（.gitignore）
│   ├── manifest.json          # hash 清单
│   ├── security/
│   │   ├── sql-injection.md.json  # 编译后的规则（机器可执行）
│   │   └── ...
│   ├── design/
│   └── implementation/
```

**注意事项**：
- 修改 Markdown 规则文件后，hash 会变化，下次编译会自动重新解析
- 缓存目录 `references/compiled/` 已加入 `.gitignore`
- `RULE-GENERATOR-GUIDE.md`、`prompts/`、`test-cases/` 不会被编译
- 预编译机制是自动的，RuleEngine 初始化时自动检查缓存

---


