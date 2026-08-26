# 能力地图（自动生成，勿手改）

> 由 `scripts/gen_capability_map.py` 从规则库实时推导生成。
> 人工只维护 `docs/capability-map-data.yaml`（质量等级与靶场凭证），
> 修改后重跑 `python3 scripts/gen_capability_map.py`。
> 质量阶梯判定标准与推进批次见 `docs/blueprint.md`；
> 新增规则的标准流程见 `docs/rule-intake-sop.md`。

## 总览

- 规则总数：**108**（taint 数据流 11 / pattern 97）
- e2e 测试覆盖规则：**33**
- L3 类别（靶场盲测零误报）：**12** / L2 1
- 待扩展格（L0）：**7**

## 覆盖矩阵（按质量等级）

| 等级 | CWE | 类别 | OWASP | 规则 | taint | e2e | 靶场凭证 |
|------|-----|------|-------|------|-------|-----|----------|
| L3 | CWE-89 | SQL 注入 | A03 | `sqli-taint`、`sqli-java-mybatis-dollar`⚠、`sqli-java-mybatis-annotation`⚠、`sqli-xml-mybatis-dollar`⚠、`sqli-python-execute-format`⚠、`sqli-python-raw-query`⚠ | ✓ | 部分 | java-sec-code: taint 4 TP + 0 FP（JDBC/JPA 全中，PreparedStatement 加固豁免） |
| L3 | CWE-22 | 路径穿越 | A01 | `path-read-traversal`、`path-write-traversal`、`path-upload-traversal`⚠、`path-config-traversal`、`path-log-traversal`、`path-traversal-taint`、`path-system-files`⚠、`path-traversal-pattern`⚠ | ✓ | 部分 | java-sec-code: taint 全 vuln 中，normalize 加固豁免 |
| L3 | CWE-918 | SSRF | A10 | `ssrf-deep-detection`、`ssrf-taint`、`ssrf-python-requests`、`ssrf-python-urllib`⚠、`ssrf-js-fetch`、`ssrf-js-fetch-weak-filter`⚠、`ssrf-js-axios`⚠、`ssrf-js-http-get`⚠ | ✓ | 部分 | java-sec-code: openStream 型检出；SSRFChecker 安全控件零误报 |
| L3 | CWE-611 | XXE | A05 | `xxe-deep-detection`、`xxe-java-document-builder`、`xxe-java-sax-parser`、`xxe-java-xml-reader`⚠、`xxe-java-unmarshaller`⚠、`xxe-python-lxml`⚠、`xxe-python-xml-dom`⚠、`xxe-python-lxml-parser`⚠、`xxe-python-lxml-parse`⚠、`xxe-python-lxml-resolve-entities`⚠ | — | 部分 | java-sec-code: 工厂级+reader级加固豁免（pattern-not-inside 实证） |
| L3 | CWE-79 | XSS | A03 | `xss-taint`、`xss-js-innerhtml`、`xss-js-document-write`⚠、`xss-js-outerhtml`⚠、`xss-js-dangerouslysetinnerhtml`⚠、`xss-python-flask-markup`⚠ | ✓ | 部分 | java-sec-code: xss-taint 检出，encode 净化豁免 |
| L3 | CWE-502 | 不安全反序列化 | A08 | `deser-taint`、`deser-yaml-taint`、`deser-python-pickle`⚠、`deser-node-serialize`⚠ | ✓ | 部分 | java-sec-code: Shiro-550 五层调用链命中；SnakeYAML SafeConstructor 豁免 |
| L3 | CWE-78 | 命令注入 | A03 | `cmdi-taint`、`priv-java-runtime-exec`⚠、`priv-java-process-builder`⚠、`priv-python-os-system`、`priv-python-subprocess-shell`、`priv-python-subprocess-run`⚠、`priv-python-subprocess-popen`⚠、`priv-js-child-process`、`priv-python-check-output-shell-true`⚠ | ✓ | 部分 | java-sec-code: 5 TP + 0 FP（含 TomcatFilterMemShell 内存马 RCE 点） |
| L3 | CWE-94/95/917 | 表达式/代码注入 | A03 | `script-engine-taint`、`priv-python-eval`、`priv-python-exec`⚠、`spel-taint`、`qlexpress-taint` | ✓ | 部分 | java-sec-code: SpEL/QLExpress/ScriptEngine 5 TP + 0 FP，加固形态豁免 |
| L3 | CWE-117 | 日志注入 | A09 | `log-injection-taint`、`log-injection-python`⚠ | ✓ | 部分 | java-sec-code: 36 检出全为真实用户数据流（pattern 版仅 2 且含常量误报） |
| L3 | CWE-798 | 硬编码凭证 | A07 | `crypto-hardcoded-key`⚠、`crypto-hardcoded-key-java`、`sig-java-hardcoded-key` | — | 部分 | WebGoat: crypto-hardcoded-key 22 TP + 0 FP（密码/JWT密钥/API Key/盐值/令牌全覆盖） |
| L3 | CWE-330 | 弱随机数 | A02 | `crypto-weak-random-java`⚠ | — | — | WebGoat: crypto-weak-random-java 11 TP + 0 FP（PIN/会话ID/JWT密钥/CSRF flag/密码重置全覆盖） |
| L3 | CWE-601 | 开放重定向 | A01 | `redirect-pattern-2` | — | ✓ | java-sec-code: redirect-pattern-2 1 TP + 0 FP（URLRedirect.java:55 sendRedirect 命中，:85 SecurityUtil.checkURL 白名单豁免） |
| L2 | CWE-327/328 | 弱加密/弱哈希 | A02 | `sig-java-weak-algorithm`、`sig-python-weak-hash`⚠ | — | 部分 | — |

