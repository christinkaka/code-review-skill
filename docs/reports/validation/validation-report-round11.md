# 代码评审工具 -- 第 11 轮验证报告

**日期**: 2026-07-28
**验证方法**: 背靠背独立验证（Agent 1 独立扫描 + Agent 2 独立评估）
**匹配方法**: 基于范围匹配（已知行号落在扫描结果 [start_line-5, end_line+5] 区间内）

---

## 1. 扫描结果概况

| 指标 | 数值 |
|------|------|
| 已知问题总数 | 26 |
| 扫描检出总数 | 57 |
| 真阳性 (TP) | 22 |
| 假阴性 (FN) | 4 |
| 假阳性 (FP) | 35 |
| 扫描引擎 | 双引擎（内置正则 + Semgrep），57 个结果全部由两个引擎同时检出 |

---

## 2. 核心指标对比（第 10 轮 vs 第 11 轮）

| 指标 | 第 10 轮 | 第 11 轮 | 变化 | 目标 | 达标 |
|------|---------|---------|------|------|------|
| **检出率 (Recall)** | 57.7% (15/26) | **84.6% (22/26)** | **+26.9%** | 70%+ | PASS |
| **精确率 (Precision)** | 30.6% (15/49) | **38.6% (22/57)** | **+8.0%** | 50%+ | FAIL |
| **误报率 (FP Rate)** | 53.1% (26/49) | **61.4% (35/57)** | +8.3% | -- | -- |
| **漏报率 (FN Rate)** | 42.3% (11/26) | **15.4% (4/26)** | **-26.9%** | -- | -- |
| **F1 Score** | 40.0% | **53.0%** | **+13.0%** | 60%+ | FAIL |

**关键发现**:
- 检出率大幅提升 +26.9%，远超 70% 目标
- 精确率有所改善但未达 50% 目标，误报数量从 26 增至 35
- F1 Score 提升 +13.0%，距 60% 目标差 7 个百分点

---

## 3. 检出详情

### 3.1 已检出问题 (22 个)

| # | 语言 | 文件 | 已知行号 | 扫描行号 | 规则 |
|---|------|------|---------|---------|------|
| 1 | Java | java/xxe/Vulnerable.java | 22 | 22-24 | xxe-java-document-builder-usage |
| 2 | Java | java/xxe/Vulnerable.java | 29 | 29-31 | xxe-java-document-builder-usage |
| 3 | Java | java/sqli/Vulnerable.java | 33 | 30-34 | sqli-java-statement-concat |
| 4 | Java | java/sqli/Vulnerable.java | 45 | 42-47 | sqli-java-statement-concat |
| 5 | Java | java/path-traversal/Vulnerable.java | 27 | 27 | path-traversal-java-file |
| 6 | Java | java/path-traversal/Vulnerable.java | 36 | 36 | path-traversal-java-weak-filter |
| 7 | Python | python/xxe/vulnerable.py | 20 | 14-29 | xxe-python-lxml-parser |
| 8 | Python | python/xxe/vulnerable.py | 28 | 14-37 | xxe-python-lxml-parse |
| 9 | Python | python/command-injection/vulnerable.py | 22 | 22 | priv-python-subprocess-shell-true |
| 10 | Python | python/command-injection/vulnerable.py | 30 | 30 | priv-python-os-system |
| 11 | Python | python/command-injection/vulnerable.py | 37 | 37 | priv-python-popen-shell-true |
| 12 | Python | python/command-injection/vulnerable.py | 46 | 46 | priv-python-check-output-shell-true |
| 13 | Python | python/path-traversal/vulnerable.py | 22 | 23 | path-traversal-python-os-path-join |
| 14 | Python | python/path-traversal/vulnerable.py | 30 | 30 | path-traversal-python-weak-filter |
| 15 | Python | python/path-traversal/vulnerable.py | 39 | 40 | path-traversal-python-os-path-join |
| 16 | TS | typescript/xss/vulnerable.ts | 21 | 21 | xss-js-innerhtml |
| 17 | TS | typescript/xss/vulnerable.ts | 30 | 30 | xss-js-document-write |
| 18 | TS | typescript/xss/vulnerable.ts | 40 | 40 | xss-js-outerhtml |
| 19 | TS | typescript/ssrf/vulnerable.ts | 22 | 22 | ssrf-js-fetch |
| 20 | TS | typescript/ssrf/vulnerable.ts | 31 | 31-36 | ssrf-js-http-get |
| 21 | TS | typescript/ssrf/vulnerable.ts | 44 | 44-47 | ssrf-js-fetch |
| 22 | TS | typescript/ssrf/vulnerable.ts | 59 | 59 | ssrf-js-fetch-weak-filter |

