# 代码评审工具 -- 第 12 轮背靠背验证报告

**日期**: 2026-07-28  
**验证方法**: 双引擎（内置正则引擎 + Semgrep）独立扫描 vs 已知问题清单对比  
**测试代码库**: `test-validation/`（Java 8 个、Python 10 个、TypeScript 8 个已知漏洞，共 26 个）

---

## 1. 扫描结果概况

| 指标 | 数值 |
|------|------|
| 总检出问题数 | **51** |
| 内置引擎检出 | 51 |
| Semgrep 检出 | 51 |
| 双引擎共同检出 | 51 (100%) |
| 仅内置引擎 | 0 |
| 仅 Semgrep | 0 |
| 已知问题总数 | 26 |
| True Positives (TP) | 23 |
| False Positives (FP) | 28 |
| False Negatives (FN) | 3 |

**关键观察**: 两个引擎的检出完全一致（51/51），说明内置引擎和 Semgrep 规则已完全同步，双引擎融合未带来额外增量。

---

## 2. 核心指标对比（第 11 轮 vs 第 12 轮）

| 指标 | 第 11 轮 | 第 12 轮 | 变化 | 趋势 |
|------|---------|---------|------|------|
| **检出率 (Recall)** | 84.6% (22/26) | **88.5% (23/26)** | +3.9% | UP |
| **精确率 (Precision)** | 38.6% (22/57) | **45.1% (23/51)** | +6.5% | UP |
| **误报率 (FPR)** | 61.4% (35/57) | **54.9% (28/51)** | -6.5% | DOWN (good) |
| **漏报率 (FNR)** | 15.4% (4/26) | **11.5% (3/26)** | -3.9% | DOWN (good) |
| **F1 Score** | 53.0% | **59.7%** | +6.7% | UP |
| **总检出数** | 57 | **51** | -6 | DOWN (good) |

**评估**: 第 12 轮在所有核心指标上均有提升。总检出数减少 6 个（误报减少），同时多检出 1 个真实问题。精确率从 38.6% 提升到 45.1%，误报率从 61.4% 下降到 54.9%。

---

## 3. 目标达成情况

| 目标 | 目标值 | 实际值 | 状态 |
|------|--------|--------|------|
| 检出率 (Recall) | >= 90% | 88.5% | **FAIL** (差 1.5%) |
| 精确率 (Precision) | >= 60% | 45.1% | **FAIL** (差 14.9%) |
| F1 Score | >= 70% | 59.7% | **FAIL** (差 10.3%) |

**评估**: 三项指标均未达标。检出率接近目标（差 1.5%），但精确率和 F1 差距较大。核心瓶颈在于 **28 个误报**，其中 18 个出现在安全文件中。

---

## 4. 检出详情

### 4.1 已检出（True Positives）-- 23 个

| # | 文件 | 行号 | 规则 | 匹配方式 |
|---|------|------|------|----------|
| 1 | java/xxe/Vulnerable.java | 22 | xxe-java-document-builder-usage | 精确匹配 |
| 2 | java/xxe/Vulnerable.java | 29 | xxe-java-document-builder-usage | 精确匹配 |
| 3 | java/sqli/Vulnerable.java | 33 | sqli-java-statement-concat | 范围匹配 (30-34) |
| 4 | java/sqli/Vulnerable.java | 45 | sqli-java-statement-concat | 范围匹配 (42-47) |
| 5 | java/path-traversal/Vulnerable.java | 27 | path-traversal-java-file | 精确匹配 |
| 6 | java/path-traversal/Vulnerable.java | 36 | path-traversal-java-weak-filter | 精确匹配 |
| 7 | python/xxe/vulnerable.py | 20 | xxe-python-lxml-parser | 范围匹配 (14-22) |
| 8 | python/xxe/vulnerable.py | 28 | xxe-python-lxml-parse | 范围匹配 (14-29) |
| 9 | python/xxe/vulnerable.py | 35 | xxe-python-lxml-resolve-entities | 范围匹配 (14-37) |
| 10 | python/command-injection/vulnerable.py | 22 | priv-python-subprocess-shell-true | 精确匹配 |
| 11 | python/command-injection/vulnerable.py | 30 | priv-python-os-system | 精确匹配 |
| 12 | python/command-injection/vulnerable.py | 37 | priv-python-popen-shell-true | 精确匹配 |
| 13 | python/command-injection/vulnerable.py | 46 | priv-python-check-output-shell-true | 精确匹配 |
| 14 | python/path-traversal/vulnerable.py | 22 | path-traversal-python-os-path-join | 邻近匹配 (23) |
| 15 | python/path-traversal/vulnerable.py | 30 | path-traversal-python-weak-filter | 精确匹配 |
| 16 | python/path-traversal/vulnerable.py | 39 | path-traversal-python-os-path-join | 邻近匹配 (40) |
| 17 | typescript/xss/vulnerable.ts | 21 | xss-js-innerhtml | 精确匹配 |
| 18 | typescript/xss/vulnerable.ts | 30 | xss-js-document-write | 精确匹配 |
| 19 | typescript/xss/vulnerable.ts | 40 | xss-js-outerhtml | 精确匹配 |
| 20 | typescript/ssrf/vulnerable.ts | 22 | ssrf-js-fetch | 精确匹配 |
| 21 | typescript/ssrf/vulnerable.ts | 31 | ssrf-js-http-get | 精确匹配 |
| 22 | typescript/ssrf/vulnerable.ts | 44 | ssrf-js-fetch | 精确匹配 |
| 23 | typescript/ssrf/vulnerable.ts | 59 | ssrf-js-fetch-weak-filter | 精确匹配 |

