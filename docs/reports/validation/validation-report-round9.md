# 第 9 轮背靠背验证报告

## 验证概况

- 验证时间：2026-07-28
- 已知问题数：26
- 检出问题数：43
- 验证方法：背靠背对比（行号容差 +/-2 行）
- 匹配模式：宽松匹配（文件 + 行号，忽略规则 ID 差异）+ 严格匹配（文件 + 行号 + 规则 ID）
- 扫描引擎：dual（builtin + semgrep 1.171.0）
- 加载规则数：83（其中 ~25 个规则 Semgrep 解析错误，占 ~30%）
- 扫描路径修复：修复了 dual_engine.py 和 rule_engine.py 中 semgrep 扫描根路径重复的 bug

## 核心指标对比

### 宽松匹配（文件 + 行号，评估实际检出能力）

| 指标 | 第 8 轮 | 第 9 轮 | 第 9 轮目标 | 变化 | 达标 |
|------|---------|---------|-------------|------|------|
| 检出率（Recall） | 50.0% | **50.0%** | 70%+ | +0.0% | 未达标 |
| 精确率（Precision） | 27.1% | **30.2%** | 50%+ | +3.1% | 未达标 |
| 误报率（FPR） | 72.9% | **69.8%** | 越低越好 | -3.1% | - |
| 漏报率（FNR） | 50.0% | **50.0%** | 越低越好 | +0.0% | - |
| F1 Score | 35.1% | **37.7%** | 60%+ | +2.6% | 未达标 |

### 严格匹配（文件 + 行号 + 规则 ID，评估规则精确匹配能力）

| 指标 | 第 8 轮 | 第 9 轮 | 变化 |
|------|---------|---------|------|
| 检出率（Recall） | 7.7%（2/26） | **23.1%（6/26）** | +15.4% |
| 精确率（Precision） | 4.2%（2/48） | **14.0%（6/43）** | +9.8% |
| F1 Score | 5.4% | **17.4%** | +12.0% |

> 严格匹配 F1 从 5.4% 提升到 17.4%（+12.0%），反映了规则 ID 一致性的改善。但宽松匹配的核心指标几乎没有变化。

## 检出详情

### 已检出的已知问题（13/26，宽松匹配）

| # | 文件 | 行号 | 期望规则 ID | 扫描规则 ID | 规则 ID 匹配 |
|---|------|------|-------------|-------------|-------------|
| 1 | java/xxe/Vulnerable.java | 22 | xxe-java-document-builder | xxe-java-document-builder | Y |
| 2 | java/xxe/Vulnerable.java | 29 | xxe-java-document-builder | xxe-java-document-builder | Y |
| 3 | java/path-traversal/Vulnerable.java | 27 | path-traversal-java-file | path-write-traversal | N |
| 4 | java/path-traversal/Vulnerable.java | 36 | path-traversal-java-weak-filter | path-traversal-pattern | N |
| 5 | python/command-injection/vulnerable.py | 35 | priv-python-popen-shell-true | priv-python-subprocess-popen | N |
| 6 | python/path-traversal/vulnerable.py | 22 | path-traversal-python-os-path-join | path-config-traversal | N |
| 7 | python/path-traversal/vulnerable.py | 30 | path-traversal-python-weak-filter | path-traversal-pattern | N |
| 8 | python/path-traversal/vulnerable.py | 39 | path-traversal-python-os-path-join | path-read-traversal | N |
| 9 | typescript/xss/vulnerable.ts | 21 | xss-js-innerhtml | xss-js-innerhtml | Y |
| 10 | typescript/xss/vulnerable.ts | 30 | xss-js-document-write | xss-js-document-write | Y |
| 11 | typescript/ssrf/vulnerable.ts | 22 | ssrf-js-fetch | ssrf-js-fetch | Y |
| 12 | typescript/ssrf/vulnerable.ts | 44 | ssrf-js-fetch | ssrf-js-fetch | Y |
| 13 | typescript/ssrf/vulnerable.ts | 59 | ssrf-js-fetch-weak-filter | ssrf-js-fetch | N |

> 其中规则 ID 也精确匹配的：6/13（第 8 轮为 2/13，改善 +4）

### 未检出的已知问题（漏报）（13/26）

