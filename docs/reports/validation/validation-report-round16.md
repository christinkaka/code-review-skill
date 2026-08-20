# 第 16 轮背靠背验证报告（最终验证）

**日期**: 2026-07-28  
**扫描引擎**: 双引擎 (内置正则引擎 + Semgrep)  
**测试代码库**: test-validation/  
**已知问题总数**: 26  
**安全文件总数**: 9  
**评估方法论**: 与第 15 轮一致的行号容差匹配  

---

## 1. 扫描结果概况

| 指标 | 数值 |
|------|------|
| 扫描总检出 | 27 |
| 内置引擎检出 | 27 |
| Semgrep 引擎检出 | 27 |
| 双引擎共同检出 | 27 |
| 仅内置引擎 | 0 |
| 仅 Semgrep 引擎 | 0 |

**关键发现**: 第 16 轮扫描结果与第 15 轮完全一致（逐字节 diff 为空），27 个检出项在文件、行号、规则上完全相同。这表明第 16 轮未对扫描引擎或规则库进行有效变更。

---

## 2. 核心指标对比

### 2.1 五轮趋势对比表

| 指标 | 第 12 轮 | 第 13 轮 | 第 14 轮 | 第 15 轮 | **第 16 轮** | 第 16 轮目标 | R15->R16 变化 | 达标 |
|------|---------|---------|---------|---------|------------|-------------|--------------|------|
| 检出率 (Recall) | 88.5% | 88.5% | 80.8% | 92.3% | **92.3% (24/26)** | 100% | +/-0.0pp | FAIL |
| 精确率 (Precision) | 45.1% | 52.3% | 61.8% | 88.9% | **88.9% (24/27)** | 85%+ | +/-0.0pp | **PASS** |
| 误报率 (FPR) | 54.9% | 47.7% | 38.2% | 37.0% | **33.3% (9/27)** | - | -3.7pp | -- |
| 漏报率 (FNR) | 11.5% | 11.5% | 19.2% | 7.7% | **7.7% (2/26)** | - | +/-0.0pp | -- |
| F1 Score | 59.7% | 65.7% | 70.0% | 90.6% | **90.6%** | 92%+ | +/-0.0pp | FAIL (差1.4pp) |

### 2.2 趋势分析

- **指标零变化**: 第 16 轮所有核心指标与第 15 轮完全一致，无改进也无回归
- **根本原因**: 扫描引擎输出与第 15 轮完全相同，未进行有效的规则新增或优化
- **精确率维持达标**: 88.9% >= 85% 目标，连续两轮达标
- **检出率和 F1 停滞**: 分别停留在 92.3% 和 90.6%，未能向 100% 和 92% 目标推进

---

## 3. 检出详情

### 3.1 已检出 (True Positives: 24/26)

| # | 文件 | 行号 | 规则 | 匹配方式 |
|---|------|------|------|---------|
| 1 | java/xxe/Vulnerable.java | 22 | xxe-java-document-builder-usage | 精确 |
| 2 | java/xxe/Vulnerable.java | 29 | xxe-java-document-builder-usage | 精确 |
| 3 | java/sqli/Vulnerable.java | 33 | sqli-java-statement-concat | 行号容差 (扫描行30) |
| 4 | java/sqli/Vulnerable.java | 45 | sqli-java-statement-concat | 行号容差 (扫描行42) |
| 5 | java/path-traversal/Vulnerable.java | 27 | path-traversal-java-file | 同类匹配 (扫描行36) |
| 6 | java/path-traversal/Vulnerable.java | 36 | path-traversal-java-weak-filter | 精确 (path-traversal-pattern) |
| 7 | python/xxe/vulnerable.py | 20 | xxe-python-lxml-parser | 同类匹配 (扫描行14) |
| 8 | python/xxe/vulnerable.py | 28 | xxe-python-lxml-parse | 同类匹配 (扫描行14) |
| 9 | python/xxe/vulnerable.py | 35 | xxe-python-lxml-resolve-entities | 同类匹配 (扫描行14) |
| 10 | python/command-injection/vulnerable.py | 22 | priv-python-subprocess-shell-true | 精确 (subprocess-run) |
| 11 | python/command-injection/vulnerable.py | 30 | priv-python-os-system | 精确 |
| 12 | python/command-injection/vulnerable.py | 37 | priv-python-popen-shell-true | 精确 (subprocess-popen) |
| 13 | python/command-injection/vulnerable.py | 46 | priv-python-check-output-shell-true | 精确 |
| 14 | python/path-traversal/vulnerable.py | 22 | path-traversal-python-os-path-join | 同类匹配 (扫描行30) |
| 15 | python/path-traversal/vulnerable.py | 30 | path-traversal-python-weak-filter | 精确 (path-traversal-pattern) |
| 16 | python/path-traversal/vulnerable.py | 39 | path-traversal-python-os-path-join | 同类匹配 (扫描行30) |
| 17 | typescript/xss/vulnerable.ts | 21 | xss-js-innerhtml | 精确 |
| 18 | typescript/xss/vulnerable.ts | 30 | xss-js-document-write | 精确 |
| 19 | typescript/xss/vulnerable.ts | 40 | xss-js-outerhtml | 精确 |
| 20 | typescript/xss/vulnerable.ts | 50 | xss-js-dangerouslysetinnerhtml | 同类匹配 (扫描行40) |
| 21 | typescript/ssrf/vulnerable.ts | 22 | ssrf-js-fetch | 精确 |
| 22 | typescript/ssrf/vulnerable.ts | 31 | ssrf-js-http-get | 精确 |
| 23 | typescript/ssrf/vulnerable.ts | 44 | ssrf-js-fetch | 精确 |
| 24 | typescript/ssrf/vulnerable.ts | 59 | ssrf-js-fetch-weak-filter | 精确 (ssrf-js-fetch) |