### 4.2 漏报（False Negatives）-- 3 个

| # | 文件 | 行号 | 规则 | 描述 |
|---|------|------|------|------|
| 1 | java/xss/Vulnerable.java | 30 | xss-java-servlet-output | Servlet doGet 将用户输入拼接到 HTML 响应，反射型 XSS |
| 2 | java/xss/Vulnerable.java | 44 | xss-java-servlet-output | Servlet doPost 将用户输入拼接到 HTML 响应，反射型 XSS |
| 3 | typescript/xss/vulnerable.ts | 50 | xss-js-dangerouslysetinnerhtml | React dangerouslySetInnerHTML 直接设置用户输入 |

**漏报分析**:
- **Java XSS (2 个)**: 缺少 `xss-java-servlet-output` 规则。该规则需要检测 `request.getParameter()` 输入通过 `out.println()` 直接输出到 HTML 的模式。当前规则库中没有覆盖 Java Servlet XSS 模式。
- **React XSS (1 个)**: 缺少 `xss-js-dangerouslysetinnerhtml` 规则。当前规则库覆盖了 innerHTML、document.write、outerHTML，但未覆盖 React 特有的 `dangerouslySetInnerHTML` 属性。

### 4.3 误报（False Positives）-- 28 个

#### 安全文件误报 -- 18 个（占 64.3%）

| # | 文件 | 行号 | 规则 | 说明 |
|---|------|------|------|------|
| 1 | java/path-traversal/Safe.java | 18 | naming-java-constant-case | 命名规范提示，非安全漏洞 |
| 2 | java/path-traversal/Safe.java | 24 | path-read-traversal | 已做路径校验，误报 |
| 3 | java/path-traversal/Safe.java | 25 | path-write-traversal | 已做路径校验，误报 |
| 4 | java/path-traversal/Safe.java | 32 | path-config-traversal | 已做路径校验，误报 |
| 5 | java/path-traversal/Safe.java | 47 | path-config-traversal | 已做路径校验，误报 |
| 6 | python/command-injection/safe.py | 30 | priv-python-subprocess-run | 安全使用 subprocess（列表参数），误报 |
| 7 | python/command-injection/safe.py | 53 | null-python-none-check | 空值检查提示，非安全漏洞 |
| 8 | python/command-injection/safe.py | 53 | priv-python-subprocess-popen | 安全使用 Popen（列表参数），误报 |
| 9 | python/path-traversal/safe.py | 26 | path-config-traversal | 已做路径校验，误报 |
| 10 | python/path-traversal/safe.py | 26 | path-read-traversal | 已做路径校验，误报 |
| 11 | python/path-traversal/safe.py | 39 | path-config-traversal | 已做路径校验，误报 |
| 12 | python/path-traversal/safe.py | 39 | path-read-traversal | 已做路径校验，误报 |
| 13 | python/path-traversal/safe.py | 52 | path-read-traversal | 已做路径校验，误报 |
| 14 | python/path-traversal/safe.py | 52 | path-write-traversal | 已做路径校验，误报 |
| 15 | typescript/ssrf/safe.ts | 40 | ssrf-js-fetch | 已做 URL 白名单校验，误报 |
| 16 | typescript/ssrf/safe.ts | 82 | ssrf-js-fetch | 已做 URL 白名单校验，误报 |
| 17 | typescript/xss/safe.ts | 20 | xss-js-innerhtml | 安全代码中的 innerHTML 使用，误报 |
| 18 | typescript/xss/safe.ts | 68 | xss-js-innerhtml | 安全代码中的 innerHTML 使用，误报 |

#### 漏洞文件额外误报 -- 10 个（占 35.7%）

| # | 文件 | 行号 | 规则 | 说明 |
|---|------|------|------|------|
| 1 | java/path-traversal/Vulnerable.java | 20 | naming-java-constant-case | 命名规范提示，非安全漏洞 |
| 2 | java/path-traversal/Vulnerable.java | 28 | path-config-traversal | 同一漏洞点的额外规则触发 |
| 3 | java/path-traversal/Vulnerable.java | 37 | path-write-traversal | 同一漏洞点的额外规则触发 |
| 4 | java/path-traversal/Vulnerable.java | 38 | path-config-traversal | 同一漏洞点的额外规则触发 |
| 5 | python/command-injection/vulnerable.py | 37 | null-python-none-check | 空值检查提示，非安全漏洞 |
| 6 | python/path-traversal/vulnerable.py | 23 | path-read-traversal | 同一漏洞点的额外规则触发 |
| 7 | python/path-traversal/vulnerable.py | 32 | path-config-traversal | 同一漏洞点的额外规则触发 |
| 8 | python/path-traversal/vulnerable.py | 32 | path-read-traversal | 同一漏洞点的额外规则触发 |
| 9 | python/path-traversal/vulnerable.py | 40 | path-write-traversal | 同一漏洞点的额外规则触发 |
| 10 | python/xxe/vulnerable.py | 14 | xxe-python-lxml-parse | 与已匹配的 TP 重叠 |

