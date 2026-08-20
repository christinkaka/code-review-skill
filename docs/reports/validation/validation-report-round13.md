# 第 13 轮背靠背验证报告

**日期**: 2026-07-28  
**扫描引擎**: 双引擎 (内置正则引擎 + Semgrep)  
**测试代码库**: test-validation/  
**已知问题总数**: 26  
**安全文件总数**: 9  

---

## 1. 扫描结果概况

| 指标 | 数值 |
|------|------|
| 扫描总检出 | 44 |
| 内置引擎检出 | 44 |
| Semgrep 引擎检出 | 44 |
| 双引擎共同检出 | 44 |
| 仅内置引擎 | 0 |
| 仅 Semgrep 引擎 | 0 |

两个引擎的检出结果完全一致，说明规则在两个引擎间已完全同步。

---

## 2. 核心指标对比

### 2.1 三轮对比表

| 指标 | 第 12 轮 | 第 13 轮 | 第 13 轮目标 | 变化 | 达标 |
|------|---------|---------|-------------|------|------|
| 检出率 (Recall) | 88.5% (23/26) | **88.5% (23/26)** | 95%+ | 0.0% | FAIL |
| 精确率 (Precision) | 45.1% (23/51) | **52.3% (23/44)** | 70%+ | +7.2% | FAIL |
| 误报率 (FPR) | 54.9% (28/51) | **47.7% (21/44)** | - | -7.2% | - |
| 漏报率 (FNR) | 11.5% (3/26) | **11.5% (3/26)** | - | 0.0% | - |
| F1 Score | 59.7% | **65.7%** | 80%+ | +6.0% | FAIL |

### 2.2 趋势分析

- **精确率提升**: 从 45.1% 提升到 52.3%（+7.2pp），总检出数从 51 降至 44，减少了 7 个误报
- **检出率持平**: 仍为 88.5%，3 个漏报与第 12 轮相同
- **F1 小幅提升**: 从 59.7% 提升到 65.7%（+6.0pp），但距离 80% 目标仍有较大差距
- **三项核心指标均未达标**

---

## 3. 检出详情

### 3.1 已检出 (True Positives: 23/26)

| # | 文件 | 行号 | 规则 | 匹配方式 |
|---|------|------|------|---------|
| 1 | java/xxe/Vulnerable.java | 22 | xxe-java-document-builder-usage | 精确 |
| 2 | java/xxe/Vulnerable.java | 29 | xxe-java-document-builder-usage | 精确 |
| 3 | java/sqli/Vulnerable.java | 33 | sqli-java-statement-concat | 行号容差 (扫描行30) |
| 4 | java/sqli/Vulnerable.java | 45 | sqli-java-statement-concat | 行号容差 (扫描行42) |
| 5 | java/path-traversal/Vulnerable.java | 27 | path-traversal-java-file | 精确 |
| 6 | java/path-traversal/Vulnerable.java | 36 | path-traversal-java-weak-filter | 精确 |
| 7 | python/xxe/vulnerable.py | 20 | xxe-python-lxml-parser | 同类匹配 (扫描行14) |
| 8 | python/xxe/vulnerable.py | 28 | xxe-python-lxml-parse | 同类匹配 (扫描行14) |
| 9 | python/xxe/vulnerable.py | 35 | xxe-python-lxml-resolve-entities | 同类匹配 (扫描行14) |
| 10 | python/command-injection/vulnerable.py | 22 | priv-python-subprocess-shell-true | 精确 |
| 11 | python/command-injection/vulnerable.py | 30 | priv-python-os-system | 精确 |
| 12 | python/command-injection/vulnerable.py | 37 | priv-python-popen-shell-true | 精确 |
| 13 | python/command-injection/vulnerable.py | 46 | priv-python-check-output-shell-true | 精确 |
| 14 | python/path-traversal/vulnerable.py | 22 | path-traversal-python-os-path-join | 行号容差 (扫描行23) |
| 15 | python/path-traversal/vulnerable.py | 30 | path-traversal-python-weak-filter | 精确 |
| 16 | python/path-traversal/vulnerable.py | 39 | path-traversal-python-os-path-join | 行号容差 (扫描行40) |
| 17 | typescript/xss/vulnerable.ts | 21 | xss-js-innerhtml | 精确 |
| 18 | typescript/xss/vulnerable.ts | 30 | xss-js-document-write | 精确 |
| 19 | typescript/xss/vulnerable.ts | 40 | xss-js-outerhtml | 精确 |
| 20 | typescript/ssrf/vulnerable.ts | 22 | ssrf-js-fetch | 精确 |
| 21 | typescript/ssrf/vulnerable.ts | 31 | ssrf-js-http-get | 精确 |
| 22 | typescript/ssrf/vulnerable.ts | 44 | ssrf-js-fetch | 精确 |
| 23 | typescript/ssrf/vulnerable.ts | 59 | ssrf-js-fetch-weak-filter | 精确 |

