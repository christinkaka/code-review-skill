# 验证报告

## 验证概况

- 验证时间：2026-07-28 16:36:31
- 已知问题数：26
- 检出问题数：48
- 验证方法：背靠背对比（行号容差 +/-2 行）
- 匹配模式：宽松匹配（文件 + 行号，忽略规则 ID 差异）+ 严格匹配（文件 + 行号 + 规则 ID）
- 扫描引擎：dual（builtin + semgrep 1.171.0）
- 加载规则数：83（其中 25 个规则加载错误，占 30.1%）

## 核心指标

### 宽松匹配（文件 + 行号，评估实际检出能力）

| 指标 | 数值 | 说明 |
|------|------|------|
| 检出率（Recall） | 50.0% | 检出的已知问题 13 / 总已知问题 26 |
| 精确率（Precision） | 27.1% | 检出的已知问题 13 / 总检出数 48 |
| 误报率（FPR） | 72.9% | 误报数 35 / 总检出数 48 |
| 漏报率（FNR） | 50.0% | 漏报数 13 / 总已知问题 26 |
| F1 Score | 35.1% | 精确率与检出率的调和平均 |

### 严格匹配（文件 + 行号 + 规则 ID，评估规则精确匹配能力）

| 指标 | 数值 | 说明 |
|------|------|------|
| 检出率（Recall） | 7.7% | 检出的已知问题 2 / 总已知问题 26 |
| 精确率（Precision） | 4.2% | 检出的已知问题 2 / 总检出数 48 |
| F1 Score | 5.4% | 精确率与检出率的调和平均 |

> **说明**：宽松匹配与严格匹配的差异（50.0% vs 7.7%）反映了规则 ID 命名不一致的程度。扫描工具实际能定位漏洞位置，但使用的规则 ID 与基准不一致。

## 检出详情

### 已检出的已知问题（13/26，宽松匹配）

| # | 文件 | 行号 | 期望规则 ID | 扫描规则 ID | 规则 ID 匹配 |
|---|------|------|-------------|-------------|-------------|
| 1 | java/xxe/Vulnerable.java | 22 | xxe-java-document-builder | xxe-java-document-builder | Y |
| 2 | java/xxe/Vulnerable.java | 29 | xxe-java-document-builder | xxe-java-document-builder | Y |
| 3 | java/path-traversal/Vulnerable.java | 27 | path-traversal-java-file | path-traversal-pattern | N |
| 4 | java/path-traversal/Vulnerable.java | 36 | path-traversal-java-weak-filter | path-traversal-pattern | N |
| 5 | python/command-injection/vulnerable.py | 35 | priv-python-popen-shell-true | priv-python-subprocess-popen | N |
| 6 | python/path-traversal/vulnerable.py | 22 | path-traversal-python-os-path-join | path-config-traversal | N |
| 7 | python/path-traversal/vulnerable.py | 30 | path-traversal-python-weak-filter | path-traversal-pattern | N |
| 8 | python/path-traversal/vulnerable.py | 39 | path-traversal-python-os-path-join | path-read-traversal | N |
| 9 | typescript/xss/vulnerable.ts | 21 | xss-ts-innerhtml | xss-js-innerhtml | N |
| 10 | typescript/xss/vulnerable.ts | 30 | xss-ts-document-write | xss-js-document-write | N |
| 11 | typescript/ssrf/vulnerable.ts | 22 | ssrf-ts-fetch-user-input | ssrf-js-fetch | N |
| 12 | typescript/ssrf/vulnerable.ts | 44 | ssrf-ts-fetch-user-input | ssrf-js-fetch | N |
| 13 | typescript/ssrf/vulnerable.ts | 59 | ssrf-ts-fetch-weak-filter | ssrf-js-fetch | N |

> 其中规则 ID 也精确匹配的：2/13

### 未检出的已知问题（漏报）（13/26）

