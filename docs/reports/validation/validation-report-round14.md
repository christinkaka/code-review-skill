# 第 14 轮背靠背验证报告

**日期**: 2026-07-28  
**扫描引擎**: 双引擎 (内置正则引擎 + Semgrep)  
**测试代码库**: test-validation/  
**已知问题总数**: 26  
**安全文件总数**: 9  

---

## 1. 扫描结果概况

| 指标 | 数值 |
|------|------|
| 扫描总检出 | 35 |
| 内置引擎检出 | 35 |
| Semgrep 引擎检出 | 35 |
| 双引擎共同检出 | 35 |
| 仅内置引擎 | 0 |
| 仅 Semgrep 引擎 | 0 |

与第 13 轮 (44 个) 相比，总检出数减少了 9 个 (20.5%)，说明部分误报规则已被移除或收窄。两个引擎的检出结果仍然完全一致。

---

## 2. 核心指标对比

### 2.1 三轮对比表

| 指标 | 第 12 轮 | 第 13 轮 | 第 14 轮 | 第 14 轮目标 | R13->R14 变化 | 达标 |
|------|---------|---------|---------|-------------|--------------|------|
| 检出率 (Recall) | 88.5% (23/26) | 88.5% (23/26) | **80.8% (21/26)** | 100% | -7.7pp | FAIL |
| 精确率 (Precision) | 45.1% (23/51) | 52.3% (23/44) | **61.8% (21/34)** | 84%+ | +9.5pp | FAIL |
| 误报率 (FPR) | 54.9% (28/51) | 47.7% (21/44) | **38.2% (13/34)** | - | -9.5pp | - |
| 漏报率 (FNR) | 11.5% (3/26) | 11.5% (3/26) | **19.2% (5/26)** | - | +7.7pp | - |
| F1 Score | 59.7% | 65.7% | **70.0%** | 91%+ | +4.3pp | FAIL |

### 2.2 趋势分析

- **精确率显著提升**: 从 52.3% 提升到 61.8% (+9.5pp)，总检出数从 44 降至 35，减少了 9 个误报
- **检出率下降**: 从 88.5% 降至 80.8% (-7.7pp)，漏报从 3 个增加到 5 个
- **F1 稳步提升**: 从 65.7% 提升到 70.0% (+4.3pp)，连续三轮上升
- **三项核心指标均未达到第 14 轮目标**

---

## 3. 检出详情

### 3.1 已检出 (True Positives: 21/26)

| # | 文件 | 行号 | 规则 | 匹配方式 |
|---|------|------|------|---------|
| 1 | java/xxe/Vulnerable.java | 22 | xxe-java-document-builder-usage | 精确 |
| 2 | java/xxe/Vulnerable.java | 29 | xxe-java-document-builder-usage | 精确 |
| 3 | java/sqli/Vulnerable.java | 33 | sqli-java-statement-concat | 行号容差 (扫描行30) |
| 4 | java/sqli/Vulnerable.java | 45 | sqli-java-statement-concat | 行号容差 (扫描行42) |
| 5 | java/path-traversal/Vulnerable.java | 36 | path-traversal-java-weak-filter | 精确 (path-traversal-pattern) |
| 6 | python/xxe/vulnerable.py | 20 | xxe-python-lxml-parser | 同类匹配 (扫描行14) |
| 7 | python/xxe/vulnerable.py | 28 | xxe-python-lxml-parse | 同类匹配 (扫描行14) |
| 8 | python/xxe/vulnerable.py | 35 | xxe-python-lxml-resolve-entities | 同类匹配 (扫描行14) |
| 9 | python/command-injection/vulnerable.py | 22 | priv-python-subprocess-shell-true | 精确 (subprocess-run) |
| 10 | python/command-injection/vulnerable.py | 30 | priv-python-os-system | 精确 |
| 11 | python/command-injection/vulnerable.py | 37 | priv-python-popen-shell-true | 精确 (subprocess-popen) |
| 12 | python/command-injection/vulnerable.py | 46 | priv-python-check-output-shell-true | 精确 |
| 13 | python/path-traversal/vulnerable.py | 22 | path-traversal-python-os-path-join | 行号容差 (扫描行23) |
| 14 | python/path-traversal/vulnerable.py | 30 | path-traversal-python-weak-filter | 精确 (path-traversal-pattern) |
| 15 | typescript/xss/vulnerable.ts | 21 | xss-js-innerhtml | 精确 |
| 16 | typescript/xss/vulnerable.ts | 30 | xss-js-document-write | 精确 |
| 17 | typescript/xss/vulnerable.ts | 40 | xss-js-outerhtml | 精确 |
| 18 | typescript/ssrf/vulnerable.ts | 22 | ssrf-js-fetch | 精确 |
| 19 | typescript/ssrf/vulnerable.ts | 31 | ssrf-js-http-get | 精确 |
| 20 | typescript/ssrf/vulnerable.ts | 44 | ssrf-js-fetch | 精确 |
| 21 | typescript/ssrf/vulnerable.ts | 59 | ssrf-js-fetch-weak-filter | 精确 (ssrf-js-fetch) |