| # | 文件 | 行号 | 规则 ID | 漏报原因 |
|---|------|------|---------|----------|
| 1 | java/xss/Vulnerable.java | 30 | xss-java-servlet-output | 规则模式不匹配：规则检测 `getWriter().write()` 但代码使用 `PrintWriter.println()` |
| 2 | java/xss/Vulnerable.java | 44 | xss-java-servlet-output | 同上 |
| 3 | java/sqli/Vulnerable.java | 33 | sqli-java-statement-concat | 规则模式不匹配：规则检测 `"SELECT ... " + $VAR` 但代码拼接模式不同 |
| 4 | java/sqli/Vulnerable.java | 45 | sqli-java-statement-concat | 同上 |
| 5 | python/xxe/vulnerable.py | 20 | xxe-python-lxml-parser | 规则缺失：无 `XMLParser()` 配置检测规则 |
| 6 | python/xxe/vulnerable.py | 28 | xxe-python-lxml-parse | 规则缺失：无 `etree.parse()` 无安全解析器检测规则 |
| 7 | python/xxe/vulnerable.py | 35 | xxe-python-lxml-resolve-entities | 规则缺失：无 `resolve_entities=True` 检测规则 |
| 8 | python/command-injection/vulnerable.py | 19 | priv-python-subprocess-shell-true | 规则模式不匹配：规则检测 `subprocess.run(...)` 但模式过窄 |
| 9 | python/command-injection/vulnerable.py | 27 | priv-python-os-system | 规则缺失：无 `os.system()` 检测规则 |
| 10 | python/command-injection/vulnerable.py | 43 | priv-python-check-output-shell-true | 规则缺失：无 `subprocess.check_output(shell=True)` 检测规则 |
| 11 | typescript/xss/vulnerable.ts | 40 | xss-js-outerhtml | 规则缺失：无 `outerHTML` 赋值检测规则 |
| 12 | typescript/xss/vulnerable.ts | 50 | xss-js-dangerouslysetinnerhtml | 规则模式不匹配：`pattern-regex` 与实际代码格式不符 |
| 13 | typescript/ssrf/vulnerable.ts | 31 | ssrf-js-http-get | 规则缺失：无 `http.get()` SSRF 检测规则 |

### 检出的非已知问题（误报）（30/43）

误报分类：安全文件误报 18 个（60%） | 重复检出/额外模式匹配 12 个（40%）

| # | 文件 | 行号 | 规则 ID | 安全文件 | 原因分析 |
|---|------|------|---------|----------|----------|
| 1 | java/path-traversal/Safe.java | 24 | path-read-traversal | Y | 未识别 getCanonicalPath() 安全防护 |
| 2 | java/path-traversal/Safe.java | 25 | path-write-traversal | Y | 未识别路径校验安全防护 |
| 3 | java/path-traversal/Safe.java | 32 | path-config-traversal | Y | 未识别 normalize() 安全防护 |
| 4 | java/path-traversal/Safe.java | 47 | path-config-traversal | Y | 未识别路径校验安全防护 |
| 5 | java/path-traversal/Vulnerable.java | 28 | path-config-traversal | N | 额外检出（非已知问题行） |
| 6 | java/path-traversal/Vulnerable.java | 37 | path-write-traversal | N | 额外检出（非已知问题行） |
| 7 | java/path-traversal/Vulnerable.java | 38 | path-config-traversal | N | 额外检出（非已知问题行） |
| 8 | java/xxe/Vulnerable.java | 22 | xxe-java-document-builder-usage | N | 同一位置重复检出（不同规则） |
| 9 | java/xxe/Vulnerable.java | 29 | xxe-java-document-builder-usage | N | 同一位置重复检出（不同规则） |
| 10 | python/command-injection/safe.py | 18 | priv-python-subprocess-run | Y | 未识别列表参数（shell=False）安全防护 |
| 11 | python/command-injection/safe.py | 30 | priv-python-subprocess-run | Y | 未识别 shlex.quote() 安全防护 |
| 12 | python/command-injection/safe.py | 42 | priv-python-subprocess-run | Y | 未识别列表参数安全防护 |
| 13 | python/command-injection/safe.py | 53 | priv-python-subprocess-popen | Y | 未识别列表参数安全防护 |
| 14 | python/command-injection/vulnerable.py | 22 | priv-python-subprocess-run | N | 额外检出（非已知问题行） |
| 15 | python/command-injection/vulnerable.py | 30 | priv-python-os-system | N | 额外检出（行号偏差） |
| 16 | python/path-traversal/safe.py | 26 | path-config-traversal | Y | 未识别 realpath() 安全防护 |
| 17 | python/path-traversal/safe.py | 26 | path-read-traversal | Y | 未识别 realpath() 安全防护 |
| 18 | python/path-traversal/safe.py | 39 | path-config-traversal | Y | 未识别 pathlib.Path.resolve() 安全防护 |
| 19 | python/path-traversal/safe.py | 39 | path-read-traversal | Y | 未识别 pathlib.Path.resolve() 安全防护 |
| 20 | python/path-traversal/safe.py | 52 | path-read-traversal | Y | 未识别路径校验安全防护 |
| 21 | python/path-traversal/safe.py | 52 | path-write-traversal | Y | 未识别路径校验安全防护 |
| 22 | python/path-traversal/vulnerable.py | 23 | path-read-traversal | N | 额外检出（非已知问题行） |
| 23 | python/path-traversal/vulnerable.py | 32 | path-config-traversal | N | 额外检出（非已知问题行） |
| 24 | python/path-traversal/vulnerable.py | 32 | path-read-traversal | N | 额外检出（非已知问题行） |
| 25 | python/path-traversal/vulnerable.py | 40 | path-write-traversal | N | 额外检出（非已知问题行） |
| 26 | python/xxe/vulnerable.py | 14 | xxe-python-lxml | N | import 级别检出（非具体漏洞行） |
| 27 | typescript/ssrf/safe.ts | 40 | ssrf-js-fetch | Y | 未识别域名白名单安全防护 |
| 28 | typescript/ssrf/safe.ts | 82 | ssrf-js-fetch | Y | 未识别 URL 校验安全防护 |
| 29 | typescript/xss/safe.ts | 20 | xss-js-innerhtml | Y | 未识别 textContent 安全防护 |
| 30 | typescript/xss/safe.ts | 68 | xss-js-innerhtml | Y | 未识别 encodeHtml() 安全防护 |

