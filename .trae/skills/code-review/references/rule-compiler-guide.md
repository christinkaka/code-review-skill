# 规约预编译详细指南

## 流程概览

```
人写自然语言规约（纯 Markdown，无需 Semgrep 语法）
    ↓
AI 理解并生成 Semgrep 规则草稿
    ↓
AI 对比解读新旧规则差异
    ↓
【AI 必须等待用户确认】← 关键控制点
    ↓
回归测试验证规则效果（可选）
    ↓
用户确认后生成最终规则
```

## ⚠️ AI 行为要求

1. **禁止自动部署**：不得直接执行 `--approve`，必须等待用户确认
2. **展示差异报告**：编译后必须展示新旧规则差异
3. **等待用户确认**：明确询问用户是否确认部署
4. **记录确认过程**：记录确认时间和内容

## 自然语言规约格式

```markdown
# XXE 漏洞 - DocumentBuilder 未禁用外部实体

## 问题描述
当代码使用 DocumentBuilder 解析 XML 输入时，如果未禁用外部实体，
攻击者可构造恶意 XML 读取服务器文件。

## 违规场景
- 创建了 DocumentBuilderFactory 且未禁用外部实体
- 用它创建 DocumentBuilder 并调用 parse()

## 安全做法
创建 Factory 后立即 setFeature 禁用 DTD 和外部实体

## 严重等级
ERROR

## 示例代码
### 违规代码
```java
DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
DocumentBuilder builder = factory.newDocumentBuilder();
builder.parse(xmlInput);
```
### 安全代码
```java
DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
DocumentBuilder builder = factory.newDocumentBuilder();
builder.parse(xmlInput);
```
```

## 命令

```bash
# 编译所有自然语言规约
python3 scripts/rule_compiler.py --specs-dir references/security/

# 强制重新编译
python3 scripts/rule_compiler.py --specs-dir references/security/ --force

# 对比新旧规则差异
python3 scripts/rule_compiler.py --diff references/security/compiled/xxe.yaml

# 回归测试
python3 scripts/rule_compiler.py --diff references/security/compiled/xxe.yaml --test references/test-cases/security/

# 人工确认后部署（交互式）
python3 scripts/rule_compiler.py --approve references/security/compiled/xxe.yaml
```

## 输出目录

```
references/security/compiled/
├── xxe.yaml              # 编译后的 Semgrep 规则
├── xxe.approved.yaml     # 已批准的规则
├── .history/             # 版本历史
└── .approval_log.json    # 审批记录
```
