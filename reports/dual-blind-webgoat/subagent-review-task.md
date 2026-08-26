# 子 Agent 评审任务

> 本文件由 scan.py 自动生成。主 Agent 读取本文件后，必须通过 Task 工具委派一个子 Agent 执行 AI 评审，不能自己直接评审。
>
> 输出字段契约唯一来源：`references/prompts/ai-enhancer-prompt.md`，不要修改字段名或输出格式。

## 扫描概要

- 仓库: `repos/webgoat`
- 分支对比: `-` -> `-`
- 规约 Profile: `default`
- 评审工作流: `comprehensive`（综合评审工作流）
- 温度参数: `0.1`（低温度确保评审严谨性与一致性）
- 候选问题数: 22
- 扫描时间: -

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

1. **[ERROR]** `priv-java-runtime-exec` — `src/main/java/org/dummy/insecure/framework/VulnerableTaskHolder.java:67`（引擎: semgrep）
   - Runtime.exec() 执行用户可控命令，存在命令注入和提权风险。
2. **[CRITICAL]** `path-traversal-taint` — `src/main/java/org/owasp/webgoat/webwolf/FileServer.java:79`（引擎: semgrep）
   - 用户可控数据（HTTP 请求、上传文件名、反序列化结果）经任何赋值/拼接传播后流入文件路径操作。基于 Semgrep taint 模式做过程内数据流追踪，替代纯模式匹配：常量拼接与已净化（basename / 规范化）场景不再误报。
3. **[WARNING]** `err-java-empty-catch` — `.mvn/wrapper/MavenWrapperDownloader.java:67`（引擎: semgrep）
   - 空的 catch 块会吞掉异常，导致问题难以排查。
4. **[WARNING]** `null-java-collection-get` — `src/it/java/org/owasp/webgoat/playwright/webgoat/pages/lessons/LessonPage.java:43`（引擎: semgrep）
   - Map.get() 可能返回 null，直接调用方法会导致 NPE。
5. **[INFO]** `naming-java-constant-case` — `src/main/java/org/dummy/insecure/framework/VulnerableTaskHolder.java:19`（引擎: semgrep）
   - Java 常量（static final 字段）应使用 UPPER_SNAKE_CASE 命名。
6. **[WARNING]** `log-injection-taint` — `src/main/java/org/dummy/insecure/framework/VulnerableTaskHolder.java:71`（引擎: semgrep）
   - 用户可控数据（HTTP 请求参数/头/请求体）流入日志调用。攻击者可注入换行符 + 伪造日志条目，干扰日志分析和审计；若日志聚合到 Web 界面展示，还可能形成存储型 XSS。基于 Semgrep taint 模式做过程内数据流追踪。
7. **[WARNING]** `log-injection-taint` — `src/main/java/org/owasp/webgoat/container/AsciiDoctorTemplateResolver.java:139`（引擎: semgrep）
   - 用户可控数据（HTTP 请求参数/头/请求体）流入日志调用。攻击者可注入换行符 + 伪造日志条目，干扰日志分析和审计；若日志聚合到 Web 界面展示，还可能形成存储型 XSS。基于 Semgrep taint 模式做过程内数据流追踪。
8. **[WARNING]** `null-java-method-chain` — `src/main/java/org/owasp/webgoat/container/assignments/LessonTrackerInterceptor.java:54`（引擎: semgrep）
   - 链式调用未做空值检查，任一环节返回 null 将导致 NPE。
9. **[INFO]** `api-java-missing-response-wrapper` — `src/main/java/org/owasp/webgoat/container/mailbox/MailboxController.java:28`（引擎: semgrep）
   - Controller 返回值未使用统一包装类（如 Result<T>），建议统一响应格式。
10. **[WARNING]** `api-java-missing-validation` — `src/main/java/org/owasp/webgoat/container/mailbox/MailboxController.java:58`（引擎: semgrep）
   - @RequestBody 参数缺少 @Valid 注解，入参校验未启用。
11. **[INFO]** `api-java-missing-response-wrapper` — `src/main/java/org/owasp/webgoat/container/users/AdminController.java:33`（引擎: semgrep）
   - Controller 返回值未使用统一包装类（如 Result<T>），建议统一响应格式。
12. **[WARNING]** `db-java-missing-transaction` — `src/main/java/org/owasp/webgoat/container/users/DefaultUserInitializer.java:32`（引擎: semgrep）
   - 方法中执行多次数据库写操作但未添加 @Transactional，可能导致数据不一致。
13. **[WARNING]** `db-java-missing-transaction` — `src/main/java/org/owasp/webgoat/container/users/UserService.java:44`（引擎: semgrep）
   - 方法中执行多次数据库写操作但未添加 @Transactional，可能导致数据不一致。
14. **[WARNING]** `log-injection-taint` — `src/main/java/org/owasp/webgoat/webwolf/FileServer.java:79`（引擎: semgrep）
   - 用户可控数据（HTTP 请求参数/头/请求体）流入日志调用。攻击者可注入换行符 + 伪造日志条目，干扰日志分析和审计；若日志聚合到 Web 界面展示，还可能形成存储型 XSS。基于 Semgrep taint 模式做过程内数据流追踪。
15. **[INFO]** `api-java-missing-response-wrapper` — `src/main/java/org/owasp/webgoat/webwolf/jwt/JWTController.java:17`（引擎: semgrep）
   - Controller 返回值未使用统一包装类（如 Result<T>），建议统一响应格式。
16. **[WARNING]** `api-java-missing-validation` — `src/main/java/org/owasp/webgoat/webwolf/jwt/JWTController.java:25`（引擎: semgrep）
   - @RequestBody 参数缺少 @Valid 注解，入参校验未启用。
17. **[WARNING]** `api-java-missing-validation` — `src/main/java/org/owasp/webgoat/webwolf/jwt/JWTController.java:36`（引擎: semgrep）
   - @RequestBody 参数缺少 @Valid 注解，入参校验未启用。
18. **[WARNING]** `err-java-empty-catch` — `src/main/java/org/owasp/webgoat/webwolf/jwt/JWTToken.java:109`（引擎: semgrep）
   - 空的 catch 块会吞掉异常，导致问题难以排查。
19. **[WARNING]** `null-java-collection-get` — `src/main/java/org/owasp/webgoat/webwolf/jwt/JWTToken.java:178`（引擎: semgrep）
   - Map.get() 可能返回 null，直接调用方法会导致 NPE。
20. **[WARNING]** `log-injection-taint` — `src/main/java/org/owasp/webgoat/webwolf/requests/LandingPage.java:30`（引擎: semgrep）
   - 用户可控数据（HTTP 请求参数/头/请求体）流入日志调用。攻击者可注入换行符 + 伪造日志条目，干扰日志分析和审计；若日志聚合到 Web 界面展示，还可能形成存储型 XSS。基于 Semgrep taint 模式做过程内数据流追踪。
21. **[WARNING]** `null-java-method-chain` — `src/main/java/org/owasp/webgoat/webwolf/requests/Requests.java:73`（引擎: semgrep）
   - 链式调用未做空值检查，任一环节返回 null 将导致 NPE。
22. **[WARNING]** `null-java-method-chain` — `src/main/java/org/owasp/webgoat/webwolf/requests/WebWolfTraceRepository.java:69`（引擎: semgrep）
   - 链式调用未做空值检查，任一环节返回 null 将导致 NPE。