### 3.2 漏报 (False Negatives: 5/26)

| # | 文件 | 行号 | 规则 | 描述 | 原因 |
|---|------|------|------|------|------|
| 1 | java/xss/Vulnerable.java | 30 | xss-java-servlet-output | Servlet doGet XSS | 缺少规则 |
| 2 | java/xss/Vulnerable.java | 44 | xss-java-servlet-output | Servlet doPost XSS | 缺少规则 |
| 3 | java/path-traversal/Vulnerable.java | 27 | path-traversal-java-file | 直接 File 构造路径穿越 | 规则丢失 (R13 曾检出) |
| 4 | python/path-traversal/vulnerable.py | 39 | path-traversal-python-os-path-join | 写入文件路径穿越 | 规则未覆盖此位置 |
| 5 | typescript/xss/vulnerable.ts | 50 | xss-js-dangerouslysetinnerhtml | React dangerouslySetInnerHTML XSS | 缺少规则 |

**漏报分析**:
- **Java XSS (2个)**: 缺少 `xss-java-servlet-output` 规则。需要检测 `request.getParameter()` + `response.getWriter().println()` 拼接模式。
- **Java 路径穿越 (1个)**: `path-traversal-java-file` 规则在第 13 轮曾检出此问题 (行号容差匹配)，但第 14 轮中该规则不再产生匹配结果。规则可能被修改或移除。
- **Python 路径穿越 (1个)**: `path-traversal-python-os-path-join` 规则未覆盖写入文件场景 (line 39)。最近的扫描检出行 (line 32) 距离 7 行，超出容差范围。
- **React XSS (1个)**: 缺少 `xss-js-dangerouslysetinnerhtml` 规则。

### 3.3 误报 (False Positives: 13/35)

#### 安全文件误报 (10 个)

| # | 文件 | 行号 | 误报规则 | 说明 |
|---|------|------|---------|------|
| 1 | java/path-traversal/Safe.java | 32 | path-config-traversal | 已用 getCanonicalPath() 校验 |
| 2 | java/path-traversal/Safe.java | 47 | path-config-traversal | 已用 getCanonicalPath() 校验 |
| 3 | python/command-injection/safe.py | 30 | priv-python-subprocess-run | shell=False 安全模式 |
| 4 | python/command-injection/safe.py | 53 | priv-python-subprocess-popen | 安全参数列表模式 |
| 5 | python/path-traversal/safe.py | 26 | path-config-traversal | 已用 realpath() 校验 |
| 6 | python/path-traversal/safe.py | 39 | path-config-traversal | 已用 realpath() 校验 |
| 7 | typescript/ssrf/safe.ts | 40 | ssrf-js-fetch | 已有域名白名单校验 |
| 8 | typescript/ssrf/safe.ts | 82 | ssrf-js-fetch | 已有域名白名单校验 |
| 9 | typescript/xss/safe.ts | 20 | xss-js-innerhtml | 已使用 textContent 替代 |
| 10 | typescript/xss/safe.ts | 68 | xss-js-innerhtml | 已使用 textContent 替代 |

#### 非安全文件误报 (3 个)