---

## 5. 误报根因分析

### 5.1 安全文件误报（18 个）-- 最严重问题

**根因**: 规则引擎采用纯模式匹配（正则/Semgrep pattern），无法识别代码中的安全保护措施。

具体表现:
- **路径穿越规则**: 检测到 `new File()`、`os.path.join()` 等 API 调用就报警，不检查后续是否有 `getCanonicalPath()`、`realpath()` 等校验逻辑
- **命令注入规则**: 检测到 `subprocess.run()`、`subprocess.Popen()` 就报警，不区分 `shell=True` 和列表参数形式
- **SSRF 规则**: 检测到 `fetch()` 就报警，不检查是否有 URL 白名单校验前置
- **XSS 规则**: 检测到 `innerHTML` 就报警，不检查是否已做 encodeHtml() 编码

### 5.2 非安全类规则误报（3 个）

- `naming-java-constant-case` (2 个): 命名规范提示，不属于安全漏洞范畴
- `null-python-none-check` (2 个): 空值检查提示，不属于安全漏洞范畴

这些规则不应出现在安全扫描结果中，或应明确标记为代码质量类（非安全类）。

### 5.3 同一漏洞点多规则触发（7 个）

在 path-traversal 场景中，同一段代码同时触发 `path-read-traversal`、`path-write-traversal`、`path-config-traversal` 等多个规则，导致重复计数。

---

## 6. 改进效果评估

### 6.1 第 12 轮改进点

相比第 11 轮，第 12 轮取得了以下进展:
1. **总检出数减少 6 个**（57 -> 51），说明部分误报被消除
2. **多检出 1 个真实问题**（22 -> 23 TP），检出率提升
3. **精确率提升 6.5%**（38.6% -> 45.1%），误报问题有所缓解
4. **F1 Score 提升 6.7%**（53.0% -> 59.7%），整体效果改善

### 6.2 仍未解决的问题

| 问题 | 影响 | 严重程度 |
|------|------|----------|
| 安全文件 18 个误报 | 精确率无法突破 60% | **高** |
| 缺少 Java Servlet XSS 规则 | 漏报 2 个 | **中** |
| 缺少 React dangerouslySetInnerHTML 规则 | 漏报 1 个 | **中** |
| 非安全规则混入安全扫描 | 增加 3-4 个误报 | **低** |
| 同一漏洞点多规则重复触发 | 增加 7 个误报 | **中** |

---

## 7. 下一步建议

### 优先级 P0: 消除安全文件误报（预期减少 18 个 FP）

**方案 A: 增加安全模式排除条件**
- 路径穿越规则: 如果同文件中检测到 `getCanonicalPath()`、`realpath()`、`normalize()` + 前缀校验，则抑制报警
- 命令注入规则: 仅在 `shell=True` 或 `os.system()` 时报警，列表参数形式不报警
- SSRF 规则: 如果同文件中检测到 URL 白名单校验逻辑，则抑制报警
- XSS 规则: 如果 innerHTML 赋值前调用了 encodeHtml() 或 sanitize()，则抑制报警

**预期效果**: 精确率可提升至 ~70%，F1 可提升至 ~75%

### 优先级 P1: 补充缺失规则（预期增加 3 个 TP）

1. 新增 `xss-java-servlet-output` 规则: 检测 `request.getParameter()` -> `out.println()` 的拼接模式
2. 新增 `xss-js-dangerouslysetinnerhtml` 规则: 检测 React `dangerouslySetInnerHTML` 属性

**预期效果**: 检出率可提升至 100% (26/26)

### 优先级 P2: 规则去重与分类（预期减少 7-10 个 FP）

1. 对同一代码位置的多规则触发现有去重逻辑
2. 将 `naming-*`、`null-*` 等非安全规则标记为代码质量类，与安全规则分离
3. 在输出中增加 `category` 字段区分安全/质量/规范

### 优先级 P3: 提升双引擎差异化

当前两个引擎 100% 重叠。应优化规则使内置引擎和 Semgrep 各有侧重，利用互补性提高独立检出能力。

---

## 8. 总结

第 12 轮改进在所有指标上均优于第 11 轮，方向正确，但距离目标仍有差距:

| 指标 | 第 11 轮 | 第 12 轮 | 目标 | 差距 |
|------|---------|---------|------|------|
| 检出率 | 84.6% | 88.5% | >= 90% | -1.5% |
| 精确率 | 38.6% | 45.1% | >= 60% | -14.9% |
| F1 Score | 53.0% | 59.7% | >= 70% | -10.3% |

**核心瓶颈**: 安全文件误报（18 个）是阻碍精确率和 F1 达标的主要原因。解决安全文件误报后，预计精确率可达 ~70%，F1 可达 ~75%，将全面达标。