### 3.2 漏报 (False Negatives: 3/26)

| # | 文件 | 行号 | 规则 | 描述 |
|---|------|------|------|------|
| 1 | java/xss/Vulnerable.java | 30 | xss-java-servlet-output | Servlet doGet 将 request.getParameter() 直接拼接到 HTML 响应，反射型 XSS |
| 2 | java/xss/Vulnerable.java | 44 | xss-java-servlet-output | Servlet doPost 将用户输入直接拼接到 HTML 响应，反射型 XSS |
| 3 | typescript/xss/vulnerable.ts | 50 | xss-js-dangerouslysetinnerhtml | dangerouslySetInnerHTML 直接设置用户输入，React XSS |

**漏报分析**:
- **Java XSS (2个)**: 缺少 `xss-java-servlet-output` 规则。该规则需要检测 `response.getWriter().println()` 与 `request.getParameter()` 的拼接模式。当前规则库中没有针对 Java Servlet XSS 的检出规则。
- **React XSS (1个)**: 缺少 `xss-js-dangerouslysetinnerhtml` 规则。该规则需要检测 React 组件中 `dangerouslySetInnerHTML` 的使用。当前规则库中未覆盖此模式。

### 3.3 误报 (False Positives: 21/44)

#### 安全文件误报 (14 个)

| # | 文件 | 行号 | 误报类型 | 说明 |
|---|------|------|---------|------|
| 1 | java/path-traversal/Safe.java | 18 | naming | 常量命名规范误报，Safe 文件中的合法常量 |
| 2 | java/path-traversal/Safe.java | 25 | path-traversal | 文件写入操作误报，已用 getCanonicalPath() 校验 |
| 3 | java/path-traversal/Safe.java | 32 | path-traversal | 配置文件路径误报，已有路径校验保护 |
| 4 | java/path-traversal/Safe.java | 47 | path-traversal | 配置文件路径误报，已有路径校验保护 |
| 5 | python/command-injection/safe.py | 30 | command-injection | subprocess.run() 误报，使用的是 shell=False 安全模式 |
| 6 | python/command-injection/safe.py | 53 | null-safety | 返回值判空误报，非安全相关规则 |
| 7 | python/command-injection/safe.py | 53 | command-injection | subprocess.Popen() 误报，使用的是安全参数列表 |
| 8 | python/path-traversal/safe.py | 26 | path-traversal | 配置文件路径误报，已用 realpath() 校验 |
| 9 | python/path-traversal/safe.py | 39 | path-traversal | 配置文件路径误报，已用 resolve() 校验 |
| 10 | python/path-traversal/safe.py | 52 | path-traversal | 文件写入路径误报，已用 realpath() 校验 |
| 11 | typescript/ssrf/safe.ts | 40 | ssrf | fetch 请求误报，已有域名白名单校验 |
| 12 | typescript/ssrf/safe.ts | 82 | ssrf | fetch 请求误报，已有域名白名单校验 |
| 13 | typescript/xss/safe.ts | 20 | xss | innerHTML 误报，已使用 textContent 替代 |
| 14 | typescript/xss/safe.ts | 68 | xss | innerHTML 误报，已使用 textContent 替代 |