| # | 文件 | 行号 | 规则 ID | 原因分析 |
|---|------|------|---------|----------|
| 1 | java/xss/Vulnerable.java | 30 | xss-java-servlet-output | 规则 'xss-java-servlet-output' 未在扫描结果中出现 |
| 2 | java/xss/Vulnerable.java | 44 | xss-java-servlet-output | 规则 'xss-java-servlet-output' 未在扫描结果中出现 |
| 3 | java/sqli/Vulnerable.java | 33 | sqli-java-statement-concat | 规则 'sqli-java-statement-concat' 未在扫描结果中出现 |
| 4 | java/sqli/Vulnerable.java | 45 | sqli-java-statement-concat | 规则 'sqli-java-statement-concat' 未在扫描结果中出现 |
| 5 | python/xxe/vulnerable.py | 20 | xxe-python-lxml-parser | 规则 'xxe-python-lxml-parser' 未在扫描结果中出现 |
| 6 | python/xxe/vulnerable.py | 28 | xxe-python-lxml-parse | 规则 'xxe-python-lxml-parse' 未在扫描结果中出现 |
| 7 | python/xxe/vulnerable.py | 35 | xxe-python-lxml-resolve-entities | 规则 'xxe-python-lxml-resolve-entities' 未在扫描结果中出现 |
| 8 | python/command-injection/vulnerable.py | 19 | priv-python-subprocess-shell-true | 规则 'priv-python-subprocess-shell-true' 未在扫描结果中出现 |
| 9 | python/command-injection/vulnerable.py | 27 | priv-python-os-system | 规则 'priv-python-os-system' 未在扫描结果中出现 |
| 10 | python/command-injection/vulnerable.py | 43 | priv-python-check-output-shell-true | 规则 'priv-python-check-output-shell-true' 未在扫描结果中出现 |
| 11 | typescript/xss/vulnerable.ts | 40 | xss-ts-outerhtml | 规则 'xss-ts-outerhtml' 未在扫描结果中出现 |
| 12 | typescript/xss/vulnerable.ts | 50 | xss-ts-dangerously-set-innerhtml | 规则 'xss-ts-dangerously-set-innerhtml' 未在扫描结果中出现 |
| 13 | typescript/ssrf/vulnerable.ts | 31 | ssrf-ts-http-get-user-input | 规则 'ssrf-ts-http-get-user-input' 未在扫描结果中出现 |

### 检出的非已知问题（误报）（35/48）

误报分类：安全文件误报 18 个 | 其他（规则 ID 不一致/重复检出/注释匹配） 17 个