> 规则名后 ⚠ 表示无 e2e 测试引用；e2e 列以规则 id 在 tests/ 中出现为准。

## 待扩展格（L0，有 CVE/CWE 归属无规则）

| CWE | 类别 | OWASP | 推进批次 |
|-----|------|-------|----------|
| CWE-1336 | SSTI 模板注入 | A03 | 阶段一 A2 |
| CWE-502 | Fastjson/XStream 反序列化（补全） | A08 | 阶段一 A3 |
| CWE-93 | CRLF 注入 | A03 | 阶段一 A4（覆盖确认） |
| CWE-352 | CSRF | A01 | 阶段一 B1（Top25 第 3，误报风险高先 PoC） |
| CWE-942 | CORS 过宽 | A05 | 阶段一 B2 |
| CWE-614 | Cookie 安全属性缺失 | A05 | 阶段一 B3 |
| CWE-470 | 不安全反射/类加载 | A03 | 待评估（泛化性差风险） |

## 规则明细（全量自动推导）

| 规则 id | 类别 | 等级 | 语言 | 形态 | e2e |
|---------|------|------|------|------|-----|
| `api-java-missing-doc` | — | — | java | pattern | — |
| `api-java-missing-response-wrapper` | — | — | java | pattern | — |
| `api-java-missing-validation` | — | — | java | pattern | — |
| `api-java-missing-version` | — | — | java | pattern | — |
| `api-java-rest-naming` | — | — | java | pattern | — |
| `arch-java-circular-dep` | — | — | java | pattern | — |
| `arch-java-entity-leak` | — | — | java | pattern | — |
| `arch-java-layer-violation` | — | — | java | pattern | — |
| `arch-java-missing-api-layer` | — | — | java | pattern | ✓ |
| `arch-java-missing-exception-handler` | — | — | java | pattern | — |
| `db-java-missing-batch` | — | — | java | pattern | — |
| `db-java-missing-index` | — | — | java | pattern | — |
| `db-java-missing-transaction` | — | — | java | pattern | — |
| `db-java-n-plus-one` | — | — | java | pattern | — |
| `db-java-select-star` | — | — | java | pattern | — |
| `db-java-sql-injection` | — | — | java | pattern | — |
| `conc-java-double-checked-locking` | — | — | java | pattern | — |
| `conc-java-unsafe-hashmap` | — | — | java | pattern | — |
| `conc-java-unsafe-simpledateformat` | — | — | java | pattern | — |
| `conc-python-global-mutable` | — | — | python | pattern | — |
| `err-java-catch-generic` | — | — | java | pattern | — |
| `err-java-empty-catch` | — | — | java | pattern | — |
| `err-java-throw-in-finally` | — | — | java | pattern | — |
| `err-python-bare-except` | — | — | python | pattern | — |
| `err-python-silent-except` | — | — | python | pattern | — |
| `naming-java-boolean-prefix` | — | — | java | pattern | ✓ |
| `naming-java-boolean-vague` | — | — | java | pattern | — |
| `naming-java-constant-case` | — | — | java | pattern | — |
| `naming-python-class-case` | — | — | python | pattern | — |
| `naming-python-function-case` | — | — | python | pattern | — |
| `null-java-collection-get` | — | — | java | pattern | — |
| `null-java-method-chain` | — | — | java | pattern | — |
| `null-java-unwrap-boxed` | — | — | java | pattern | ✓ |
| `auth-java-horizontal-escalation` | CWE-862 | — | java | pattern | — |
| `auth-java-idor-direct-ref` | CWE-862 | — | java | pattern | — |
| `auth-java-missing-annotation` | CWE-862 | — | java | pattern | — |
| `auth-python-django-mixin` | CWE-862 | — | python | pattern | — |
| `auth-python-missing-login-required` | CWE-862 | — | python | pattern | — |
| `cmdi-taint` | CWE-78 | L3 | java | taint | ✓ |
| `crypto-hardcoded-key` | CWE-798 | L3 | java/python/javascript/typescript | pattern | — |
| `crypto-hardcoded-key-java` | CWE-798 | L3 | java | pattern | ✓ |
| `crypto-weak-random-java` | CWE-330 | L3 | java | pattern | — |
| `deser-node-serialize` | CWE-502 | L3 | javascript/typescript | pattern | — |
| `deser-python-pickle` | CWE-502 | L3 | python | pattern | — |
| `deser-taint` | CWE-502 | L3 | java | taint | ✓ |
| `deser-yaml-taint` | CWE-502 | L3 | java | taint | ✓ |
| `log-injection-python` | CWE-117 | L3 | python | pattern | — |
| `log-injection-taint` | CWE-117 | L3 | java | taint | ✓ |
| `path-config-traversal` | CWE-22 | L3 | python/javascript/typescript | pattern | ✓ |
| `path-log-traversal` | CWE-22 | L3 | python/javascript/typescript | pattern | ✓ |
| `path-read-traversal` | CWE-22 | L3 | python/javascript/typescript | pattern | ✓ |
| `path-system-files` | CWE-22 | L3 | java/python/javascript/typescript | pattern | — |
| `path-traversal-pattern` | CWE-22 | L3 | java/python/javascript/typescript | pattern | — |
| `path-traversal-taint` | CWE-22 | L3 | java | taint | ✓ |
| `path-upload-traversal` | CWE-22 | L3 | python/javascript/typescript | pattern | — |
| `path-write-traversal` | CWE-22 | L3 | python/javascript/typescript | pattern | ✓ |
| `priv-java-process-builder` | CWE-78 | L3 | java | pattern | — |
| `priv-java-runtime-exec` | CWE-78 | L3 | java | pattern | — |
| `priv-js-child-process` | CWE-78 | L3 | javascript/typescript | pattern | ✓ |
| `priv-python-check-output-shell-true` | CWE-78 | L3 | python | pattern | — |
| `priv-python-eval` | CWE-95 | L3 | python | pattern | ✓ |
| `priv-python-exec` | CWE-95 | L3 | python | pattern | — |
| `priv-python-os-system` | CWE-78 | L3 | python | pattern | ✓ |
| `priv-python-subprocess-popen` | CWE-78 | L3 | python | pattern | — |
| `priv-python-subprocess-run` | CWE-78 | L3 | python | pattern | — |
| `priv-python-subprocess-shell` | CWE-78 | L3 | python | pattern | ✓ |
| `qlexpress-taint` | CWE-917 | L3 | java | taint | ✓ |
| `redirect-pattern-2` | CWE-601 | L3 | java | pattern | ✓ |
| `script-engine-taint` | CWE-94 | L3 | java | taint | ✓ |
| `sig-bypass-version-check-regex` | CWE-345 | — | java | pattern | — |
| `sig-bypass-version-skip` | CWE-345 | — | java | pattern | — |
| `sig-java-hardcoded-key` | CWE-798 | L3 | java | pattern | ✓ |
| `sig-java-verify-skip` | CWE-345 | — | java | pattern | — |
| `sig-java-weak-algorithm` | CWE-328 | L2 | java | pattern | ✓ |
| `sig-python-no-timestamp` | CWE-345 | — | python | pattern | — |
| `sig-python-verify-false` | CWE-345 | — | python | pattern | — |
| `sig-python-weak-hash` | CWE-328 | L2 | python | pattern | — |
| `spel-taint` | CWE-917 | L3 | java | taint | ✓ |
| `sqli-java-mybatis-annotation` | CWE-89 | L3 | java | pattern | — |
| `sqli-java-mybatis-dollar` | CWE-89 | L3 | java | pattern | — |
| `sqli-python-execute-format` | CWE-89 | L3 | python | pattern | — |
| `sqli-python-raw-query` | CWE-89 | L3 | python | pattern | — |
| `sqli-taint` | CWE-89 | L3 | java | taint | ✓ |
| `sqli-xml-mybatis-dollar` | CWE-89 | L3 | xml | pattern | — |
| `ssrf-deep-detection` | CWE-918 | L3 | java/python/javascript/typescript | pattern | ✓ |
| `ssrf-js-axios` | CWE-918 | L3 | javascript/typescript | pattern | — |
| `ssrf-js-fetch` | CWE-918 | L3 | javascript/typescript | pattern | ✓ |
| `ssrf-js-fetch-weak-filter` | CWE-918 | L3 | javascript/typescript | pattern | — |
| `ssrf-js-http-get` | CWE-918 | L3 | javascript/typescript | pattern | — |
| `ssrf-python-requests` | CWE-918 | L3 | python | pattern | ✓ |
| `ssrf-python-urllib` | CWE-918 | L3 | python | pattern | — |
| `ssrf-taint` | CWE-918 | L3 | java | taint | ✓ |
| `xss-js-dangerouslysetinnerhtml` | CWE-79 | L3 | javascript/typescript | pattern | — |
| `xss-js-document-write` | CWE-79 | L3 | javascript/typescript | pattern | — |
| `xss-js-innerhtml` | CWE-79 | L3 | javascript/typescript | pattern | ✓ |
| `xss-js-outerhtml` | CWE-79 | L3 | javascript/typescript | pattern | — |
| `xss-python-flask-markup` | CWE-79 | L3 | python | pattern | — |
| `xss-taint` | CWE-79 | L3 | java | taint | ✓ |
| `xxe-deep-detection` | CWE-611 | L3 | java/python | pattern | ✓ |
| `xxe-java-document-builder` | CWE-611 | L3 | java | pattern | ✓ |
| `xxe-java-sax-parser` | CWE-611 | L3 | java | pattern | ✓ |
| `xxe-java-unmarshaller` | CWE-611 | L3 | java | pattern | — |
| `xxe-java-xml-reader` | CWE-611 | L3 | java | pattern | — |
| `xxe-python-lxml` | CWE-611 | L3 | python | pattern | — |
| `xxe-python-lxml-parse` | CWE-611 | L3 | python | pattern | — |
| `xxe-python-lxml-parser` | CWE-611 | L3 | python | pattern | — |
| `xxe-python-lxml-resolve-entities` | CWE-611 | L3 | python | pattern | — |
| `xxe-python-xml-dom` | CWE-611 | L3 | python | pattern | — |
