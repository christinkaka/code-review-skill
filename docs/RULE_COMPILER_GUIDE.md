# 规约预编译器使用指南

## 概述

规约预编译器（`scripts/rule_compiler.py`）将自然语言安全规约转换为 Semgrep 规则，并通过安全审核机制确保规则质量。

**核心优势**：
- ✅ 降低规约编写门槛：只需写自然语言，无需学习 Semgrep 语法
- ✅ AI 辅助生成：自动理解规约语义并生成检测规则
- ✅ 安全审核机制：对比解读、回归测试、人工确认，避免 AI 幻觉
- ✅ 版本管理：保留历史版本，支持回滚

## 快速开始

### 1. 编写自然语言规约

在 `references/security/` 目录下创建 Markdown 文件，使用自然语言描述安全问题：

```markdown
# XXE 漏洞 - DocumentBuilder 未禁用外部实体

## 问题描述
当代码使用 DocumentBuilder 解析 XML 输入时，如果 DocumentBuilderFactory 没有禁用外部实体，
攻击者可以构造恶意 XML 读取服务器文件或发起 SSRF 攻击。

## 违规场景
- 创建了 DocumentBuilderFactory 实例
- 没有调用 setFeature() 禁用外部实体
- 使用该 Factory 创建了 DocumentBuilder
- 调用了 parse() 方法解析输入

## 安全做法
在创建 DocumentBuilderFactory 后，立即调用：
- factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true)
- factory.setFeature("http://xml.org/sax/features/external-general-entities", false)

## 严重等级
ERROR - 可能导致敏感文件泄露或 SSRF

## 示例代码

### 违规代码
```java
DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
DocumentBuilder builder = factory.newDocumentBuilder();
Document doc = builder.parse(xmlInput);
```

### 安全代码
```java
DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
DocumentBuilder builder = factory.newDocumentBuilder();
Document doc = builder.parse(xmlInput);
```
```

### 2. 编译规约

```bash
# 编译所有自然语言规约
python3 scripts/rule_compiler.py --specs-dir references/security/
```

编译器会：
1. 读取 Markdown 文件
2. 提取问题描述、违规场景、安全做法、示例代码
3. 调用 AI 生成 Semgrep 规则
4. 保存到 `references/security/compiled/` 目录
5. 保存版本历史到 `.history/` 目录

### 3. 对比规则差异

```bash
# 对比新旧规则差异
python3 scripts/rule_compiler.py --diff references/security/compiled/xxe.yaml
```

输出示例：
```json
{
  "status": "diff_generated",
  "previous_version": "references/security/compiled/.history/xxe_20260819_103000.yaml",
  "current_version": "references/security/compiled/xxe.yaml",
  "report": {
    "summary": "规则已更新",
    "changes": [
      {
        "type": "pattern_changed",
        "description": "检测模式已更新",
        "impact": "high",
        "recommendation": "建议使用测试用例验证新规则效果"
      }
    ],
    "recommendations": [
      "运行回归测试验证规则效果",
      "检查人审核差异报告后确认"
    ]
  }
}
```

### 4. 回归测试

```bash
# 用测试用例验证新规则效果
python3 scripts/rule_compiler.py \
  --diff references/security/compiled/xxe.yaml \
  --test references/test-cases/security/
```

测试会：
1. 用新规则扫描测试用例
2. 对比预期结果
3. 计算检出率和误报率

### 5. 人工确认并部署

```bash
# 人工确认后部署规则
python3 scripts/rule_compiler.py --approve references/security/compiled/xxe.yaml
```

确认后生成：
- `xxe.approved.yaml` - 已批准的规则
- 更新 `.approval_log.json` - 审批记录

### 6. 使用预编译规则

```bash
# 使用预编译规则扫描
python3 scripts/rule_engine.py \
  --repo /path/to/repo \
  --diff-result diff_result.json \
  --specs-dir references/security/compiled/ \
  --profile default \
  --output deterministic_issues.json
```

## 完整工作流

```
1. 编写自然语言规约
   └─ references/security/xxe.md

2. 编译规约
   └─ python3 scripts/rule_compiler.py --specs-dir references/security/
   └─ 输出: references/security/compiled/xxe.yaml

3. 对比差异
   └─ python3 scripts/rule_compiler.py --diff references/security/compiled/xxe.yaml
   └─ 查看 AI 解读的差异报告

4. 回归测试
   └─ python3 scripts/rule_compiler.py --diff references/security/compiled/xxe.yaml --test references/test-cases/security/
   └─ 验证规则效果

5. 人工确认
   └─ python3 scripts/rule_compiler.py --approve references/security/compiled/xxe.yaml
   └─ 输出: references/security/compiled/xxe.approved.yaml

6. 使用规则
   └─ python3 scripts/rule_engine.py --specs-dir references/security/compiled/ ...
```