| # | 文件 | 行号 | 规则 ID | 引擎 | 原因分析 |
|---|------|------|---------|------|----------|
| 1 | java/path-traversal/Safe.java | 24 | path-read-traversal | semgrep | 安全文件误报：未识别安全防护措施 |
| 2 | java/path-traversal/Safe.java | 25 | path-write-traversal | semgrep | 安全文件误报：未识别安全防护措施 |
| 3 | java/path-traversal/Safe.java | 32 | path-config-traversal | semgrep | 安全文件误报：未识别安全防护措施 |
| 4 | java/path-traversal/Safe.java | 47 | path-config-traversal | semgrep | 安全文件误报：未识别安全防护措施 |
| 5 | java/path-traversal/Vulnerable.java | 11 | path-traversal-pattern | builtin | 规则 ID 不匹配或重复检出 |
| 6 | java/path-traversal/Vulnerable.java | 27 | path-write-traversal | semgrep | 规则 ID 不匹配或重复检出 |
| 7 | java/path-traversal/Vulnerable.java | 28 | path-config-traversal | semgrep | 规则 ID 不匹配或重复检出 |
| 8 | java/path-traversal/Vulnerable.java | 36 | path-traversal-pattern | builtin | 规则 ID 不匹配或重复检出 |
| 9 | java/path-traversal/Vulnerable.java | 37 | path-write-traversal | semgrep | 规则 ID 不匹配或重复检出 |
| 10 | java/path-traversal/Vulnerable.java | 38 | path-config-traversal | semgrep | 规则 ID 不匹配或重复检出 |
| 11 | java/xxe/Vulnerable.java | 22 | xxe-java-document-builder-usage | semgrep | 规则 ID 不匹配或重复检出 |
| 12 | java/xxe/Vulnerable.java | 29 | xxe-java-document-builder-usage | semgrep | 规则 ID 不匹配或重复检出 |
| 13 | python/command-injection/safe.py | 18 | priv-python-subprocess-run | semgrep | 安全文件误报：未识别安全防护措施 |
| 14 | python/command-injection/safe.py | 30 | priv-python-subprocess-run | semgrep | 安全文件误报：未识别安全防护措施 |
| 15 | python/command-injection/safe.py | 42 | priv-python-subprocess-run | semgrep | 安全文件误报：未识别安全防护措施 |
| 16 | python/command-injection/safe.py | 53 | priv-python-subprocess-popen | semgrep | 安全文件误报：未识别安全防护措施 |
| 17 | python/command-injection/vulnerable.py | 22 | priv-python-subprocess-run | semgrep | 规则 ID 不匹配或重复检出 |
| 18 | python/command-injection/vulnerable.py | 30 | priv-python-os-system | builtin | 规则 ID 不匹配或重复检出 |
| 19 | python/path-traversal/safe.py | 26 | path-config-traversal | semgrep | 安全文件误报：未识别安全防护措施 |
| 20 | python/path-traversal/safe.py | 26 | path-read-traversal | semgrep | 安全文件误报：未识别安全防护措施 |
| 21 | python/path-traversal/safe.py | 39 | path-config-traversal | semgrep | 安全文件误报：未识别安全防护措施 |
| 22 | python/path-traversal/safe.py | 39 | path-read-traversal | semgrep | 安全文件误报：未识别安全防护措施 |
| 23 | python/path-traversal/safe.py | 52 | path-read-traversal | semgrep | 安全文件误报：未识别安全防护措施 |
| 24 | python/path-traversal/safe.py | 52 | path-write-traversal | semgrep | 安全文件误报：未识别安全防护措施 |
| 25 | python/path-traversal/vulnerable.py | 6 | path-traversal-pattern | builtin | 规则 ID 不匹配或重复检出 |
| 26 | python/path-traversal/vulnerable.py | 23 | path-read-traversal | semgrep | 规则 ID 不匹配或重复检出 |
| 27 | python/path-traversal/vulnerable.py | 30 | path-traversal-pattern | builtin | 规则 ID 不匹配或重复检出 |
| 28 | python/path-traversal/vulnerable.py | 32 | path-config-traversal | semgrep | 规则 ID 不匹配或重复检出 |
| 29 | python/path-traversal/vulnerable.py | 32 | path-read-traversal | semgrep | 规则 ID 不匹配或重复检出 |
| 30 | python/path-traversal/vulnerable.py | 40 | path-write-traversal | semgrep | 规则 ID 不匹配或重复检出 |
| 31 | python/xxe/vulnerable.py | 14 | xxe-python-lxml | semgrep | 规则 ID 不匹配或重复检出 |
| 32 | typescript/ssrf/safe.ts | 40 | ssrf-js-fetch | semgrep | 安全文件误报：未识别安全防护措施 |
| 33 | typescript/ssrf/safe.ts | 82 | ssrf-js-fetch | semgrep | 安全文件误报：未识别安全防护措施 |
| 34 | typescript/xss/safe.ts | 20 | xss-js-innerhtml | semgrep | 安全文件误报：未识别安全防护措施 |
| 35 | typescript/xss/safe.ts | 68 | xss-js-innerhtml | semgrep | 安全文件误报：未识别安全防护措施 |

## 按规则统计