| # | 文件 | 行号 | 误报规则 | 说明 |
|---|------|------|---------|------|
| 1 | java/path-traversal/Vulnerable.java | 28 | path-config-traversal | 额外的 config 路径检测 |
| 2 | java/path-traversal/Vulnerable.java | 38 | path-config-traversal | 额外的 config 路径检测 |
| 3 | python/path-traversal/vulnerable.py | 32 | path-config-traversal | 额外的 config 路径检测 |

---

## 4. 安全文件误报统计

| 安全文件 | 期望问题数 | 实际误报数 | 状态 |
|----------|-----------|-----------|------|
| java/xxe/Safe.java | 0 | 0 | CLEAN |
| java/xss/Safe.java | 0 | 0 | CLEAN |
| java/sqli/Safe.java | 0 | 0 | CLEAN |
| java/path-traversal/Safe.java | 0 | **2** | FAIL |
| python/xxe/safe.py | 0 | 0 | CLEAN |
| python/command-injection/safe.py | 0 | **2** | FAIL |
| python/path-traversal/safe.py | 0 | **2** | FAIL |
| typescript/xss/safe.ts | 0 | **2** | FAIL |
| typescript/ssrf/safe.ts | 0 | **2** | FAIL |

**9 个安全文件中有 5 个被误报**，安全文件误报率 55.6% (与第 13 轮持平)。

---

## 5. 按漏洞类型统计

### 5.1 检出率

| 漏洞类型 | 已知总数 | 检出数 | 漏报数 | 检出率 | 状态 |
|----------|---------|-------|-------|-------|------|
| command-injection | 4 | 4 | 0 | **100%** | FULL |
| sqli | 2 | 2 | 0 | **100%** | FULL |
| ssrf | 4 | 4 | 0 | **100%** | FULL |
| xxe | 5 | 5 | 0 | **100%** | FULL |
| **path-traversal** | **5** | **3** | **2** | **60%** | PARTIAL |
| **xss** | **6** | **3** | **3** | **50%** | PARTIAL |

command-injection、sqli、ssrf、xxe 四类漏洞达到 100% 检出。path-traversal 和 xss 存在漏报。

### 5.2 误报分布

| 误报规则 | 数量 | 安全文件 | 非安全文件 |
|----------|------|---------|-----------|
| path-config-traversal | 7 | 4 | 3 |
| ssrf-js-fetch | 2 | 2 | 0 |
| xss-js-innerhtml | 2 | 2 | 0 |
| priv-python-subprocess-run | 1 | 1 | 0 |
| priv-python-subprocess-popen | 1 | 1 | 0 |

**path-config-traversal 贡献了 53.8% 的误报 (7/13)**，是最大误报来源。

---

## 6. 改进效果评估

### 6.1 第 14 轮改进成效

与第 13 轮相比，第 14 轮的改进体现在以下方面:

**正面改进**:
- **总检出数减少**: 44 -> 35 (-20.5%)，误报数量减少
- **精确率提升**: 52.3% -> 61.8% (+9.5pp)，为三轮中最大增幅
- **F1 持续提升**: 65.7% -> 70.0% (+4.3pp)
- **naming 规则误报消除**: 第 13 轮的 2 个 naming-java-constant-case 误报已消除
- **null-safety 规则误报消除**: 第 13 轮的 2 个 null-python-none-check 误报已消除
- **path-traversal 误报减少**: 从 10 个降至 7 个 (-30%)
- **command-injection 安全文件误报减少**: 从 3 个降至 2 个

**退步问题**:
- **检出率下降**: 88.5% -> 80.8% (-7.7pp)，漏报从 3 个增至 5 个
- **path-traversal-java-file 规则丢失**: 第 13 轮能检出的 Java File 路径穿越问题，本轮无法检出
- **python/path-traversal 写入场景漏报**: line 39 的文件写入路径穿越未检出

### 6.2 目标达成情况

| 目标 | 当前值 | 目标值 | 差距 | 状态 |
|------|-------|-------|------|------|
| 检出率 | 80.8% | 100% | -19.2pp | 未达标 |
| 精确率 | 61.8% | 84%+ | -22.2pp | 未达标 |
| F1 Score | 70.0% | 91%+ | -21.0pp | 未达标 |