#### 非安全文件误报 (7 个)

| # | 文件 | 行号 | 误报类型 | 说明 |
|---|------|------|---------|------|
| 1 | java/path-traversal/Vulnerable.java | 20 | naming | 常量命名规范，不在已知问题范围内 |
| 2 | java/path-traversal/Vulnerable.java | 28 | path-traversal | 额外的 path-config-traversal，非已知问题 |
| 3 | java/path-traversal/Vulnerable.java | 37 | path-traversal | 额外的 path-write-traversal，非已知问题 |
| 4 | java/path-traversal/Vulnerable.java | 38 | path-traversal | 额外的 path-config-traversal，非已知问题 |
| 5 | python/command-injection/vulnerable.py | 37 | null-safety | 返回值判空，非安全相关规则 |
| 6 | python/path-traversal/vulnerable.py | 32 | path-traversal | 额外的 path-config-traversal，非已知问题 |
| 7 | python/xxe/vulnerable.py | 14 | xxe | resolve_entities 规则行号偏差过大 |

---

## 4. 安全文件误报统计

| 安全文件 | 期望问题数 | 实际误报数 | 状态 |
|----------|-----------|-----------|------|
| java/xxe/Safe.java | 0 | 0 | CLEAN |
| java/xss/Safe.java | 0 | 0 | CLEAN |
| java/sqli/Safe.java | 0 | 0 | CLEAN |
| java/path-traversal/Safe.java | 0 | **4** | FAIL |
| python/xxe/safe.py | 0 | 0 | CLEAN |
| python/command-injection/safe.py | 0 | **3** | FAIL |
| python/path-traversal/safe.py | 0 | **3** | FAIL |
| typescript/xss/safe.ts | 0 | **2** | FAIL |
| typescript/ssrf/safe.ts | 0 | **2** | FAIL |

**9 个安全文件中有 5 个被误报**，安全文件误报率 55.6%。

---

## 5. 按漏洞类型统计

### 5.1 检出率

| 漏洞类型 | 已知总数 | 检出数 | 漏报数 | 检出率 |
|----------|---------|-------|-------|-------|
| command-injection | 4 | 4 | 0 | 100.0% |
| path-traversal | 5 | 5 | 0 | 100.0% |
| sqli | 2 | 2 | 0 | 100.0% |
| ssrf | 4 | 4 | 0 | 100.0% |
| xxe | 5 | 5 | 0 | 100.0% |
| **xss** | **6** | **3** | **3** | **50.0%** |

XSS 是唯一存在漏报的漏洞类型，检出率仅 50%。

### 5.2 误报分布

| 误报类型 | 数量 | 占比 |
|----------|------|------|
| path-traversal | 10 | 47.6% |
| naming | 2 | 9.5% |
| command-injection | 2 | 9.5% |
| null-safety | 2 | 9.5% |
| ssrf | 2 | 9.5% |
| xss | 2 | 9.5% |
| xxe | 1 | 4.8% |

**path-traversal 类规则贡献了 47.6% 的误报**，是误报的最大来源。

---

## 6. 改进效果评估

### 6.1 第 13 轮改进成效

与第 12 轮相比：
- **总检出数减少**: 51 -> 44（减少 7 个），说明部分误报被消除
- **精确率提升**: 45.1% -> 52.3%（+7.2pp），有改善但幅度有限
- **检出率未变**: 仍为 88.5%，3 个漏报未解决
- **F1 提升**: 59.7% -> 65.7%（+6.0pp），小幅进步

### 6.2 目标达成情况

| 目标 | 当前值 | 目标值 | 差距 | 状态 |
|------|-------|-------|------|------|
| 检出率 | 88.5% | 95%+ | -6.5pp | 未达标 |
| 精确率 | 52.3% | 70%+ | -17.7pp | 未达标 |
| F1 Score | 65.7% | 80%+ | -14.3pp | 未达标 |