| 规则 ID（已知问题） | 已知问题数 | 检出数 | 漏报数 | 误报数 | 检出率 |
|----------------------|-----------|--------|--------|--------|--------|
| path-config-traversal | 0 | 0 | 0 | 7 | N/A |
| path-read-traversal | 0 | 0 | 0 | 6 | N/A |
| path-traversal-java-file | 1 | 1 | 0 | 0 | 100% |
| path-traversal-java-weak-filter | 1 | 1 | 0 | 0 | 100% |
| path-traversal-pattern | 0 | 0 | 0 | 4 | N/A |
| path-traversal-python-os-path-join | 2 | 2 | 0 | 0 | 100% |
| path-traversal-python-weak-filter | 1 | 1 | 0 | 0 | 100% |
| path-write-traversal | 0 | 0 | 0 | 5 | N/A |
| priv-python-check-output-shell-true | 1 | 0 | 1 | 0 | 0% |
| priv-python-os-system | 1 | 0 | 1 | 1 | 0% |
| priv-python-popen-shell-true | 1 | 1 | 0 | 0 | 100% |
| priv-python-subprocess-popen | 0 | 0 | 0 | 1 | N/A |
| priv-python-subprocess-run | 0 | 0 | 0 | 4 | N/A |
| priv-python-subprocess-shell-true | 1 | 0 | 1 | 0 | 0% |
| sqli-java-statement-concat | 2 | 0 | 2 | 0 | 0% |
| ssrf-js-fetch | 0 | 0 | 0 | 2 | N/A |
| ssrf-ts-fetch-user-input | 2 | 2 | 0 | 0 | 100% |
| ssrf-ts-fetch-weak-filter | 1 | 1 | 0 | 0 | 100% |
| ssrf-ts-http-get-user-input | 1 | 0 | 1 | 0 | 0% |
| xss-java-servlet-output | 2 | 0 | 2 | 0 | 0% |
| xss-js-innerhtml | 0 | 0 | 0 | 2 | N/A |
| xss-ts-dangerously-set-innerhtml | 1 | 0 | 1 | 0 | 0% |
| xss-ts-document-write | 1 | 1 | 0 | 0 | 100% |
| xss-ts-innerhtml | 1 | 1 | 0 | 0 | 100% |
| xss-ts-outerhtml | 1 | 0 | 1 | 0 | 0% |
| xxe-java-document-builder | 2 | 2 | 0 | 0 | 100% |
| xxe-java-document-builder-usage | 0 | 0 | 0 | 2 | N/A |
| xxe-python-lxml | 0 | 0 | 0 | 1 | N/A |
| xxe-python-lxml-parse | 1 | 0 | 1 | 0 | 0% |
| xxe-python-lxml-parser | 1 | 0 | 1 | 0 | 0% |
| xxe-python-lxml-resolve-entities | 1 | 0 | 1 | 0 | 0% |

## 按语言统计

| 语言 | 已知问题数 | 检出数 | 漏报数 | 误报数 | 检出率 |
|------|-----------|--------|--------|--------|--------|
| Java | 8 | 4 | 4 | 12 | 50% |
| Python | 10 | 4 | 6 | 19 | 40% |
| Typescript | 8 | 5 | 3 | 4 | 62% |

## 安全文件误报分析

9 个安全文件中，**5 个**被误报，共产生 **18** 个误报（占总误报 51%）。

| 安全文件 | 误报数 | 误报规则 |
|----------|--------|----------|
| java/path-traversal/Safe.java | 4 | path-config-traversal, path-write-traversal, path-read-traversal |
| python/command-injection/safe.py | 4 | priv-python-subprocess-popen, priv-python-subprocess-run |
| python/path-traversal/safe.py | 6 | path-config-traversal, path-write-traversal, path-read-traversal |
| typescript/ssrf/safe.ts | 2 | ssrf-js-fetch |
| typescript/xss/safe.ts | 2 | xss-js-innerhtml |

无误报的安全文件：java/xxe/Safe.java, java/xss/Safe.java, java/sqli/Safe.java, python/xxe/safe.py