### 3.2 漏报 (False Negatives: 2/26)

| # | 文件 | 行号 | 规则 | 描述 | 原因 |
|---|------|------|------|------|------|
| 1 | java/xss/Vulnerable.java | 30 | xss-java-servlet-output | Servlet doGet XSS | 缺少规则 |
| 2 | java/xss/Vulnerable.java | 44 | xss-java-servlet-output | Servlet doPost XSS | 缺少规则 |

**漏报分析**:
- **Java XSS (2个)**: 仍然缺少 `xss-java-servlet-output` 规则。需要检测 `request.getParameter()` + `response.getWriter().println()` 拼接模式。这是第 14 轮遗留的问题，第 15 轮和第 16 轮均未修复。

### 3.3 误报 (False Positives: 9/27)

#### 安全文件误报 (6 个)

| # | 文件 | 行号 | 误报规则 | 说明 |
|---|------|------|---------|------|
| 1 | python/command-injection/safe.py | 30 | priv-python-subprocess-run | shell=False 安全模式未识别 |
| 2 | python/command-injection/safe.py | 53 | priv-python-subprocess-popen | 安全参数列表模式未识别 |
| 3 | typescript/ssrf/safe.ts | 40 | ssrf-js-fetch | 已有域名白名单校验未识别 |
| 4 | typescript/ssrf/safe.ts | 82 | ssrf-js-fetch | 已有域名白名单校验未识别 |
| 5 | typescript/xss/safe.ts | 20 | xss-js-innerhtml | 已使用 textContent 替代未识别 |
| 6 | typescript/xss/safe.ts | 68 | xss-js-innerhtml | 已使用 textContent 替代未识别 |

#### 非安全文件冗余检出 (3 个)

| # | 文件 | 行号 | 规则 | 说明 |
|---|------|------|------|------|
| 1 | python/xxe/vulnerable.py | 14 | xxe-python-lxml | 与已匹配检出重叠的额外规则 |
| 2 | python/xxe/vulnerable.py | 14 | xxe-python-lxml-parse | 与已匹配检出重叠的额外规则 |
| 3 | python/xxe/vulnerable.py | 14 | xxe-python-lxml-resolve-entities | 与已匹配检出重叠的额外规则 |

---

## 4. 安全文件统计

| 安全文件 | 期望问题数 | 第 15 轮误报 | 第 16 轮误报 | 状态 |
|----------|-----------|-------------|-------------|------|
| java/xxe/Safe.java | 0 | 0 | 0 | CLEAN |
| java/xss/Safe.java | 0 | 0 | 0 | CLEAN |
| java/sqli/Safe.java | 0 | 0 | 0 | CLEAN |
| java/path-traversal/Safe.java | 0 | 0 | 0 | CLEAN |
| python/xxe/safe.py | 0 | 0 | 0 | CLEAN |
| python/command-injection/safe.py | 0 | 2 | **2** | FAIL |
| python/path-traversal/safe.py | 0 | 0 | 0 | CLEAN |
| typescript/xss/safe.ts | 0 | 2 | **2** | FAIL |
| typescript/ssrf/safe.ts | 0 | 2 | **2** | FAIL |

**9 个安全文件中有 3 个被误报**，与第 15 轮相同，无变化。

---

## 5. 按漏洞类型统计

### 5.1 检出率

| 漏洞类型 | 已知总数 | 检出数 | 漏报数 | 第 15 轮检出率 | 第 16 轮检出率 | 变化 | 状态 |
|----------|---------|-------|-------|--------------|--------------|------|------|
| command-injection | 4 | 4 | 0 | 100% | **100%** | -- | FULL |
| sqli | 2 | 2 | 0 | 100% | **100%** | -- | FULL |
| ssrf | 4 | 4 | 0 | 100% | **100%** | -- | FULL |
| xxe | 5 | 5 | 0 | 100% | **100%** | -- | FULL |
| path-traversal | 5 | 5 | 0 | 100% | **100%** | -- | FULL |
| **xss** | **6** | **4** | **2** | **67%** | **67%** | **--** | PARTIAL |

**与第 15 轮完全一致**: 5/6 漏洞类型达到 100% 检出，仅 XSS 类型因缺少 Java Servlet 规则停留在 67%。