**三项核心指标均未达到第 13 轮目标。**

### 6.3 核心问题诊断

**问题 1: path-traversal 规则过度泛化 (影响: 10 个误报)**
- `path-config-traversal` 和 `path-write-traversal` 规则在已做好路径校验的安全代码上仍然报警
- 规则仅检测 "用户输入 + 文件操作" 的模式，但无法识别后续的路径校验逻辑（如 `getCanonicalPath()`、`realpath()`、`normalize()` 等）
- 这是最影响精确率的根源

**问题 2: 缺少 Java XSS 和 React XSS 规则 (影响: 3 个漏报)**
- 缺少 `xss-java-servlet-output` 规则：无法检测 Servlet 中 `getParameter()` + `println()` 的 XSS 模式
- 缺少 `xss-js-dangerouslysetinnerhtml` 规则：无法检测 React 组件中 `dangerouslySetInnerHTML` 的使用

**问题 3: 非安全相关规则混入 (影响: 4 个误报)**
- `naming-java-constant-case` (2 个): 命名规范不属于安全扫描范畴
- `null-python-none-check` (2 个): 空值检查不属于安全扫描范畴
- 这些规则增加了噪声，稀释了精确率

**问题 4: 安全文件上下文感知不足 (影响: 14 个安全文件误报)**
- 规则引擎缺乏对安全保护措施的识别能力
- 无法区分 "有漏洞的代码模式" 和 "已加防护的代码模式"
- 5/9 的安全文件被错误标记

---

## 7. 下一步建议

### 7.1 优先级 P0: 修复 path-traversal 规则 (预期消除 10 个误报)

1. **增加安全模式豁免**: 当检测到路径校验代码（`getCanonicalPath()`、`realpath()`、`normalize()`、`startsWith()` 等）时，抑制 path-traversal 告警
2. **收窄规则匹配范围**: `path-config-traversal` 和 `path-write-traversal` 规则应仅在无后续校验时报警
3. **预期效果**: 精确率从 52.3% 提升至约 67%（23/34）

### 7.2 优先级 P1: 新增缺失的 XSS 规则 (预期减少 3 个漏报)

1. **新增 `xss-java-servlet-output` 规则**: 检测 `request.getParameter()` -> `response.getWriter().println()` 的拼接模式
2. **新增 `xss-js-dangerouslysetinnerhtml` 规则**: 检测 React 组件中 `dangerouslySetInnerHTML` 与用户输入的关联
3. **预期效果**: 检出率从 88.5% 提升至 100%（26/26）

### 7.3 优先级 P2: 移除非安全规则 (预期消除 4 个误报)

1. **移除或禁用 `naming-java-constant-case`**: 命名规范不属于安全评审范畴
2. **移除或禁用 `null-python-none-check`**: 空值检查不属于安全评审范畴
3. **预期效果**: 精确率进一步提升至约 74%（23/31）

### 7.4 优先级 P3: 增强安全文件识别

1. **增加安全模式库**: 建立常见安全防护措施的识别模式（参数化查询、HTML 编码、路径规范化等）
2. **上下文感知**: 规则引擎在检出后应检查是否存在对应的安全防护代码
3. **预期效果**: 安全文件误报降至 0

### 7.5 预期第 14 轮指标

如果上述 P0-P2 改进全部落地：
- 检出率: 26/26 = **100%** (目标 95%+, PASS)
- 精确率: 26/~31 = **~84%** (目标 70%+, PASS)
- F1 Score: **~91%** (目标 80%+, PASS)

---

## 附录: 数据文件

- 扫描结果: `test-validation/scan-results-round13.json`
- 已知问题: `test-validation/known-issues.json`
- 评估脚本: `/Users/chris/.trae-cn/work/6a670005e08c6f1bf753c84d/evaluate_round13.py`