## 规则 ID 映射分析

以下展示了已知问题规则 ID 与扫描工具实际使用的规则 ID 之间的对应关系：

| 已知规则 ID | 扫描规则 ID | 涉及文件 | 匹配情况 |
|-------------|-------------|----------|----------|
| path-traversal-java-file | path-traversal-pattern | java/path-traversal/Vulnerable.java | ID 不一致 |
| path-traversal-java-weak-filter | path-traversal-pattern | java/path-traversal/Vulnerable.java | ID 不一致 |
| path-traversal-python-os-path-join | path-config-traversal | python/path-traversal/vulnerable.py | ID 不一致 |
| path-traversal-python-os-path-join | path-read-traversal | python/path-traversal/vulnerable.py | ID 不一致 |
| path-traversal-python-weak-filter | path-traversal-pattern | python/path-traversal/vulnerable.py | ID 不一致 |
| priv-python-popen-shell-true | priv-python-subprocess-popen | python/command-injection/vulnerable.py | ID 不一致 |
| ssrf-ts-fetch-user-input | ssrf-js-fetch | typescript/ssrf/vulnerable.ts | ID 不一致 |
| ssrf-ts-fetch-weak-filter | ssrf-js-fetch | typescript/ssrf/vulnerable.ts | ID 不一致 |
| xss-ts-document-write | xss-js-document-write | typescript/xss/vulnerable.ts | ID 不一致 |
| xss-ts-innerhtml | xss-js-innerhtml | typescript/xss/vulnerable.ts | ID 不一致 |
| xxe-java-document-builder | xxe-java-document-builder | java/xxe/Vulnerable.java | ID 一致 |
| xss-java-servlet-output | (无) | java/xss/Vulnerable.java | 规则缺失 |
| xss-java-servlet-output | (无) | java/xss/Vulnerable.java | 规则缺失 |
| sqli-java-statement-concat | (无) | java/sqli/Vulnerable.java | 规则缺失 |
| sqli-java-statement-concat | (无) | java/sqli/Vulnerable.java | 规则缺失 |
| xxe-python-lxml-parser | (无) | python/xxe/vulnerable.py | 规则缺失 |
| xxe-python-lxml-parse | (无) | python/xxe/vulnerable.py | 规则缺失 |
| xxe-python-lxml-resolve-entities | (无) | python/xxe/vulnerable.py | 规则缺失 |
| priv-python-subprocess-shell-true | (无) | python/command-injection/vulnerable.py | 规则缺失 |
| priv-python-os-system | (无) | python/command-injection/vulnerable.py | 规则缺失 |
| priv-python-check-output-shell-true | (无) | python/command-injection/vulnerable.py | 规则缺失 |
| xss-ts-outerhtml | (无) | typescript/xss/vulnerable.ts | 规则缺失 |
| xss-ts-dangerously-set-innerhtml | (无) | typescript/xss/vulnerable.ts | 规则缺失 |
| ssrf-ts-http-get-user-input | (无) | typescript/ssrf/vulnerable.ts | 规则缺失 |

## 改进建议

### P0 - 立即修复

1. **修复安全文件识别能力**：5/9 安全文件被误报（共 16 个误报），工具无法识别 `PreparedStatement`、`getCanonicalPath()`、`shlex.quote()`、`textContent`、域名白名单等安全防护模式。建议增加安全防护模式的识别逻辑，对已确认安全的代码路径进行豁免。

2. **补充 Java XSS 检测规则**：`xss-java-servlet-output` 规则完全未检出 Java Servlet 中的 XSS 漏洞（0/2），扫描结果中无任何 Java XSS 相关检出。需补充 `HttpServletResponse.getWriter().print()` 配合用户输入的 XSS 检测规则。

3. **补充 SQL 注入检测规则**：`sqli-java-statement-concat` 规则完全未检出 Java SQL 注入漏洞（0/2）。扫描结果中无任何 SQL 注入相关检出。需补充 `Statement.executeQuery()` 配合字符串拼接的检测规则。