## 按语言统计

| 语言 | 已知问题数 | 检出数 | 漏报数 | 误报数 | 检出率 |
|------|-----------|--------|--------|--------|--------|
| Java | 8 | 4 | 4 | 9 | 50% |
| Python | 10 | 4 | 6 | 17 | 40% |
| TypeScript | 8 | 5 | 3 | 4 | 62% |

## 安全文件误报分析

9 个安全文件中，**5 个**被误报，共产生 **18** 个误报（占总误报 60%）。

| 安全文件 | 误报数 | 误报规则 |
|----------|--------|----------|
| java/path-traversal/Safe.java | 4 | path-config-traversal, path-write-traversal, path-read-traversal |
| python/command-injection/safe.py | 4 | priv-python-subprocess-run, priv-python-subprocess-popen |
| python/path-traversal/safe.py | 6 | path-config-traversal, path-write-traversal, path-read-traversal |
| typescript/ssrf/safe.ts | 2 | ssrf-js-fetch |
| typescript/xss/safe.ts | 2 | xss-js-innerhtml |

无误报的安全文件：java/xxe/Safe.java, java/xss/Safe.java, java/sqli/Safe.java, python/xxe/safe.py

## 规则 ID 映射分析

| 已知规则 ID | 扫描规则 ID | 涉及文件 | ID 匹配 |
|-------------|-------------|----------|---------|
| xxe-java-document-builder | xxe-java-document-builder | java/xxe/Vulnerable.java | Y |
| xss-js-innerhtml | xss-js-innerhtml | typescript/xss/vulnerable.ts | Y |
| xss-js-document-write | xss-js-document-write | typescript/xss/vulnerable.ts | Y |
| ssrf-js-fetch | ssrf-js-fetch | typescript/ssrf/vulnerable.ts | Y |
| path-traversal-java-file | path-write-traversal | java/path-traversal/Vulnerable.java | N |
| path-traversal-java-weak-filter | path-traversal-pattern | java/path-traversal/Vulnerable.java | N |
| path-traversal-python-os-path-join | path-config-traversal / path-read-traversal | python/path-traversal/vulnerable.py | N |
| path-traversal-python-weak-filter | path-traversal-pattern | python/path-traversal/vulnerable.py | N |
| priv-python-popen-shell-true | priv-python-subprocess-popen | python/command-injection/vulnerable.py | N |
| ssrf-js-fetch-weak-filter | ssrf-js-fetch | typescript/ssrf/vulnerable.ts | N |

## 改进效果评估

### 第 9 轮 vs 第 8 轮变化

| 维度 | 第 8 轮 | 第 9 轮 | 变化 | 评估 |
|------|---------|---------|------|------|
| 总检出数 | 48 | 43 | -5 | 略有改善 |
| 检出已知问题 | 13/26 | 13/26 | 0 | 无变化 |
| 误报数 | 35 | 30 | -5 | 略有改善 |
| 安全文件误报 | 18 | 18 | 0 | 无变化 |
| 规则 ID 精确匹配 | 2/13 | 6/13 | +4 | 显著改善 |
| 严格匹配 F1 | 5.4% | 17.4% | +12.0% | 显著改善 |
| 宽松匹配 F1 | 35.1% | 37.7% | +2.6% | 微幅改善 |

### 改善点

1. **规则 ID 一致性提升**：严格匹配 F1 从 5.4% 提升到 17.4%（+12.0%），规则 ID 精确匹配从 2 个增加到 6 个。TypeScript XSS/SSRF 的规则 ID 现在与基准一致。
2. **总检出数减少**：从 48 减少到 43，减少了 5 个误报，精确率从 27.1% 提升到 30.2%。
3. **扫描路径修复**：修复了 dual_engine.py 和 rule_engine.py 中 semgrep 扫描根路径重复的 bug，使扫描能正常执行。

