# 子 Agent 评审任务

> 本文件由 scan.py 自动生成。主 Agent 读取本文件后，必须通过 Task 工具委派一个子 Agent 执行 AI 评审，不能自己直接评审。
>
> 输出字段契约唯一来源：`references/prompts/ai-enhancer-prompt.md`，不要修改字段名或输出格式。

## 扫描概要

- 仓库: `repos/freeCodeCamp`
- 分支对比: `-` -> `-`
- 规约 Profile: `default`
- 评审工作流: `comprehensive`（综合评审工作流）
- 温度参数: `0.1`（低温度确保评审严谨性与一致性）
- 候选问题数: 6
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

1. **[ERROR]** `xss-js-innerhtml` — `packages/challenge-builder/src/transformers.js:214`（引擎: semgrep）
   - innerHTML 直接赋值用户输入，存在 DOM 型 XSS 风险。
2. **[ERROR]** `xss-js-innerhtml` — `packages/challenge-builder/src/transformers.js:251`（引擎: semgrep）
   - innerHTML 直接赋值用户输入，存在 DOM 型 XSS 风险。
3. **[ERROR]** `xss-js-innerhtml` — `packages/challenge-builder/src/transformers.js:276`（引擎: semgrep）
   - innerHTML 直接赋值用户输入，存在 DOM 型 XSS 风险。
4. **[ERROR]** `xss-js-innerhtml` — `packages/challenge-builder/src/transformers.js:427`（引擎: semgrep）
   - innerHTML 直接赋值用户输入，存在 DOM 型 XSS 风险。
5. **[HIGH]** `crypto-hardcoded-key` — `tools/challenge-parser/parser/plugins/utils/i18n-stringify.js:7`（引擎: semgrep）
   - 密码、密钥、令牌等敏感信息硬编码在源代码中，攻击者获取源码后可直接获取凭据。
6. **[CRITICAL]** `path-write-traversal` — `tools/scripts/seed-exams/add-nano-ids.js:54`（引擎: semgrep）
   - 文件写入操作使用用户输入路径，攻击者可通过 `../` 覆盖系统关键文件（如 `/etc/passwd`、`crontab`、配置文件等）。