4. **修复 Python 命令注入规则 ID 不一致**：扫描工具能检出 3/4 命令注入漏洞，但规则 ID 与预期不一致（如检出 `priv-python-subprocess-run` 而非 `priv-python-subprocess-shell-true`）。需统一规则 ID 或增加 `shell=True` 的细粒度判断。

### P1 - 短期优化

5. **统一规则 ID 命名体系**：扫描工具使用的规则 ID 与测试基准存在系统性差异（如 `path-write-traversal` vs `path-traversal-java-file`、`ssrf-js-fetch` vs `ssrf-ts-fetch-user-input`、`xss-js-innerhtml` vs `xss-ts-innerhtml`），建议建立规则 ID 映射表或统一命名规范。

6. **补充 Python XXE 细粒度规则**：扫描工具仅检出 `xxe-python-lxml`（import 级别），未检出 `XMLParser()` 配置、`etree.parse()` 调用、`resolve_entities` 参数等具体漏洞点。需增加细粒度检测。

7. **补充 TypeScript 高级 XSS 规则**：未检出 `outerHTML` 赋值和 `dangerouslySetInnerHTML` 两种 XSS 模式。需补充 `xss-ts-outerhtml` 和 `xss-ts-dangerously-set-innerhtml` 规则。

8. **补充 SSRF 非 fetch 规则**：`ssrf-ts-http-get-user-input` 规则未检出 Node.js `http.get()` 的 SSRF 漏洞。需补充非 fetch 类 HTTP 请求的检测。

9. **修复注释匹配问题**：builtin 引擎在 Java/Python path-traversal 文件中匹配了注释里的 `../` 模式（如 Javadoc 注释中的路径穿越描述），产生非漏洞代码行的误报。建议增加注释行过滤逻辑。

### P2 - 长期增强

10. **减少规则加载错误**：当前 83 条规则中有 25 条加载错误（30.1%），严重影响检出覆盖率。需排查并修复规则语法/兼容性问题。

11. **引入数据流分析**：当前规则主要基于模式匹配，缺乏数据流追踪能力。引入 taint analysis 可有效区分安全/不安全代码路径，同时提升检出率和精确率。

12. **补充 Python 路径穿越规则**：缺少对 `os.path.join()` 不安全使用模式的直接检测规则 `path-traversal-python-os-path-join`。

## 结论

**实际有效性评分**：35.1/100（基于宽松匹配 F1 Score）

**评价**：

- 检出率：50.0% -- 较差，大量漏洞未被检出
- 误报率：72.9% -- 较差，大量误报影响可信度
- 漏报率：50.0% -- 较差
- F1 Score：35.1%
- 严格匹配 F1 Score：5.4%（规则 ID 一致性问题导致大幅下降）

**核心发现**：


1. **实际检出能力（宽松匹配）**：工具在 26 个已知漏洞中检出了 13 个（50.0%），说明对部分漏洞类型有一定检出能力，但对 Java XSS、SQL 注入、Python XXE 细粒度检测等存在盲区。

2. **误报问题严重**：35 个误报中，18 个来自安全文件（占 51%），说明工具无法识别常见的安全防护模式。

3. **规则 ID 命名不一致**：宽松匹配检出 13 个，严格匹配仅 2 个，差异达 11 个。说明工具能定位漏洞位置，但规则 ID 体系与基准不一致。

4. **规则加载错误率高**：30.1% 的规则加载错误直接限制了检出能力上限。

**亮点**：

- Java XXE 检出率 100%（2/2），行号和规则 ID 均精确匹配
- TypeScript XSS innerHTML/document.write 检出率 100%（2/2）
- TypeScript SSRF fetch 类检出率 75%（3/4）
- Python 命令注入实际位置检出 3/4（但规则 ID 不一致）
- Java path-traversal 实际位置检出 2/2（但规则 ID 不一致）
