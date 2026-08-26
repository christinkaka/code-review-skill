# 子 Agent 评审任务

> 本文件由 scan.py 自动生成。主 Agent 读取本文件后，必须通过 Task 工具委派一个子 Agent 执行 AI 评审，不能自己直接评审。
>
> 输出字段契约唯一来源：`references/prompts/ai-enhancer-prompt.md`，不要修改字段名或输出格式。

## 扫描概要

- 仓库: `/private/tmp/test-e2e-repo`
- 分支对比: `main` -> `feature-vuln`
- 规约 Profile: `default`
- 评审工作流: `security`（安全审计工作流）
- 温度参数: `0.1`（低温度确保评审严谨性与一致性）
- 候选问题数: 2
- 扫描时间: 2026-08-26T14:35:23.042853

## 历史反馈统计

总反馈数: 0, 确认: 0, 误报: 0, 待定: 0

历史准确率: 暂无数据

## 近期反馈示例

- 暂无历史反馈

## 评审要求

1. 为每个判断提供**决策理由和证据**，禁止无依据结论
2. 标记误报（`is_false_positive = true` 时必须给出理由）
3. 输出 JSON 字段契约（严格遵守字段名）：

   ```json
   {
     "rule_id": "规则 ID",
     "is_false_positive": false,
     "ai_confidence": 0.92,
     "analysis": "分析说明",
     "enhanced_fix": "修复建议代码",
     "evidence": ["证据列表（引用具体代码行或上下文）"]
   }
   ```

## 待评审问题清单

1. **[ERROR]** `sqli-taint` — `VulnController.java:10`（引擎: semgrep）
   - 用户可控数据（HTTP 请求参数/头）经赋值、字符串拼接传播后流入 SQL 执行 API 或 SQL 构造 API。基于 Semgrep taint 模式做过程内数据流追踪，PreparedStatement 参数绑定（setString 等）作为净化器切断污点传播。
2. **[HIGH]** `redirect-pattern-2` — `VulnController.java:15`（引擎: semgrep）
   - 用户可控 URL 参数未经白名单校验直接流入 `sendRedirect`，导致钓鱼攻击或凭证泄露。
