# 子 Agent 评审任务

> 本文件由 scan.py 自动生成。主 Agent 读取本文件后，必须通过 Task 工具委派一个子 Agent 执行 AI 评审，不能自己直接评审。
>
> 输出字段契约唯一来源：`references/prompts/ai-enhancer-prompt.md`，不要修改字段名或输出格式。

## 投票委派要求（多数票模式）

> 本任务配置为 **3 评审员投票模式**（Self-Consistency）。
>
> 主 Agent 必须并行委派 **相互独立的** 3 个子 Agent 评审同一份任务文件，各评审员：
>
> 1. 使用相同的评审契约（本文件 + ai-enhancer-prompt.md）
> 2. 各自将结果写入独立文件：`ai-review-result-vote1.json` ~ `ai-review-result-vote3.json`
> 3. 评审员之间不得共享结论或互相参考
>
> 全部 3 份结果就绪后，`_merge_subagent_review` 按 (rule_id, file, line) 多数票聚合（≥ 2 票）：多数判误报则滤除、多数判真实则保留、无多数保守保留待人工。

## 扫描概要

- 仓库: `/tmp/spring-petclinic`
- 分支对比: `47be0ea` -> `9a5d50c`
- 规约 Profile: `default`
- 评审工作流: `security`（安全审计工作流）
- 温度参数: `0.1`（低温度确保评审严谨性与一致性）
- 候选问题数: 23
- 扫描时间: 2026-08-27T22:21:46.498570

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

1. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:99`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
2. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:105`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
3. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:111`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
4. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:197`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
5. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:198`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
6. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:208`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
7. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:221`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
8. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:226`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
9. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:231`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
10. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:243`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
11. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:246`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
12. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:267`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
13. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:268`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
14. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:269`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
15. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:270`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
16. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:279`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
17. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:343`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
18. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:346`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
19. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:354`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
20. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:356`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
21. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:357`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
22. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:358`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
23. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:388`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
