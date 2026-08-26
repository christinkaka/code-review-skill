# 子 Agent 评审任务

> 本文件由 scan.py 自动生成。主 Agent 读取本文件后，必须通过 Task 工具委派一个子 Agent 执行 AI 评审，不能自己直接评审。
>
> 输出字段契约唯一来源：`references/prompts/ai-enhancer-prompt.md`，不要修改字段名或输出格式。

## 扫描概要

- 仓库: `repos/spring-boot`
- 分支对比: `-` -> `-`
- 规约 Profile: `default`
- 评审工作流: `comprehensive`（综合评审工作流）
- 温度参数: `0.1`（低温度确保评审严谨性与一致性）
- 候选问题数: 10
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

1. **[WARNING]** `null-java-unwrap-boxed` — `buildpack/spring-boot-buildpack-platform/src/main/java/org/springframework/boot/buildpack/platform/docker/TotalProgressListener.java:112`（引擎: semgrep）
   - Integer 自动拆箱为 int，若 Integer 为 null 将抛出 NullPointerException。
2. **[WARNING]** `err-java-empty-catch` — `buildpack/spring-boot-buildpack-platform/src/main/java/org/springframework/boot/buildpack/platform/docker/ssl/PemPrivateKeyParser.java:254`（引擎: semgrep）
   - 空的 catch 块会吞掉异常，导致问题难以排查。
3. **[WARNING]** `err-java-empty-catch` — `buildpack/spring-boot-buildpack-platform/src/main/java/org/springframework/boot/buildpack/platform/docker/ssl/PemPrivateKeyParser.java:263`（引擎: semgrep）
   - 空的 catch 块会吞掉异常，导致问题难以排查。
4. **[WARNING]** `null-java-method-chain` — `buildpack/spring-boot-buildpack-platform/src/main/java/org/springframework/boot/buildpack/platform/docker/transport/DockerConnectionException.java:51`（引擎: semgrep）
   - 链式调用未做空值检查，任一环节返回 null 将导致 NPE。
5. **[WARNING]** `null-java-unwrap-boxed` — `buildpack/spring-boot-buildpack-platform/src/main/java/org/springframework/boot/buildpack/platform/docker/type/ContainerStatus.java:55`（引擎: semgrep）
   - Integer 自动拆箱为 int，若 Integer 为 null 将抛出 NullPointerException。
6. **[WARNING]** `err-java-empty-catch` — `buildpack/spring-boot-buildpack-platform/src/main/java/org/springframework/boot/buildpack/platform/docker/type/Image.java:155`（引擎: semgrep）
   - 空的 catch 块会吞掉异常，导致问题难以排查。
7. **[WARNING]** `null-java-unwrap-boxed` — `buildpack/spring-boot-buildpack-platform/src/main/java/org/springframework/boot/buildpack/platform/docker/type/ImageArchiveIndex.java:51`（引擎: semgrep）
   - Integer 自动拆箱为 int，若 Integer 为 null 将抛出 NullPointerException。
8. **[WARNING]** `null-java-unwrap-boxed` — `buildpack/spring-boot-buildpack-platform/src/main/java/org/springframework/boot/buildpack/platform/docker/type/Manifest.java:55`（引擎: semgrep）
   - Integer 自动拆箱为 int，若 Integer 为 null 将抛出 NullPointerException。
9. **[WARNING]** `null-java-unwrap-boxed` — `buildpack/spring-boot-buildpack-platform/src/main/java/org/springframework/boot/buildpack/platform/docker/type/ManifestList.java:56`（引擎: semgrep）
   - Integer 自动拆箱为 int，若 Integer 为 null 将抛出 NullPointerException。
10. **[WARNING]** `crypto-weak-random-java` — `buildpack/spring-boot-buildpack-platform/src/main/java/org/springframework/boot/buildpack/platform/docker/type/RandomString.java:31`（引擎: semgrep）
   - 使用 java.util.Random 生成安全敏感场景的随机值，输出可被预测。