### 3.2 漏报问题 (4 个)

| # | 语言 | 文件 | 行号 | 规则 | 原因分析 |
|---|------|------|------|------|---------|
| 1 | Java | java/xss/Vulnerable.java | 30 | xss-java-servlet-output | **缺少 Java Servlet XSS 规则**。扫描器没有针对 `doGet/doPost` 中 `out.println()` 拼接用户输入的检出规则 |
| 2 | Java | java/xss/Vulnerable.java | 44 | xss-java-servlet-output | 同上，`doPost` 方法中的 XSS 同样未检出 |
| 3 | Python | python/xxe/vulnerable.py | 35 | xxe-python-lxml-resolve-entities | **行号范围冲突**。扫描器在 line 14 的 `xxe-python-lxml-resolve-entities` 规则（end_line=37）已被 line 28 的已知问题优先匹配占用，导致 line 35 无法再匹配此规则 |
| 4 | TS | typescript/xss/vulnerable.ts | 50 | xss-js-dangerouslysetinnerhtml | **缺少 React dangerouslySetInnerHTML 规则**。扫描器没有针对 React JSX 中 `dangerouslySetInnerHTML` 的检出规则 |

### 3.3 误报问题 (35 个)

#### 安全文件中的误报 (23 个，占 65.7%)

| 文件 | 误报数 | 主要规则 |
|------|-------|---------|
| java/path-traversal/Safe.java | 6 | path-read/write/config-traversal (4), hardcoded-password (1), naming-constant-case (1) |
| python/path-traversal/safe.py | 6 | path-read-traversal (3), path-write-traversal (1), path-config-traversal (2) |
| python/command-injection/safe.py | 5 | priv-python-subprocess-run (3), null-python-none-check (1), priv-python-subprocess-popen (1) |
| java/sqli/Safe.java | 2 | custom-hardcoded-password (2) |
| typescript/xss/safe.ts | 2 | xss-js-innerhtml (2) |
| typescript/ssrf/safe.ts | 2 | ssrf-js-fetch (2) |

#### 漏洞文件中的额外误报 (12 个，占 34.3%)

| 文件 | 误报数 | 主要规则 |
|------|-------|---------|
| java/path-traversal/Vulnerable.java | 5 | hardcoded-password (1), naming-constant-case (1), path-config-traversal (2), path-write-traversal (1) |
| python/path-traversal/vulnerable.py | 4 | path-read-traversal (2), path-config-traversal (1), path-write-traversal (1) |
| python/xxe/vulnerable.py | 2 | xxe-python-lxml-parser (1), xxe-python-lxml-parse (1) -- 重复检出 |
| python/command-injection/vulnerable.py | 1 | null-python-none-check (1) |

---

## 4. 分类检出率

| 分类 | 检出/总数 | 检出率 | 状态 |
|------|----------|--------|------|
| java/path-traversal | 2/2 | 100% | FULL |
| java/sqli | 2/2 | 100% | FULL |
| java/xxe | 2/2 | 100% | FULL |
| **java/xss** | **0/2** | **0%** | **MISS** |
| python/command-injection | 4/4 | 100% | FULL |
| python/path-traversal | 3/3 | 100% | FULL |
| python/xxe | 2/3 | 67% | PARTIAL |
| typescript/ssrf | 4/4 | 100% | FULL |
| typescript/xss | 3/4 | 75% | PARTIAL |

