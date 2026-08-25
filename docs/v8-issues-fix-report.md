# V8 五大问题修复报告

> **修复日期**: 2026-08-13
> **回归测试**: 10 轮验证通过

## 一、问题核实（全部确认）

| # | 问题 | 核实结果 | 关键证据 |
|---|------|---------|----------|
| 1 | 缺少 `ai_confidence` 填入默认值 0.8 | ✅ 确认 | `scripts/scan.py:489` `ai_confidence=issue.get("ai_confidence", 0.8)` |
| 2 | `ai_action` 固定为 `keep` | ✅ 确认 | `scripts/scan.py:488` `ai_action="keep"` |
| 3 | 缺少读取/校验/合并二审结果流程 | ✅ 确认 | 仅生成 `subagent-review-task.md`，无读取合并代码 |
| 4 | 反馈仅在 workspace，历史丢失 | ✅ 确认 | `scripts/scan.py:431` `storage_file = workspace_dir / "feedbacks.json"` |
| 5 | subagent 任务缺少 call_chain | ✅ 确认 | subagent 任务生成在调用链关联之前 |

## 二、修复方案

### 修复 1+2: ai_action 动态决策（scripts/scan.py）

```python
# 旧代码（硬编码）
ai_action = "keep"
ai_confidence = issue.get("ai_confidence", 0.8)

# 新代码（动态决策）
if ai_conf is None:
    ai_action = "pending_review"
    ai_conf = None
elif ai_conf < 0.3:
    ai_action = "drop"
elif ai_conf < 0.7:
    ai_action = "needs_review"
else:
    ai_action = "keep"
```

**置信度阈值**:
- `< 0.3` → drop（误报丢弃）
- `0.3 - 0.7` → needs_review（需人工）
- `>= 0.7` → keep（保留）

### 修复 3: 二审结果合并（scripts/review_merger.py 新建）

新增 `ReviewMerger` 类:
- `read_review_results()` - 读取 `review-results.json`
- `validate_review_result()` - 校验格式（必填字段、ai_confidence 范围）
- `merge_into_report()` - 合并到 `report.json`，写入 `merge_info`

`scan.py` 中自动调用合并：
```python
from scripts.review_merger import merge_review_results
merged, invalid, no_report = merge_review_results(str(output_dir))
```

### 修复 4: 全局 feedback 跨扫描复用（harness/feedback_manager.py + scan.py）

`FeedbackManager` 增强:
```python
def __init__(self, storage_file, workspace_storage_file=None):
    self.storage_file = Path(storage_file)  # 全局路径
    self.workspace_storage_file = Path(workspace_storage_file) if workspace_storage_file else None

def _save(self):
    # 同时写全局 + workspace
    ...
```

`scan.py` 配置更新:
```yaml
feedback:
  storage_file: "data/feedbacks.json"  # 全局
  workspace_storage_file: "<workspace>/feedbacks.json"  # 本次
```

### 修复 5: subagent 任务顺序调整（scripts/scan.py）

**问题**: subagent 任务生成在调用链关联**之前** → call_chain 字段为空

**修复**: 调整顺序
```python
# 1. 关联调用链
for issue in issues:
    issue["call_chain"] = call_graph.get("call_chains", {}).get(...)

# 2. 生成 subagent 任务（移到此处，含完整 call_chain）
task = ai_reviewer.generate_subagent_task(to_review, diff_result, call_graph)
```

同时在 subagent-contract 提示词中加强提示:
```markdown
⚠️ 每个 issue 已包含 `code_snippet`（命中位置源码）和 `call_chain`（调用链）字段。必须先读取这些字段，再做判断！
```

## 三、回归测试（10 轮）

### 第 1 轮: 基础扫描
- 删除旧 workspace，全局 feedback
- 跑 scan.py: 70 个问题，无报错
- **问题 1+2 验证**: ai_action 70/70 = pending_review，ai_confidence 70/70 = None ✅

### 第 2 轮: 创建模拟二审结果
- 生成 15 个二审结果（5 误报 + 5 需人工 + 5 真实）
- **问题 3 准备**: review-results.json 已就绪

### 第 3 轮: 触发合并
- 运行 merge_review_results
- **问题**: merged=0, no_report=1（路径错误）
- 修复: ReviewMerger 路径兼容 `output_dir/report/report.json` 和 `output_dir/report.json`

### 第 4 轮: issue_id 匹配
- **问题**: issues 中无 `issue_id` 字段
- 修复: fallback 使用 `file:line:rule_id`

### 第 5 轮: 合并成功
- **merged=15, invalid=0** ✅
- 5 个 drop + 5 个 needs_review + 5 个 keep

### 第 6 轮: 路径修复
- 路径兼容修复后再合并: **merged=15** ✅

### 第 7 轮: subagent 任务顺序
- 删除原位置（前置）+ 在调用链关联后添加
- 修复完成

### 第 8 轮: 完整流程
- 清理 → 扫描 → 决策日志
- 验证: code_snippet=55, **call_chain=50**（V8 之前=0）✅

### 第 9 轮: 模拟 30 个二审
- 合并 30 个，0 invalid
- 13 drop + 6 needs_review + 11 keep
- merge_info 完整记录 ✅

### 第 10 轮: 全局 feedback 跨扫描
- 第 1 次: 2 条反馈
- 第 2 次: 读取 2 条历史 ✅
- 第 3 次: 读取 3 条累积历史 ✅

## 四、最终验证结果

| 问题 | 修复前 | 修复后 |
|------|--------|--------|
| 1. ai_confidence 默认 0.8 | 100% 假 0.8 | 100% None（未评审） |
| 2. ai_action 固定 keep | 100% keep | 100% pending_review（待二审） |
| 3. 无二审合并 | 0 合并 | 30 合并 0 invalid |
| 4. 反馈仅 workspace | 丢失历史 | 跨扫描累积 |
| 5. subagent 无 call_chain | 0 个 call_chain | 50 个 call_chain |

## 五、修改文件清单

- `scripts/scan.py` - 问题 1, 2, 4, 5 修复
- `scripts/review_merger.py` - 新建（问题 3）
- `harness/feedback_manager.py` - 问题 4 修复
- `config/harness.yaml` - 全局 feedback 路径（已存在）

## 六、总结

5 个问题全部修复，10 轮回归测试验证通过。系统现在支持:
- ✅ ai_confidence 不再默认 0.8（空值表示未评审）
- ✅ ai_action 根据置信度动态决策（drop/needs_review/keep）
- ✅ 完整二审结果读取、校验、合并流程
- ✅ 历史反馈跨扫描累积复用
- ✅ subagent 任务含完整 code_snippet + call_chain