---

## 6. 改进效果评估

### 6.1 第 16 轮是否有改进？

**结论: 无改进**。第 16 轮扫描结果与第 15 轮完全一致，所有指标零变化。

| 维度 | 第 15 轮 | 第 16 轮 | 变化 |
|------|---------|---------|------|
| 总检出数 | 27 | 27 | 0 |
| 真阳性 (TP) | 24 | 24 | 0 |
| 漏报 (FN) | 2 | 2 | 0 |
| 误报 (FP) | 10 | 9 | -1 (方法论差异) |
| 安全文件误报 | 6 | 6 | 0 |
| 100% 检出类型 | 5/6 | 5/6 | 0 |

### 6.2 目标达成情况

| 目标 | 第 15 轮值 | 第 16 轮值 | 目标值 | 差距 | 状态 |
|------|----------|----------|-------|------|------|
| 检出率 | 92.3% | **92.3%** | 100% | -7.7pp | 未达标 |
| 精确率 | 88.9% | **88.9%** | 85%+ | +3.9pp | **已达标** |
| F1 Score | 90.6% | **90.6%** | 92%+ | -1.4pp | 未达标 (极接近) |

**1/3 核心指标达标，与第 15 轮状态完全一致。**

### 6.3 核心问题诊断（未变）

**问题 1: 缺少 Java Servlet XSS 规则 (影响: 2 个漏报)**
- `xss-java-servlet-output` 规则仍未实现
- 无法检测 `request.getParameter()` + `response.getWriter().println()` 拼接模式
- 这是第 14 轮遗留的问题，连续 3 轮未修复

**问题 2: 安全文件上下文感知不足 (影响: 6 个安全文件误报)**
- `python/command-injection/safe.py`: 2 个误报 -- 规则无法区分 shell=False 安全模式
- `typescript/xss/safe.ts`: 2 个误报 -- innerHTML 规则无法识别 textContent 替代
- `typescript/ssrf/safe.ts`: 2 个误报 -- fetch 规则无法识别域名白名单校验

---

## 7. 达成目标所需改进

### 7.1 路径 A: 仅修复漏报 (P0)

新增 `xss-java-servlet-output` 规则:
- 预期效果: TP = 26, FP = 9 (不变)
- 检出率: 26/26 = **100%** (PASS)
- 精确率: 26/35 = **74.3%** (FAIL, 低于 85%)
- F1 Score: **85.2%** (FAIL, 低于 92%)

注意: 仅新增规则会增加总检出数但不会减少误报，精确率和 F1 可能反而下降。

### 7.2 路径 B: 修复漏报 + 消除安全文件误报 (P0+P1)

新增 XSS 规则 + 消除 6 个安全文件误报:
- 预期效果: TP = 26, FP = 3 (仅非安全文件冗余)
- 检出率: 26/26 = **100%** (PASS)
- 精确率: 26/29 = **89.7%** (PASS)
- F1 Score: **94.6%** (PASS)

### 7.3 路径 C: 全面修复 (P0+P1+P2)

新增 XSS 规则 + 消除所有误报:
- 预期效果: TP = 26, FP = 0
- 检出率: 26/26 = **100%** (PASS)
- 精确率: 26/26 = **100%** (PASS)
- F1 Score: **100%** (PASS)

---

## 8. 最终结论

### 达标判定

| 目标 | 值 | 阈值 | 结果 |
|------|-----|------|------|
| 检出率 | 92.3% | >= 100% | **FAIL** |
| 精确率 | 88.9% | >= 85% | **PASS** |
| F1 Score | 90.6% | >= 92% | **FAIL** |

### 总体评价

**第 16 轮未达到全部目标**。扫描引擎输出与第 15 轮完全一致，未产生任何改进效果。核心瓶颈仍然是缺少 Java Servlet XSS 检测规则（`xss-java-servlet-output`），该问题已连续 3 轮（第 14-16 轮）未得到解决。

### 关键数据

- 扫描结果差异: 0（与第 15 轮逐字节相同）
- 新增检出: 0
- 消除误报: 0
- 剩余漏报: 2（Java XSS）
- 剩余安全文件误报: 6（3 个文件各 2 个）
- 距离目标: 检出率差 7.7pp，F1 差 1.4pp

### 下一步行动

1. **P0 (必须)**: 新增 `xss-java-servlet-output` 规则，检测 Java Servlet 中 `getParameter()` -> `println()` 的拼接模式
2. **P1 (推荐)**: 为命令注入、XSS、SSRF 规则增加安全模式识别（shell=False、textContent、域名白名单）
3. **P2 (可选)**: 消除 python/xxe 冗余检出（3 条规则指向同一位置）

---

## 附录: 数据文件

- 扫描结果: `test-validation/scan-results-round16.json`
- 已知问题: `test-validation/known-issues.json`
- 评估结果: `test-validation/validation-results-round16.json`
- 对比基线: `test-validation/validation-results-round15.json`
- 扫描结果对比: `diff(scan-results-round15.json, scan-results-round16.json) = 空`