**三项核心指标均未达到第 14 轮目标。**

### 6.3 核心问题诊断

**问题 1: 缺少 3 条安全规则 (影响: 4 个漏报)**
- `xss-java-servlet-output`: 无法检测 Java Servlet 中 getParameter() + println() 的 XSS 模式 (2 个漏报)
- `xss-js-dangerouslysetinnerhtml`: 无法检测 React dangerouslySetInnerHTML 的使用 (1 个漏报)
- `path-traversal-java-file`: 规则丢失或被修改，无法检测 `new File(base, userInput)` 模式 (1 个漏报)

**问题 2: path-config-traversal 规则过度泛化 (影响: 7 个误报)**
- 在已做好路径校验的安全代码上仍然报警
- 无法识别 getCanonicalPath()、realpath()、resolve() 等安全防护措施
- 贡献了 53.8% 的总误报

**问题 3: 安全文件上下文感知不足 (影响: 10 个安全文件误报)**
- 5/9 的安全文件被错误标记
- 规则引擎缺乏对安全保护措施的识别能力
- 无法区分 "有漏洞的代码模式" 和 "已加防护的代码模式"

**问题 4: python/path-traversal 写入场景覆盖不足 (影响: 1 个漏报)**
- os.path.join 规则仅覆盖读取场景 (line 22)，未覆盖写入场景 (line 39)
- 写入操作的路径穿越同样危险，需要同等关注

---

## 7. 下一步建议

### 7.1 优先级 P0: 恢复/修复丢失的规则 (预期恢复 1 个检出)

1. **恢复 `path-traversal-java-file` 规则**: 该规则在第 13 轮能检出 `new File(BASE_DIR, fileName)` 模式，但在第 14 轮失效。需排查规则文件中的变更。
2. **扩展 `path-traversal-python-os-path-join`**: 增加对写入场景 (line 39) 的覆盖，或增加 `path-write-traversal` 规则。
3. **预期效果**: 检出率从 80.8% 提升至 84.6% (22/26)

### 7.2 优先级 P1: 新增缺失的 XSS 规则 (预期恢复 3 个检出)

1. **新增 `xss-java-servlet-output` 规则**: 检测 `request.getParameter()` -> `response.getWriter().println()` 的拼接模式
2. **新增 `xss-js-dangerouslysetinnerhtml` 规则**: 检测 React 组件中 `dangerouslySetInnerHTML` 与用户输入的关联
3. **预期效果**: 检出率从 84.6% 提升至 96.2% (25/26)

### 7.3 优先级 P2: 修复 path-config-traversal 误报 (预期消除 7 个误报)

1. **增加安全模式豁免**: 当检测到路径校验代码 (getCanonicalPath()、realpath()、normalize()、startsWith() 等) 时，抑制 path-config-traversal 告警
2. **收窄匹配范围**: 仅在无后续路径校验时报警
3. **预期效果**: 精确率从 61.8% 提升至约 78.8% (21/27)

### 7.4 优先级 P3: 增强安全文件上下文感知 (预期消除 10 个安全文件误报)

1. **增加安全模式库**: 建立常见安全防护措施的识别模式
2. **上下文感知**: 规则引擎在检出后检查是否存在对应的安全防护代码
3. **预期效果**: 安全文件误报降至 0，精确率进一步提升

### 7.5 预期第 15 轮指标

如果上述 P0-P2 改进全部落地:
- 检出率: 25/26 = **96.2%** (目标 100%, 接近)
- 精确率: 25/~27 = **~92.6%** (目标 84%+, PASS)
- F1 Score: **~94.3%** (目标 91%+, PASS)

如果 P0-P3 全部落地:
- 检出率: 25/26 = **96.2%**
- 精确率: 25/~25 = **~100%**
- F1 Score: **~98.0%**

---

## 附录: 数据文件

- 扫描结果: `test-validation/scan-results-round14.json`
- 已知问题: `test-validation/known-issues.json`
- 评估结果: `test-validation/validation-results-round14.json`
- 评估脚本: `/Users/chris/.trae-cn/work/6a670005e08c6f1bf753c84d/evaluate_round14_definitive.py`
