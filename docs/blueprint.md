# 安全规则库能力蓝图与推进方案

> [首页](../README.md) / [文档索引](README.md) / **能力蓝图**
>
> 制定日期：2026-08-26
> 范围：code-review-skill 规则库纵深（Java 高危全覆盖 + 泛化验证 + 规则治理），不含平台工程
> 对齐框架：[OWASP Top 10:2021](https://owasp.org/Top10/2021/index.html)、[CWE Top 25 (2025)](https://cwe.mitre.org/top25/archive/2025/2025_cwe_top25)

---

## 一、定位与现状盘点

### 1.1 现有资产（2026-08-26 快照）

| 维度 | 现状 |
|------|------|
| 规则总量 | 105 条（安全 60+ / 设计 10 / 实现 30+） |
| taint 数据流规则 | 12 条（全部 Java，CRITICAL/HIGH 主力） |
| 端到端测试 | 605 个（含全量可解析性回归，防 rc=2 静默失效） |
| 规约格式 | 半结构化 Markdown DSL（sources/sinks/sanitizers/not/not-inside/metavariable-regex） |
| 盲测靶场 | java-sec-code（32 个漏洞类 controller，已覆盖约 20 类） |
| 验证方法论 | PoC 矩阵先行 → 规约落地 → e2e TP/TN 固化 → 靶场全量实测 |

### 1.2 问题诊断：为什么"散"

前六批推进采用"盲测发现缺口 → 逐条补规则"的打地鼠模式。该模式每步都有实测验证（质量可靠），但存在三个结构性缺陷：

1. **无覆盖度地图**——不知道整体缺多少、缺在哪，推进优先级由靶场目录顺序而非风险权重决定
2. **无质量分级**——105 条规则中 taint 规则经靶场零 FP 验证，大量 pattern 规则从未实证过精确率，两者在库中无区分
3. **规则库存在债**——语义重复（priv-java-runtime-exec vs cmdi-taint）、遗留错位（deserialization.md 内含 SSRF/XXE section）、path 系列 pattern 残留

本蓝图以**覆盖矩阵为地图、质量阶梯为标尺、批次推进为节奏**取代打地鼠模式。

### 2.4 从"批次手推"到"一句话可扩展"（扩展性架构）

批次推进解决"推进什么"，但每批的手工流程不可复用会限制长期演化。为此
规则库扩展被固化为三个可复用资产（2026-08-26 落地）：

- **能力地图**（`docs/capability-map.md`）：脚本从规则库实时推导
  （`scripts/gen_capability_map.py`），人工只维护薄数据层的等级与靶场
  凭证（`capability-map-data.yaml`）——地图永不与规则库脱节，
  同时充当扩展指令的"先查地图再动手"入口
- **扩展锚点**（`docs/extension-points.md`）：全部扩展面收敛为七个锚点
  （规约层 / DSL 块 / 入口点 / 净化器 / 孪生产物 / 验证 / 质量），
  每锚点给出插在哪、怎么插、验收什么——扩展不要求读懂引擎代码
- **接入 SOP**（`docs/rule-intake-sop.md`）：CVE/CWE 案例到 L3 规则的
  八步流水线，含触发语对照表与 semgrep 语义陷阱 checklist——
  "整理 CWE-xxx 转成规则"一句话即可按流程执行到底

三资产与本蓝图的关系：蓝图定方向与批次（做什么），地图定现状
（在哪），锚点与 SOP 定路径（怎么做）。每批次的推进即 SOP 的一次执行。

---

## 二、核心理念：三个转变

### 2.1 从"漏洞驱动"到"矩阵驱动"

推进单位从"单条规则"变为"覆盖矩阵的一个格子"（漏洞类别 × 质量等级）。每个格子点亮必须走完 PoC → 规约 → e2e → 靶场实测全链路，不允许只写规则不验证的半成品。靶场从"验证工具"升格为"覆盖度标尺"——java-sec-code 的 32 类漏洞即 Java 侧矩阵的天然纵轴。

### 2.2 从"规则数量"到"质量阶梯"

| 等级 | 定义 | 达标凭证 |
|------|------|----------|
| L0 | 未覆盖 | — |
| L1 | 规则存在且可解析 | 全量可解析性回归通过（rc=2 防护已建立） |
| L2 | 端到端行为固化 | 真实 semgrep e2e 测试（TP/TN 矩阵）进 tests/ |
| L3 | 靶场盲测零误报 | java-sec-code 全量实测 TP/FP 记录进盲测报告 |

当前约 9 个类别达 L3（SQLi、路径穿越、SSRF、XXE、XSS、反序列化、命令注入、表达式注入、日志注入），硬编码密钥/弱加密/弱随机等约 L2，其余 L0/L1。**规则库的含金量 = L3 格子数，不是规则总数。**

### 2.3 从"静态全覆盖"到"静态最优 + 边界显式化 + AI 补位"

已实证 Semgrep OSS 严格过程内、类型化元变量不支持子类型与隐式导入解析、跨方法委托不可静态区分（激进源标记证伪实验见 architecture.md）。结论不追求静态层全覆盖，而是：

- **静态层**做到 OSS 边界内最优（入口点锚定 + 过程内数据流，已验证零 FP）
- **边界显式化**——所有已知漏报面登记为清单（跨方法委托、WebSocket 入口、配置分散类），随扫描报告输出"本次未检查项"，评审者知情
- **AI 补位**——CRITICAL/HIGH 问题进 LLM 精审，静态漏报面作为 AI 复审的重点提示项

---

## 三、能力地图：CWE 对齐覆盖矩阵

以 [CWE Top 25 (2025)](https://cwe.mitre.org/top25/archive/2025/2025_cwe_top25)（基于 2024-06 至 2025-06 披露的 3.9 万余 CVE 统计）中与 Web 代码审计相关的类别为纵轴，剔除内存安全类（CWE-787/416/125 等主要属 C/C++ 域，不在 SAST 目标范围）：

| CWE | 漏洞类别 | OWASP | 现有规则 | 等级 |
|-----|---------|-------|---------|------|
| CWE-79 | XSS（Top25 第 1） | A03 | xss-taint | **L3** |
| CWE-89 | SQL 注入（第 2） | A03 | sqli-taint + mybatis×3 | **L3** |
| CWE-352 | CSRF（第 3） | A01 | — | L0 |
| CWE-22 | 路径穿越（第 6） | A01 | path-traversal-taint | **L3** |
| CWE-78 | 命令注入 | A03 | cmdi-taint | **L3** |
| CWE-94/95 | 代码/表达式注入 | A03 | spel/qlexpress/script-engine | **L3** |
| CWE-1336 | SSTI 模板注入 | A03 | — | L0 |
| CWE-918 | SSRF（第 22） | A10 | ssrf-taint | **L3** |
| CWE-502 | 不安全反序列化 | A08 | deser-taint/deser-yaml-taint | **L3**（Fastjson/XStream 未覆盖） |
| CWE-611 | XXE | A05 | xxe-deep-detection | **L3** |
| CWE-117 | 日志注入 | A09 | log-injection-taint | **L3** |
| CWE-601 | 开放重定向 | A01 | — | L0 |
| CWE-942 | 过宽跨域 | A05 | — | L0 |
| CWE-614 | Cookie 安全属性缺失 | A05 | — | L0 |
| CWE-470 | 不安全反射/类加载 | A03 | — | L0 |
| CWE-348 | 信任源伪造（X-Forwarded-For） | A07 | — | L0 |
| CWE-1333 | ReDoS | A04 | — | L0 |
| CWE-798 | 硬编码凭证 | A07 | crypto-hardcoded-key | L2 |
| CWE-327/328 | 弱加密/弱哈希 | A02 | sig-java-weak-algorithm | L2 |
| CWE-330 | 弱随机数 | A02 | crypto-weak-random-java | L2 |

靶场未覆盖的 12 类全部落入 L0/L3 部分格：CSRF、CORS、Cookies、ClassDataLoader、Dotall（ReDoS）、Fastjson、IPForge、Jsonp、SSTI、URLRedirect、WebSockets、CRLFInjection（需实测确认是否已被 log-injection-taint 覆盖）。

---

## 四、推进方案：三阶段

### 阶段一：Java 高危矩阵点亮 + 规则库治理

目标：L3 类别数 9 → 14+，规则库零语义重复。每批严格沿用"PoC 矩阵先行"方法论。

**批次 A（taint 类，可行性高优先）**

| 批次 | 任务 | 靶场验证 | 备注 |
|------|------|---------|------|
| A1 | 开放重定向 taint（CWE-601）：`sendRedirect`/`RedirectView`/`ModelAndView(setRedirect)` sink | URLRedirect.java | taint 形态最清晰，先行 |
| A2 | SSTI taint（CWE-1336）：VelocityEngine/Freemarker sink | SSTI.java | 表达式注入同族经验可复用 |
| A3 | Fastjson/XStream 反序列化（CWE-502 补全）：扩展 deser sink 族 | Fastjson/XStreamRce.java | 注意与 deser-taint sink 归属 |
| A4 | CRLF 注入实测确认（CWE-93）：log-injection-taint 是否已覆盖 | CRLFInjection.java | 若覆盖则补测试锚定即可 |

**批次 B（配置/模式类，误报风险高，先 PoC 后定去留）**

| 批次 | 任务 | 靶场验证 | 风险 |
|------|------|---------|------|
| B1 | CSRF（CWE-352，Top25 第 3）：Spring 写操作端点缺 CSRF 防护的 pattern 检测 | CSRF.java | 配置分散，误报面大；PoC 不达标则登记为 AI 复审提示项 |
| B2 | CORS 过宽（CWE-942）：`addAllowedOrigin("*")` 等 pattern | Cors.java | 低风险，快速 |
| B3 | Cookie 安全属性（CWE-614）：`new Cookie` 后缺 `setHttpOnly`/`setSecure` | Cookies.java | 低风险 |
| B4 | WebSocket 入口扩展：`@ServerEndpoint` 参数锚定进 sources DSL | WebSockets*.java | 已知漏报面，需评估误报 |

**批次 C（规则库治理，价值在长期维护成本）**

| 任务 | 内容 |
|------|------|
| 语义去重 | priv-java-runtime-exec / priv-java-process-builder 与 cmdi-taint 重叠，Java 侧并入后者（Python/JS 保留） |
| 错位迁移 | deserialization.md 内的 ssrf-deep-detection/xxe-deep-detection 遗留 section 迁至对应规约文件 |
| 残留清理 | path-traversal.md 中 path-read/write/upload/config/log-traversal 的 Java pattern 残留核对（taint 已接管） |
| 边界登记表 | 已知漏报面清单固化为文档（跨方法委托、WebSocket、配置分散类），供 AI 复审与报告输出引用 |

阶段一验收：新增规则全部 L2 + L3（靶场 TP/FP 记录）；全量回归 600+ 始终绿；规则库无语义重复条目；边界登记表成文。

### 阶段二：第二靶场泛化验证 ✅ 已完成（2026-08-26）

目标：证明规则泛化能力，而非过拟合 java-sec-code 代码风格。

**执行结果**：

1. **靶场选型**：OWASP WebGoat（Spring Boot 2025.3, Java 21, ~350 Java 文件），通过 gitcode 镜像克隆至 `repos/webgoat/`
2. **全量盲测**：91 条安全规则（13 taint + 78 pattern）全量扫描，产出 49 检出
3. **TP/FP 判定**：48 TP + 1 FP，**精确率 97.96%**
4. **规则修复**：sig-java-verify-skip 的 FP 驱动了 pattern-not 方法级重构
5. **质量晋升**：8 条规则从 L2 晋升 L3（crypto-hardcoded-key, crypto-weak-random-java, sqli-taint, xss-taint, deser-taint, path-traversal-taint, log-injection-taint, priv-java-runtime-exec）
6. **双靶场回归**：修复后 java-sec-code + WebGoat 双靶场全绿

详细报告：`docs/blind-test-webgoat.md`
方法论支撑：`docs/architecture.md` > 双盲验证方法论

**方法论沉淀**：本次盲测确立了「靶场 + 投票」双盲验证框架——靶场泛化检验规则在未知代码上的表现，投票机制通过多评审员背靠背判定计算 Cohen's Kappa 一致性系数。两者协同消除确认偏误、量化规则质量。详见架构文档。

阶段二验收：✅ 第二靶场精确率 97.96%（> 95% 阈值）；双靶场回归全绿。

### 阶段三：质量标尺固化（轻量收尾）

不做平台工程，仅两个轻量交付：

1. **质量等级自动标注**：脚本从测试收集情况推导各规则等级（有 e2e 测试 = L2，盲测报告覆盖 = L3），生成 rules-quality 报告，纳入日常回归
2. **覆盖度透明化**：扫描报告附"本次未检查的能力"清单（引用边界登记表）——把"静态最优 + 边界显式"理念落地为交付物特性

---

## 五、质量度量与验收标准

| 层级 | 指标 | 基线 | 当前（阶段二后） | 阶段三目标 |
|------|------|------|----------------|-----------|
| 能力 | L3 类别数 | ~9 | **11**（+crypto-hardcoded, crypto-weak-random） | 14+ |
| 质量 | 新规则 L2 覆盖率 | — | 100% | 100%（始终） |
| 质量 | 全量回归 | 599 passed | **599 passed** / 6 skipped | 始终绿 |
| 质量 | 规则语义重复 | 2 组已知 | 2 组（crypto-hardcoded-key 双规则，待治理） | 0 |
| 泛化 | 靶场数 | 1 | **2**（java-sec-code + WebGoat） | 2+ |
| 泛化 | 第二靶场精确率 | — | **97.96%**（48 TP / 49 检出） | ≥ 95% |
| 泛化 | 盲测驱动修复 | — | 1 条（sig-java-verify-skip） | 持续 |
| 扩展 | SOP 可执行性 | 八步流水线 + 七锚点 + 自维护地图 | 同左 | 新类别一句话接入即走通 |

推进节奏沿用既定习惯：每批次独立可交付、实测验证、报告沉淀（architecture.md 批次记录 + 盲测报告），单批规模以"一个规则族 + 一份靶场验证"为限，不合并过大变更。

---

## 六、风险与边界登记表

| # | 边界/风险 | 性质 | 应对 |
|---|----------|------|------|
| 1 | 跨方法污点（源/汇在被调方法、字段间接） | Semgrep OSS 能力边界（已实证） | AI 复审补位；不尝试静态修复（激进源标记已证伪） |
| 2 | WebSocket 入口未锚定 | DSL 覆盖缺口 | 阶段一 B4 扩展评估 |
| 3 | CSRF/CORS/Cookie 配置类规则误报风险 | 规则设计风险 | 先 PoC 后落地；不达标降级为 AI 复审提示项 |
| 4 | 第二靶场暴露过拟合 | 泛化风险 | 双靶场回归制（修复不得反噬第一靶场） |
| 5 | IPForge/ReDoS/ClassDataLoader 静态泛化性差 | 类别特性 | 不强行做规则；评估后登记为 AI 复审提示项 |
| 6 | 隐式导入/类型化元变量/anchored regex 等 semgrep 行为陷阱 | 已实证已沉淀 | 规约内注释 + 项目记忆，新规则 PoC 阶段强校验 |

---

## 附：与既有文档的关系

- `docs/architecture.md`——引擎与规则技术演进史（批次一至六记录），本蓝图是其上层规划
- `docs/capability-map.md`——能力地图（脚本生成），覆盖矩阵的实时视图；人工数据在 `capability-map-data.yaml`
- `docs/extension-points.md`——扩展锚点：七个扩展面定义（插在哪/怎么插/验收什么）
- `docs/rule-intake-sop.md`——规则接入 SOP：CVE/CWE 案例到 L3 规则的八步流水线
- `docs/blind-test-java-sec-code.md`——第一靶场盲测基线，阶段二产出对应第二靶场报告
- 本蓝图为活文档：每阶段收尾时更新矩阵等级与验收状态
