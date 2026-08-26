# 扩展锚点（Extension Points）

> 规则库的扩展不要求读懂引擎全部代码——所有扩展面收敛为七个锚点。
> 每个锚点给出：插在哪、怎么插、验收什么。
> 配套：新漏洞类别从零到上线的完整流程见 `docs/rule-intake-sop.md`；
> 当前能力全景见 `docs/capability-map.md`（自动生成）。

---

## 锚点总览

```
一句话触发（README 引导提示词）
   │
   ▼
SOP 八步流水线（rule-intake-sop.md）
   │
   ├── ① 规约层锚点   新漏洞类别 → 新 md 规约文件          【最常用】
   ├── ② DSL 块锚点    新检测语义 → 新 pattern-* 块类型
   ├── ③ 入口点锚点    新框架入口 → spring-entrypoint-param 族
   ├── ④ 净化器锚点    新加固写法 → sanitizer 约定登记
   ├── ⑤ 孪生产物锚点  规约 md → 静态 yaml 导出
   ├── ⑥ 验证锚点      TP/TN 行为 → e2e 测试 + 靶场实测
   └── ⑦ 质量锚点     L 等级与凭证 → 薄数据层 + 地图重生成
```

---

## ① 规约层锚点（新增漏洞类别）

**插在哪**：`references/security/<category>.md`（安全）或 design/implementation 对应目录

**怎么插**：一个文件可含多条规则，每条 = `# 标题` section + 元数据 yaml 块 + DSL 块。最小骨架：

```markdown
# <类别名> - <一句话语义>（数据流分析）

> <攻击后果与检测原理，一段话>

```yaml
id: <category>-taint          # 命名：<域>-<类别>-taint / -pattern
languages: [java]
severity: CRITICAL|HIGH|WARNING
cwe: CWE-78                    # 必填：能力地图按此归组
owasp: A03:2021
```

## 检测模式

```pattern-sources
<污点源，一行一个>
```

```pattern-sinks
<污点汇聚点>
```

```pattern-sanitizers
<净化器，可选>
```
```

**登记三件套**（缺一则 profile 完备性测试红）：
1. `references/profiles/default.yaml` 的 specs 列表加 `- path: security/<category>.md enabled: true`
2. 孪生 yaml（见锚点 ⑤）
3. e2e 测试（见锚点 ⑥）

**验收**：`pytest tests/test_profile_completeness.py` 绿。

---

## ② DSL 块锚点（新增检测语义）

现有块类型语义总表（semgrep 语义的一一映射）：

| DSL 块 | 适用 | 复合为 semgrep | 语义要点 |
|--------|------|----------------|----------|
| `pattern` | pattern 规则 | `pattern` / `pattern-either` | 多块自动 either |
| `pattern-not` | pattern 规则 | `pattern-not` | 同范围否定 |
| `pattern-not-inside` | pattern 规则 | `pattern-not-inside` | 命中点位于排除块内才豁免 |
| `pattern-regex` | pattern 规则 | `pattern-regex` | 全文正则 |
| `pattern-metavariable-regex` | pattern 规则 | `metavariable-regex` | 每行 `$VAR: regex`；**anchored 全匹配**，`.*Impl` 非 `Impl$` |
| `pattern-sources` | taint 规则 | `pattern-sources` | 污点源；`spring-entrypoint-param` 为保留字 |
| `pattern-sinks` | taint 规则 | `pattern-sinks` | 污点汇聚 |
| `pattern-sanitizers` | taint 规则 | `pattern-sanitizers` | 切断污点 |
| `pattern-sinks-not` | taint 规则 | 复合进每条 sink 的 `pattern-not` | sink 同范围排除（加固参数形态） |
| `pattern-sinks-not-inside` | taint 规则 | 复合进每条 sink 的 `pattern-not-inside` | sink 命中点位于豁免块内（加固语句序列） |

语言子分组：`### Java` / `### Python` / `### Node.js` 子标题下写块，自动打 lang 标签，仅对对应语言生效。

**新增块类型改哪里**（`scripts/rule_engine.py` 两处）：
1. 解析处：`_parse_section` 的块类型分支（参照 `pattern-metavariable-regex` 分支，含格式校验与告警）
2. 构建处：`_build_semgrep_rule`（pattern 族）或 `_apply_sink_exclusions`（taint 族）的复合逻辑

**验收**：新块类型必须有正负两侧用例进 e2e（见锚点 ⑥）；全量可解析性回归（rc=2 静默失效防护）绿。

---

## ③ 入口点锚点（新框架入口）

