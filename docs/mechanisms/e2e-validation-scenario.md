# 端到端代码评审验证场景

> [首页](../../README.md) / [文档索引](../README.md) / [核心机制](../README.md#核心机制详解) / [测试体系](testing.md) / **端到端验证场景**
>
> 场景编号：E2E-001  
> 验证目标：验证完整代码评审流水线（扫描 → AI 评审 → 报告）的正确性与准确性  
> 关联子智能体：`code-reviewer`（model: qwen-3.7-plus）  
> 设计日期：2026-08-26

---

## 1. 场景概述

本场景验证从代码变更到最终报告的完整评审链路，重点验证：

1. **扫描流水线**：差异分析 → 调用图 → 规则检查 → 降噪 → AI 评审
2. **子智能体触发**：description 匹配是否正确，能否自动委派评审任务
3. **评审准确性**：TP/FP 裁决是否符合预期，输出格式是否规范
4. **模型性能**：qwen-3.7-plus 的评审质量与成本

### 1.1 验证范围

| 阶段 | 验证内容 | 成功标准 |
|------|----------|----------|
| 扫描阶段 | 差异分析、调用图、规则检查、降噪 | 检出数量与预期一致，无静默失效 |
| AI 评审阶段 | 子智能体触发、TP/FP 裁决、输出格式 | 精确率 ≥ 95%，JSON schema 合规 |
| 报告阶段 | 报告生成、字段完整性 | 报告包含所有检出，调用链关联正确 |

### 1.2 验证靶场

使用项目已有的测试用例库（`references/test-cases/security/`），包含 10 类高危漏洞的违规/安全代码对：

| 漏洞类别 | CWE | 违规样本数 | 安全样本数 | 预期检出 |
|----------|-----|-----------|-----------|----------|
| SQL 注入 | CWE-89 | 3 | 2 | 3 TP + 0 FP |
| XXE | CWE-611 | 4 | 3 | 4 TP + 0 FP |
| 命令注入 | CWE-78 | 3 | 2 | 3 TP + 0 FP |
| 路径穿越 | CWE-22 | 5 | 4 | 5 TP + 0 FP |
| XSS | CWE-79 | 3 | 2 | 3 TP + 0 FP |
| SSRF | CWE-918 | 3 | 3 | 3 TP + 0 FP |
| 反序列化 | CWE-502 | 2 | 2 | 2 TP + 0 FP |
| 表达式注入 | CWE-94 | 3 | 2 | 3 TP + 0 FP |
| 硬编码凭证 | CWE-798 | 4 | 3 | 4 TP + 0 FP |
| 弱加密 | CWE-327 | 2 | 2 | 2 TP + 0 FP |

**总计**：32 违规样本 + 25 安全样本 = 57 个测试用例

---

## 2. 验证流程

### 阶段一：环境准备（5 分钟）

**目标**：确保验证环境就绪，无外部依赖干扰。

**步骤**：

1. 确认子智能体配置文件存在：
   ```bash
   ls -la .trae/agents/code-reviewer.md
   ```
   预期：文件存在，frontmatter 包含 `model: qwen-3.7-plus`

2. 确认测试用例库完整：
   ```bash
   ls references/test-cases/security/*.md | wc -l
   ```
   预期：输出 10（10 类漏洞）

3. 确认 semgrep 可用（可选，AST 引擎始终执行）：
   ```bash
   semgrep --version
   ```
   预期：输出版本号或 "command not found"（不影响验证）

4. 清理历史报告：
   ```bash
   rm -rf report/ .code-review/
   ```

**验收标准**：所有检查通过，无阻塞性错误。

---

### 阶段二：扫描流水线验证（10 分钟）

**目标**：验证扫描阶段的检出数量与预期一致，无静默失效。

**步骤**：

1. 运行扫描（使用测试用例库作为扫描目标）：
   ```bash
   python3 scripts/scan.py \
     --repo references/test-cases/ \
     --base main \
     --target HEAD \
     --output report/ \
     --workflow security \
     --no-ai  # 先不启用 AI 评审，验证纯扫描
   ```

2. 检查扫描日志：
   ```bash
   grep -E "检出|降噪|Prefilter" report/scan.log
   ```
   预期：显示检出数量、Prefilter 过滤数量

3. 检查报告生成：
   ```bash
   ls -lh report/
   ```
   预期：包含 `report.json`、`report.md`、`summary.json`

4. 统计检出数量：
   ```bash
   python3 -c "import json; d=json.load(open('report/report.json')); print(f'总检出: {len(d[\"issues\"])}')"
   ```
   预期：接近 32（违规样本数），允许 ±5 偏差（部分规则可能未覆盖）

5. 检查静默失效：
   ```bash
   grep -i "error\|failed\|rc=2" report/scan.log
   ```
   预期：无 rc=2 错误，无规则解析失败

**验收标准**：
- 检出数量 ≥ 27（32 × 85%）
- 无 rc=2 错误
- 报告文件完整

---

### 阶段三：AI 评审验证（15 分钟）

**目标**：验证子智能体触发、TP/FP 裁决准确性、输出格式合规。

**步骤**：

1. 重新运行扫描（启用 AI 评审）：
   ```bash
   python3 scripts/scan.py \
     --repo references/test-cases/ \
     --base main \
     --target HEAD \
     --output report/ \
     --workflow security
   ```
   预期：日志显示 "AI 评审已启用"、"工作流: security"

2. 检查子智能体任务文件生成：
   ```bash
   ls -lh report/subagent-review-task.md
   ```
   预期：文件存在，包含待评审问题清单

3. 委派子智能体评审（在 TRAE 中执行）：
   - 输入："评审一下扫描结果"
   - 预期：内置 Agent 识别任务，自动委派给 `code-reviewer` 子智能体
   - 子智能体使用 qwen-3.7-plus 模型执行评审

4. 检查子智能体输出：
   ```bash
   ls -lh report/ai-review-result.json
   ```
   预期：文件存在，包含 JSON 数组

5. 验证 JSON schema 合规：
   ```python
   import json
   schema = {
       "type": "array",
       "items": {
           "type": "object",
           "required": ["rule_id", "file", "line", "is_false_positive", "ai_confidence", "analysis"],
           "properties": {
               "rule_id": {"type": "string"},
               "file": {"type": "string"},
               "line": {"type": "integer"},
               "is_false_positive": {"type": "boolean"},
               "ai_confidence": {"type": "number", "minimum": 0, "maximum": 1},
               "analysis": {"type": "string"}
           }
       }
   }
   result = json.load(open('report/ai-review-result.json'))
   # 使用 jsonschema 验证
   ```
   预期：所有条目符合 schema

6. 计算精确率：
   ```python
   import json
   result = json.load(open('report/ai-review-result.json'))
   tp = sum(1 for r in result if r['is_false_positive'] == False)
   fp = sum(1 for r in result if r['is_false_positive'] == True)
   precision = tp / (tp + fp) if (tp + fp) > 0 else 0
   print(f"TP: {tp}, FP: {fp}, 精确率: {precision:.2%}")
   ```
   预期：精确率 ≥ 95%

**验收标准**：
- 子智能体成功触发并执行
- JSON schema 100% 合规
- 精确率 ≥ 95%（至少 30 TP + ≤ 2 FP）

---

### 阶段四：报告完整性验证（5 分钟）

**目标**：验证最终报告包含所有检出，调用链关联正确。

**步骤**：

1. 检查最终报告：
   ```bash
   ls -lh report/report.json report/report.md
   ```

2. 统计最终检出（AI 评审后）：
   ```bash
   python3 -c "import json; d=json.load(open('report/report.json')); print(f'最终检出: {len(d[\"issues\"])}')"
   ```
   预期：接近阶段二的检出数量（AI 评审过滤部分误报）

3. 检查调用链关联：
   ```bash
   python3 -c "import json; d=json.load(open('report/report.json')); issues_with_chain = [i for i in d['issues'] if 'call_chain' in i]; print(f'含调用链: {len(issues_with_chain)}')"
   ```
   预期：至少 50% 的检出包含调用链

4. 检查 AI 增强字段：
   ```bash
   python3 -c "import json; d=json.load(open('report/report.json')); issues_with_ai = [i for i in d['issues'] if 'ai_confidence' in i]; print(f'含 AI 评审: {len(issues_with_ai)}')"
   ```
   预期：所有 CRITICAL/HIGH 级别检出包含 AI 评审字段

**验收标准**：
- 报告文件完整
- 调用链关联 ≥ 50%
- AI 评审字段覆盖所有高严重级检出

---

### 阶段五：成本与性能度量（5 分钟）

**目标**：记录 qwen-3.7-plus 的评审成本（token 消耗）与耗时。

**步骤**：

1. 从子智能体日志提取 token 消耗：
   ```bash
   grep -E "input_tokens|output_tokens|total_tokens" report/subagent.log
   ```

2. 计算平均每条检出的 token 消耗：
   ```python
   import json
   log = json.load(open('report/subagent.log'))
   total_tokens = log['total_tokens']
   issues_count = len(log['issues'])
   avg_tokens = total_tokens / issues_count
   print(f"平均每条检出: {avg_tokens:.0f} tokens")
   ```

3. 记录评审耗时：
   ```bash
   grep -E "start_time|end_time" report/subagent.log
   ```

**验收标准**：
- 平均每条检出 token 消耗 ≤ 2000（合理范围）
- 评审耗时 ≤ 5 分钟（32 条检出）

---

## 3. 验证指标汇总

| 指标 | 目标值 | 测量方法 | 验收标准 |
|------|--------|----------|----------|
| 扫描检出数量 | ≥ 27 | `report.json` 统计 | 阶段二通过 |
| 扫描无静默失效 | 0 rc=2 | 日志检查 | 阶段二通过 |
| 子智能体触发成功率 | 100% | 任务文件生成 | 阶段三通过 |
| JSON schema 合规率 | 100% | schema 验证 | 阶段三通过 |
| **精确率** | **≥ 95%** | TP/(TP+FP) | **阶段三通过** |
| 调用链关联率 | ≥ 50% | `call_chain` 字段统计 | 阶段四通过 |
| AI 评审覆盖率 | 100%（CRITICAL/HIGH） | `ai_confidence` 字段统计 | 阶段四通过 |
| 平均 token 消耗 | ≤ 2000/条 | 日志统计 | 阶段五通过 |
| 评审耗时 | ≤ 5 分钟 | 时间戳差值 | 阶段五通过 |

---

## 4. 验收判定

### 4.1 通过条件

所有指标达到目标值，判定为**验证通过**。

### 4.2 部分通过条件

- 精确率 ≥ 90% 但 < 95%：标记为**条件通过**，需优化子智能体提示词或模型参数
- 其他指标未达标但偏差 ≤ 10%：标记为**条件通过**，需记录原因并制定改进计划

### 4.3 失败条件

- 精确率 < 90%：判定为**验证失败**，需回滚子智能体配置或更换模型
- 子智能体未触发：判定为**验证失败**，需检查 description 配置
- JSON schema 合规率 < 100%：判定为**验证失败**，需修复输出格式

---

## 5. 回归测试

本场景应纳入 CI/CD 流水线，每次子智能体配置变更或模型升级时自动执行：

```bash
# CI 脚本示例
python3 scripts/validate_e2e_scenario.py --scenario E2E-001
```

回归测试覆盖：
- 子智能体配置文件变更
- 模型切换（如 qwen-3.7-plus → qwen-3.6-plus）
- 提示词模板更新
- 规则库新增/修改

---

## 6. 相关文档

| 主题 | 文档 |
|------|------|
| 测试体系分层 | [testing.md](testing.md) |
| 双盲验证方法论 | [architecture.md](../architecture.md) |
| 子智能体配置 | [.trae/agents/code-reviewer.md](../../.trae/agents/code-reviewer.md) |
| 验证矩阵 | [VERIFICATION_MATRIX.md](../VERIFICATION_MATRIX.md) |
