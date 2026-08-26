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

- 仓库: `/tmp/ruoyi-e2e`
- 分支对比: `v4.8.0` -> `v4.8.1`
- 规约 Profile: `default`
- 评审工作流: `security`（安全审计工作流）
- 温度参数: `0.1`（低温度确保评审严谨性与一致性）
- 候选问题数: 45
- 扫描时间: 2026-08-26T19:13:40.105813

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

1. **[WARNING]** `api-java-rest-naming` — `ruoyi-admin/src/main/java/com/ruoyi/web/controller/system/SysMenuController.java:150`（引擎: semgrep）
   - GET 接口应使用名词复数形式，不应使用动词前缀。
2. **[ERROR]** `xss-js-innerhtml` — `ruoyi-admin/src/main/resources/static/ajax/libs/bootstrap-fileinput/fileinput.js:242`（引擎: semgrep）
   - innerHTML 直接赋值用户输入，存在 DOM 型 XSS 风险。
3. **[INFO]** `naming-java-constant-case` — `ruoyi-common/src/main/java/com/ruoyi/common/core/domain/entity/SysUser.java:23`（引擎: semgrep）
   - Java 常量（static final 字段）应使用 UPPER_SNAKE_CASE 命名。
4. **[INFO]** `naming-java-constant-case` — `ruoyi-common/src/main/java/com/ruoyi/common/core/page/TableDataInfo.java:13`（引擎: semgrep）
   - Java 常量（static final 字段）应使用 UPPER_SNAKE_CASE 命名。
5. **[INFO]** `naming-java-boolean-vague` — `ruoyi-common/src/main/java/com/ruoyi/common/utils/ServletUtils.java:166`（引擎: semgrep）
   - 布尔变量名应表达判断语义（如 isActive、found、enabled、hasNext），
6. **[INFO]** `naming-java-constant-case` — `ruoyi-common/src/main/java/com/ruoyi/common/utils/poi/ExcelUtil.java:112`（引擎: semgrep）
   - Java 常量（static final 字段）应使用 UPPER_SNAKE_CASE 命名。
7. **[WARNING]** `err-java-empty-catch` — `ruoyi-common/src/main/java/com/ruoyi/common/utils/poi/ExcelUtil.java:1417`（引擎: semgrep）
   - 空的 catch 块会吞掉异常，导致问题难以排查。
8. **[INFO]** `naming-java-constant-case` — `ruoyi-common/src/main/java/com/ruoyi/common/utils/uuid/UUID.java:17`（引擎: semgrep）
   - Java 常量（static final 字段）应使用 UPPER_SNAKE_CASE 命名。
9. **[WARNING]** `null-java-method-chain` — `ruoyi-framework/src/main/java/com/ruoyi/framework/aspectj/LogAspect.java:112`（引擎: semgrep）
   - 链式调用未做空值检查，任一环节返回 null 将导致 NPE。
10. **[WARNING]** `err-java-empty-catch` — `ruoyi-framework/src/main/java/com/ruoyi/framework/aspectj/LogAspect.java:209`（引擎: semgrep）
   - 空的 catch 块会吞掉异常，导致问题难以排查。
11. **[WARNING]** `err-java-empty-catch` — `ruoyi-framework/src/main/java/com/ruoyi/framework/shiro/web/filter/kickout/KickoutSessionFilter.java:102`（引擎: semgrep）
   - 空的 catch 块会吞掉异常，导致问题难以排查。
12. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:47`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
13. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:56`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
14. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:65`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
15. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:71`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
16. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:78`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
17. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:84`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
18. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:90`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
19. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:97`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
20. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:104`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
21. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:111`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
22. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:118`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
23. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:125`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
24. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:132`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
25. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:139`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
26. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:146`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
27. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:153`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
28. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:160`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
29. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:173`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
30. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:180`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
31. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:187`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
32. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:194`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
33. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:201`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
34. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:208`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
35. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:215`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
36. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:222`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
37. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:229`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
38. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:257`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
39. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:258`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
40. **[ERROR]** `sqli-mybatis-dollar` — `pom.xml:259`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
41. **[ERROR]** `sqli-mybatis-dollar` — `ruoyi-admin/pom.xml:95`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
42. **[ERROR]** `sqli-mybatis-dollar` — `ruoyi-admin/pom.xml:132`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
43. **[ERROR]** `sqli-mybatis-dollar` — `ruoyi-system/src/main/resources/mapper/system/SysUserMapper.xml:88`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
44. **[ERROR]** `sqli-mybatis-dollar` — `ruoyi-system/src/main/resources/mapper/system/SysUserMapper.xml:105`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
45. **[ERROR]** `sqli-mybatis-dollar` — `ruoyi-system/src/main/resources/mapper/system/SysUserMapper.xml:123`（引擎: ast）
   - [SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。
