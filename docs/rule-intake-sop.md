# 规则接入 SOP：从 CVE/CWE 案例到上线规则

> 目标：把"整理 CWE-352 漏洞案例转成规则"这类一句话指令，变成一条
> 可重复执行的八步流水线。任何新漏洞类别（CWE/CVE/自然语言描述）沿本
> SOP 从零到 L3，不需要读懂引擎代码——扩展面定义见 `docs/extension-points.md`。
> 能力全景与当前等级见 `docs/capability-map.md`。

---

## 一、触发语对照表

| 用户指令示例 | SOP 入口 | 走法 |
|--------------|----------|------|
| "整理 CWE-352 转成规则" / "把 CSRF 检测加上" | 步骤 1 | 全流程 |
| "CVE-2022-22965 Spring4Shell 加进检测" | 步骤 1 | 全流程（CVE 先归到对应 CWE 类别，能并入现有规约的扩展 sink，不另开文件） |
| "给 taint 规则加 @ServerEndpoint 入口" | 步骤 3 | 锚点 ③ 入口点扩展，从 PoC 起步 |
| "XXE 这条规则误报了" | 步骤 3 | 修正 PoC → 顺流而下重走 4-8 |
| "这个漏洞做不了静态检测吧？" | 步骤 1 后决策 | 登记 AI 复审提示项（蓝图边界登记表），不强行做规则 |

**先查地图再动手**：接指令后第一步对照 `docs/capability-map.md`——
若类别已有 L2/L3 规则，走"扩展现有规约"（加 sink/sanitizer/入口），
不新建文件；若在待扩展格（L0），新建规约。

---

## 二、八步流水线

### 步骤 1：案例归集与类别判定

- **输入**：CWE 编号 / CVE 编号 / 自然语言漏洞描述
- **做**：检索该 CWE 官方定义与真实漏洞代码形态（CWE/CVE 描述必须
  WebSearch 验证后引用，禁止凭印象编造案例代码）；收集 vuln/sec
  **成对**用例（每个漏洞形态必须找到对应的加固写法——没有加固形态
  的规则做不出 TN，精确率不可验证）
- **输出**：类别判定（并入现有规约 or 新建）+ vuln/sec 代码对清单
- **验收**：每个漏洞形态至少一对用例；能写出一句"污点从哪来到哪去"
  （写不出来的转 pattern 规则或登记 AI 复审提示项）

### 步骤 2：三元组提炼

- **输入**：步骤 1 的代码对
- **做**：提炼 source（用户可控入口）/ sink（危险汇聚）/ sanitizer
  （加固切断点），标注 sink 的 API 形态（声明 receiver / 链式 /
  构造器 / 类型化）
- **输出**：三元组草案
- **验收**：sanitizer 列表覆盖全部 sec 用例；sink 无与常见无害 API
  同名的风险（如 Cookie.getValue() 撞 SpEL getValue）

### 步骤 3：PoC 矩阵（先验证后落地，本 SOP 的质量闸门）

- **输入**：三元组草案
- **做**：临时目录写 semgrep yaml + 构造用例文件（TP/TN 各就位），
  **预期先行**——先写下每行该报/不该报，再跑 semgrep 对照
- **输出**：实测矩阵（预期 vs 实际全一致的 yaml）
- **验收**：矩阵 100% 符合预期；任何不符合先怀疑三元组或踩了语义陷阱

**semgrep 语义陷阱 checklist（每条 PoC 必过）**：

| # | 陷阱 | 正确写法 |
|---|------|----------|
| 1 | java.lang 等隐式导入类型，全限定名不解析 | `(Runtime $R)` 而非 `(java.lang.Runtime $R)`；判据：目标代码是否需显式 import |
| 2 | 类型化元变量不支持子类型匹配 | sink 显式枚举接口类型（PreparedStatement/Statement 分列） |
| 3 | metavariable-regex 是 anchored 全匹配 | "以 Impl 结尾"写 `.*Impl` 非 `Impl$` |
| 4 | 方法调用 pattern 默认全匹配含 receiver | sanitizer 写 `$X.cmdFilter(...)`，无 receiver 不命中静态调用 |
| 5 | 类型化元变量不推断链式返回值类型 | 双 sink：类型化 + 链式各一条 |
| 6 | 元变量须 `$[A-Z_][A-Z_0-9]*` | 含小写即 rc=2 静默失效（$CLASSImpl 事故） |
| 7 | sink 排除块复合进规则内全部 sink | 加固豁免语义需独立成规则时，勿并入多 sink 规则（deser-yaml 先例） |
| 8 | 污点过程内（OSS 边界） | 入口点对象作源经不透明调用可保守传播；源/汇在被调方法即漏报，属已知边界不修 |

### 步骤 4：规约落地

- **做**：按锚点 ① 骨架写 `references/security/<category>.md`；
  检测原理段落**必须记录步骤 3 的实测结论**（哪些报哪些不报及原因），
  这是规则的"行为合同"
- **验收**：`python3 -c` 走引擎编译无告警；yaml 元数据含 cwe/owasp

### 步骤 5：孪生 yaml + profile 注册

- **做**：锚点 ⑤ 命令生成静态孪生；`profiles/default.yaml` 注册
- **验收**：`pytest tests/test_profile_completeness.py` 绿；
  孪生 yaml 直接 semgrep -f 行为与引擎一致

### 步骤 6：e2e 测试固化

- **做**：按锚点 ⑥ 模板写 `tests/test_<category>_e2e.py`，
  PoC 矩阵的每个 TP/TN 都要有断言；结构断言（sink/sanitizer 生成正确）一并写
- **验收**：单文件测试绿；注意断言 marker 勿与注释行撞文本
  （`logger.error(token);` 带 `;` 区分代码与注释）

### 步骤 7：靶场全量实测

- **做**：java-sec-code 全量跑引擎路径（非孪生 yaml），逐条 TP/FP
  人工判定；FP 零容忍——每处 FP 要么修规则重走 4-6，要么书面豁免理由
- **验收**：TP/FP 记录进盲测报告；靶场相关 controller 漏报面逐类核对

### 步骤 8：能力地图更新与收尾

- **做**：`capability-map-data.yaml` 登记等级与靶场凭证 →
  `python3 scripts/gen_capability_map.py` 重生成 → 全量回归 →
  architecture.md 追加批次记录
- **验收**：全量回归绿；地图无 ⚠ 新增（或登记为已知债）

---

## 三、红线与止损

1. **不允许只写规则不验证上线**——步骤 3/6/7 任何一步跳过，规则等级
   停留在 L1（可解析），不得声称覆盖
2. **FP 零容忍**——靶场出现 FP 且无豁免理由，回步骤 2 重提炼
3. **止损出口**——步骤 1-3 任一步发现该类别静态泛化性差（案例间无
   稳定 source/sink 形态），转两条路：自然语言预编译线
   （RULE_COMPILER_GUIDE.md）或登记 AI 复审提示项；不硬做
4. **过拟合防护**（阶段二起）——所有修复必须在双靶场回归通过，
   不得为第二靶场牺牲第一靶场成绩

## 四、完成一个类别后的自检清单

```
[ ] references/security/<category>.md        含实测行为合同
[ ] references/security/<category>.yaml      孪生产物，行为一致
[ ] references/profiles/default.yaml         已注册
[ ] tests/test_<category>_e2e.py             TP/TN 矩阵全断言
[ ] 靶场实测记录                             TP/FP 判定在案
[ ] docs/capability-map-data.yaml            等级与凭证登记
[ ] docs/capability-map.md                   已重生成
[ ] 全量回归                                 绿
```