### 未改善的问题

1. **检出率停滞**：50.0% 未变，仍有 13 个已知漏洞未检出。
2. **安全文件误报未改善**：18 个安全文件误报完全未变，工具仍无法识别常见安全防护模式。
3. **核心目标全部未达标**：
   - 检出率 50.0% vs 目标 70%（差距 20%）
   - 精确率 30.2% vs 目标 50%（差距 19.8%）
   - F1 Score 37.7% vs 目标 60%（差距 22.3%）

## 下一步建议

### P0 - 提升检出率（目标：从 50% 到 70%+）

需新增/修复以下规则以额外检出至少 6 个已知问题：

1. **补充 `os.system()` 检测规则**：新增 `priv-python-os-system` 规则，检测 `os.system($CMD)` 模式。可解决 1 个漏报。
2. **补充 `subprocess.check_output(shell=True)` 检测规则**：新增 `priv-python-check-output-shell-true` 规则。可解决 1 个漏报。
3. **修复 `subprocess.run(shell=True)` 检测**：当前规则模式过窄，需匹配 `subprocess.run($CMD, shell=True, ...)` 模式。可解决 1 个漏报。
4. **补充 Java XSS `PrintWriter.println()` 检测**：当前规则仅检测 `getWriter().write()`，需扩展到 `println()` 等变体。可解决 2 个漏报。
5. **修复 SQL 注入模式匹配**：当前 `"SELECT ... " + $VAR` 模式无法匹配实际代码中的多行拼接。可解决 2 个漏报。
6. **补充 `outerHTML` 检测规则**：新增 `xss-js-outerhtml` 规则。可解决 1 个漏报。
7. **修复 `dangerouslySetInnerHTML` 正则**：调整 pattern-regex 以匹配实际代码格式。可解决 1 个漏报。
8. **补充 `http.get()` SSRF 检测**：新增 `ssrf-js-http-get` 规则。可解决 1 个漏报。
9. **补充 Python XXE 细粒度规则**：新增 `XMLParser()` 配置、`etree.parse()` 无安全解析器、`resolve_entities=True` 检测。可解决 3 个漏报。

### P1 - 降低误报率（目标：从 69.8% 到 50% 以下）

10. **增加安全防护模式识别**：为 path-traversal 规则增加 pattern-not，识别 `getCanonicalPath()`、`realpath()`、`Path.resolve()`、`normalize()` 等安全防护。可消除 10 个安全文件误报。
11. **增加命令注入安全防护识别**：为 subprocess 规则增加 pattern-not，识别列表参数形式（`shell=False`）和 `shlex.quote()` 等安全防护。可消除 4 个安全文件误报。
12. **增加 SSRF 安全防护识别**：为 ssrf 规则增加 pattern-not，识别域名白名单、URL 校验等安全防护。可消除 2 个安全文件误报。
13. **增加 XSS 安全防护识别**：为 xss 规则增加 pattern-not，识别 `textContent`、`encodeHtml()` 等安全防护。可消除 2 个安全文件误报。

### P2 - 规则质量提升

14. **减少 Semgrep 规则解析错误**：当前 ~30% 规则解析失败，修复 `$org`、`$param` 等元变量命名问题。
15. **消除同位置重复检出**：java/xxe/Vulnerable.java 的 22 行和 29 行各被 2 条规则检出，需优化规则粒度避免重复。

## 结论

**实际有效性评分**：37.7/100（基于宽松匹配 F1 Score）

**评价**：

- 检出率：50.0% -- 较差，与第 8 轮持平，大量漏洞仍未检出
- 误报率：69.8% -- 较差，略有改善（-3.1%），但仍过高
- F1 Score：37.7% -- 较差，微幅改善（+2.6%），距目标 60% 差距显著
- 严格匹配 F1：17.4% -- 显著改善（+12.0%），反映规则 ID 一致性提升

**核心发现**：

1. **检出率零增长**：第 9 轮改进在规则 ID 一致性上取得进展（严格匹配 F1 +12.0%），但对检出率没有贡献。13 个漏报的根本原因是规则缺失或模式不匹配。
2. **误报问题依然严重**：60% 的误报来自安全文件，工具无法识别 `getCanonicalPath()`、`shlex.quote()`、`textContent`、域名白名单等常见安全防护模式。
3. **与目标差距显著**：三项核心指标（检出率 50% vs 70%、精确率 30% vs 50%、F1 38% vs 60%）均未达标，需要大幅度改进。
4. **改善方向明确**：P0 建议中列出的 9 项规则新增/修复可覆盖全部 13 个漏报中的至少 12 个；P1 建议中的安全防护模式识别可消除 18 个安全文件误报。