## 安全审核机制

预编译器内置了四重安全审核机制，避免 AI 幻觉导致规则错乱：

### 1. AI 对比解读

每次编译后，AI 会生成新旧规则的语义差异报告：
- 检测范围变化（扩大还是缩小）
- 可能新增的误报或漏报
- 建议的测试用例

### 2. 回归测试

用测试用例验证新规则效果：
- 检出率：能否检测到已知漏洞
- 误报率：是否误报安全代码

### 3. 人工确认

检查人审核差异报告和测试结果后，确认是否部署：
- 查看差异报告
- 查看测试结果
- 确认无误后执行 `--approve`

### 4. 版本管理

保留所有历史版本：
- `.history/` 目录保存每次编译的结果
- 支持回滚到任意历史版本
- `.approval_log.json` 记录审批历史

## 常见问题

### Q1: 预编译器和现有的 rule_engine.py 是什么关系？

**A**: 预编译器是 rule_engine.py 的前置步骤：
- `rule_compiler.py`：将自然语言规约转换为 Semgrep 规则
- `rule_engine.py`：使用 Semgrep 规则扫描代码

### Q2: 预编译需要 AI 吗？

**A**: 是的，预编译器需要调用 AI 理解自然语言并生成 Semgrep 规则。但扫描时不需要 AI，只需要 Semgrep。

### Q3: 如何回滚到历史版本？

**A**: 从 `.history/` 目录复制历史版本到 `compiled/` 目录：

```bash
cp references/security/compiled/.history/xxe_20260819_103000.yaml \
   references/security/compiled/xxe.yaml
```

### Q4: 预编译后的规则和手动编写的规则可以混用吗？

**A**: 可以。预编译后的规则保存在 `compiled/` 目录，手动编写的规则保存在 `security/` 目录，可以分别使用或合并使用。

### Q5: 如何强制重新编译？

**A**: 使用 `--force` 参数：

```bash
python3 scripts/rule_compiler.py --specs-dir references/security/ --force
```

## 最佳实践

1. **先写自然语言规约**：用自然语言描述问题，不要直接写 Semgrep 语法
2. **提供清晰的违规场景**：列出具体的违规步骤，帮助 AI 理解
3. **提供违规和安全代码示例**：帮助 AI 学习检测模式
4. **运行回归测试**：每次编译后都要运行测试，验证规则效果
5. **人工确认后再部署**：不要跳过人工确认步骤
6. **定期审查审批记录**：查看 `.approval_log.json`，了解规则变更历史

## 技术细节

### 预编译器架构

```
RuleCompiler
├── compile_all()              # 编译所有规约
├── compile_rule()             # 编译单个规约
├── _extract_metadata()        # 提取元数据
├── _extract_section()         # 提取章节内容
├── _extract_code_block()      # 提取代码块
├── _generate_semgrep_rule_with_ai()  # AI 生成规则
├── diff_rules()               # 对比规则差异
├── _generate_diff_report_with_ai()   # AI 生成差异报告
├── run_regression_test()      # 回归测试
└── approve_and_deploy()       # 人工确认并部署
```

### 输出格式

预编译后的规则是标准 Semgrep YAML 格式：

```yaml
rules:
  - id: xxe-documentbuilder
    message: XXE 漏洞 - DocumentBuilder 未禁用外部实体
    severity: ERROR
    languages: [java]
    pattern: |
      DocumentBuilderFactory $FACTORY = DocumentBuilderFactory.newInstance();
      ...
      DocumentBuilder $BUILDER = $FACTORY.newDocumentBuilder();
      ...
      $BUILDER.parse(...);
    metadata:
      violation_scenario: |
        - 创建了 DocumentBuilderFactory 实例
        - 没有调用 setFeature() 禁用外部实体
        - 使用该 Factory 创建了 DocumentBuilder
        - 调用了 parse() 方法解析输入
      safe_approach: |
        在创建 DocumentBuilderFactory 后，立即调用：
        - factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true)
        - factory.setFeature("http://xml.org/sax/features/external-general-entities", false)
      compiled_at: '2026-08-19T10:30:00'
      source_file: XXE 漏洞 - DocumentBuilder 未禁用外部实体
```

## 总结

规约预编译器让安全规约编写变得更简单、更安全：
- ✅ 降低门槛：只需写自然语言
- ✅ AI 辅助：自动生成 Semgrep 规则
- ✅ 安全审核：对比解读、回归测试、人工确认
- ✅ 版本管理：保留历史，支持回滚

开始使用预编译器，让你的安全规约编写更高效！