---

## 5. 改进效果评估

### 5.1 显著改进

1. **检出率大幅提升 (+26.9%)**: 从 57.7% 跃升至 84.6%，远超 70% 目标
   - Java SQLi: 0% -> 100% (新增 2 个检出)
   - Java Path-traversal: 50% -> 100% (新增 1 个检出)
   - Python Command-injection: 75% -> 100% (新增 1 个检出)
   - TypeScript XSS: 25% -> 75% (新增 2 个检出)
   - TypeScript SSRF: 75% -> 100% (新增 1 个检出)

2. **漏报率大幅下降 (-26.9%)**: 从 42.3% 降至 15.4%
   - 第 10 轮漏报 11 个 -> 第 11 轮漏报仅 4 个

3. **F1 Score 提升 (+13.0%)**: 从 40.0% 升至 53.0%

### 5.2 仍需改进

1. **精确率未达标 (38.6% vs 50% 目标)**:
   - 误报从 26 增至 35，新增 8 个误报
   - 安全文件中 23 个误报（占 65.7%），说明规则对安全代码的辨识能力不足
   - 主要误报来源：
     - **path-traversal 规则过于宽泛** (18 个误报): 仅检测到 `new File()`/`os.path.join()` 等 API 调用，未考虑上下文中是否已有路径校验逻辑
     - **command-injection 规则不区分 shell=True/False** (3 个误报): safe.py 中 `subprocess.run()` 使用列表参数（安全），但规则仍标记为风险
     - **hardcoded-password 规则误匹配** (4 个误报): 将注释中的 "password" 关键词误识别为硬编码密码

2. **两类规则完全缺失**:
   - Java Servlet XSS (`xss-java-servlet-output`): 无规则覆盖 `doGet/doPost` 中的 `out.println()` 拼接
   - React dangerouslySetInnerHTML (`xss-js-dangerouslysetinnerhtml`): 无规则覆盖 React JSX 属性

---

## 6. 下一步建议

### 优先级 P0（精确率提升 -- 对 F1 影响最大）

1. **path-traversal 规则增加安全上下文感知**:
   - 在检出 `new File()`/`os.path.join()` 后，向上搜索是否存在 `getCanonicalPath()`/`realpath()`/`normalize()` 等路径校验
   - 如果存在校验逻辑，降级为 INFO 或不报告
   - 预期减少误报: ~12-15 个

2. **command-injection 规则区分 shell 参数**:
   - `subprocess.run()`/`Popen()` 使用列表参数且 `shell=False` 时不应报告
   - 仅当 `shell=True` 或参数为字符串时才报告
   - 预期减少误报: ~3-5 个

3. **hardcoded-password 规则排除注释**:
   - 跳过以 `//`、`#`、`*` 开头的行
   - 预期减少误报: ~4 个

### 优先级 P1（检出率补全）

4. **新增 Java Servlet XSS 规则**:
   - 检测 `doGet/doPost` 中 `out.println()` / `response.getWriter()` 拼接 `request.getParameter()` 的模式
   - 预期新增检出: 2 个

5. **新增 React dangerouslySetInnerHTML 规则**:
   - 检测 JSX 属性 `dangerouslySetInnerHTML` 直接使用变量
   - 预期新增检出: 1 个

### 预期效果

如果完成 P0 + P1 改进:
- 精确率: 38.6% -> ~65%+ (减少 ~20 误报)
- 检出率: 84.6% -> ~96% (新增 3 检出)
- F1 Score: 53.0% -> ~75%+

---

## 附录: 验证数据文件

- 扫描结果: `test-validation/scan-results-round11.json`
- 验证结果: `test-validation/validation-results-round11.json`
- 已知问题: `test-validation/known-issues.json`