**插在哪**：各 taint 规约 `pattern-sources` 的 `spring-entrypoint-param` 保留字展开处——
`scripts/rule_engine.py` 中该保留字替换为注解 pattern-inside 族
（GetMapping/PostMapping/RequestMapping/PutMapping/DeleteMapping/PatchMapping）。

**怎么插**：新增入口类型（如 `@ServerEndpoint`）= 在展开清单追加注解形态。
注意各入口语义差异：WebSocket `@ServerEndpoint` 的 `@OnMessage` 方法参数
是消息体而非 URL 参数，污点语义更宽，需独立 PoC 评估误报（蓝图 B4 批次）。

**验收**：新入口构造用例 TP；既有入口用例零回归。

---

## ④ 净化器锚点（新加固写法）

**插在哪**：规约的 `pattern-sanitizers` 块；taint 规则的约定式函数名
（`cmdFilter(...)`/`isAllowedUrl(...)` 等白名单函数族）。

**已实证陷阱**：
- 方法调用形态的 sanitizer **必须带 receiver 元变量**：`$X.cmdFilter(...)`，
  无 receiver 写法不匹配静态调用 `SecurityUtil.cmdFilter(...)`
- 精确字面匹配语义：`replaceAll("[\n\r]", ...)` 两种源码拼写要分列，
  无关替换（`replaceAll("a","b")`）不净化（正确）

**验收**：每种净化形态一个 TN 用例；非净化同形调用一个 TP 反证用例。

---

## ⑤ 孪生产物锚点

**插在哪**：`references/security/<category>.yaml`——引擎实时编译产物的
静态快照，供外部直接 `semgrep -f` 使用。

**怎么生成**：

```bash
cd scripts && python3 -c "
import sys; sys.path.insert(0, '.')
from rule_engine import RuleEngine
import yaml
engine = RuleEngine('../references/security', {'specs': [{'path': '<category>.md', 'enabled': True}]})
out = engine._rules_to_semgrep()
with open('../references/security/<category>.yaml', 'w', encoding='utf-8') as f:
    f.write('# <类别> 静态孪生产物说明头\n\nrules:\n')
    for r in out['rules']:
        f.write(yaml.safe_dump([r], allow_unicode=True, default_flow_style=False, sort_keys=False, width=100))
"
```

注意：一个 md 含多个语义域的规则时（如 deserialization.md 历史遗留
SSRF/XXE section），按规则 id 前缀过滤后导出，勿混入。

**验收**：`semgrep --config <category>.yaml --json <用例>` 行为与引擎路径一致。

---

## ⑥ 验证锚点

**e2e 测试**：`tests/test_<category>_e2e.py`，模板参照
`tests/test_command_injection_e2e.py`——fixture 含 TP/TN 矩阵，
断言用行号集合；`pytestmark = skipif(无 semgrep)`。

**靶场实测**：java-sec-code 全量跑引擎路径，TP/FP 逐条人工判定，
记录进盲测报告与 capability-map-data.yaml。

**验收门槛**（质量阶梯，详见 blueprint.md）：
- L2：e2e 测试进 tests/ 且绿
- L3：靶场全量实测 TP/FP 记录在案，FP=0（或每处 FP 有豁免理由）

---

## ⑦ 质量锚点

**插在哪**：`docs/capability-map-data.yaml`（人工维护的唯一数据）——
新类别上线/升级时登记 `quality_level` 与 `blind_test` 凭证。

**重生成**：`python3 scripts/gen_capability_map.py`（规则明细自动推导，
含孪生 yaml 缺失告警与 e2e 覆盖标注）。

**验收**：地图总览数字与 git 状态一致；⚠ 标注（无 e2e / 缺孪生）要么补齐、要么在蓝图登记为已知债。

---

## 两条编译线的关系

| 线 | 入口 | 产物 | 适用 |
|----|------|------|------|
| 结构化 DSL 线 | `<category>.md`（本锚点体系） | 引擎实时编译 + 孪生 yaml | 检测语义明确可枚举 source/sink（全部 taint 规则） |
| 自然语言预编译线 | `*-natural-language.md` | `compiled/*.approved.yaml`（人工审批后加载） | 语义只能自然语言描述的规约，见 `docs/RULE_COMPILER_GUIDE.md` |

两线并行互补：SOP（rule-intake-sop.md）走 DSL 线；当无法提炼稳定
source/sink 三元组时（如配置分散类 CSRF），评估转自然语言线或登记为
AI 复审提示项（不强行做规则）。
