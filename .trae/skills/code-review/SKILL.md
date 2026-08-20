---
name: "code-review"
description: "自动化代码评审工具。对指定 Git 仓库执行分支差异扫描、调用链分析、多规约（设计/实现/安全）自动评审，输出结构化问题报告与修复建议。当用户需要代码扫描、代码评审、安全规约检查、分支差异分析、调用链追踪时调用。"
---

# Code Review Skill

基于分层规约库（设计/实现/安全）执行自动评审，输出结构化问题报告与修复建议。

**核心理念**：确定性锚点（Semgrep/正则）+ AI 增强 + LLM 无关 + 离线优先 + 用户确认

---

## 触发条件

- 代码评审 / 代码扫描
- 检查 release 与 master 分支差异
- 安全规约检查（越权、XXE、XSS、目录穿越等）
- 调用链分析
- 生成评审报告

---

## 工作流概览

```
Step 0: 环境准备（Python 3.8+、依赖安装、Semgrep 检测）
    ↓
Step 1: 策略识别（意图/规模/扫描策略/Profile）
    ↓
Step 1.5: 策略确认 ← 用户确认点（含外部规则加载交互）
    ↓
Step 2: 确定性扫描（Git diff + 调用图 + 规则匹配）
    ↓
Step 3: AI 增强评审（可选：误报过滤 + 分析 + 修复建议）
    ↓
Step 4: 结果合并与报告生成（JSON + Markdown → report/）
```

---

## Step 0: 环境准备

```bash
# 检测 Python
python3 --version  # 需要 3.8+

# 安装依赖（优先离线）
cd <skill-root>
if [ -d "offline-packages" ] && [ "$(ls -A offline-packages)" ]; then
    pip3 install --no-index --find-links=offline-packages -r requirements.txt
else
    pip3 install -r requirements.txt --break-system-packages
fi

# 检测 Semgrep（可选增强）
command -v semgrep && echo "Semgrep: $(semgrep --version)" || echo "Semgrep 未安装，使用正则引擎"
```

---

## Step 1: 策略识别与路由

### 扫描策略

| 策略 | 确定性扫描 | AI 增强 | 适用场景 |
|------|-----------|---------|----------|
| python-only | Semgrep/正则 | 无 | 快速扫描、离线 |
| ai-enhanced | Semgrep/正则 | 增强 | 日常评审（推荐） |
| hybrid | Semgrep（必须） | 增强 | 严格审查、安全审计 |

### 策略选择逻辑

```python
def select_scan_strategy(user_intent, semgrep_available, repo_size):
    if user_intent == "快速扫描": return "python-only"
    if user_intent == "严格审查" and semgrep_available: return "hybrid"
    return "ai-enhanced"  # 默认推荐
```

### 仓库规模评估

```bash
FILE_COUNT=$(find <repo> -type f \( -name "*.java" -o -name "*.py" -o -name "*.js" -o -name "*.ts" \) | wc -l)
# < 100: small (全量) | 100-1000: medium (增量) | > 1000: large (增量+分批)
```

---

## Step 1.5: 策略确认（用户确认点）

**⚠️ 执行前必须与用户确认策略。**

### 1.5.0 规则配置检测（AI 主动执行）

展示策略前，AI **必须主动执行**：

1. **检测项目语言**：扫描目标仓库主要编程语言
2. **检测已有外部规则**：检查 `references/external/` 是否已有规则
3. **匹配推荐规则库**：根据语言匹配

| 项目语言 | 推荐规则库 | 说明 |
|---|---|---|
| Java / Kotlin | android-security | OWASP MASTG 移动安全 |
| C / C++ | 0xdea-c-cpp | 内存安全、缓冲区溢出 |
| JavaScript / TypeScript | dom-xss | DOM XSS 深度检测 |
| 任意语言 | semgrep-official | OWASP Top 10 全集 |

### 1.5.1 展示策略

```
═══════════════════════════════════════════════════════════════
                    代码评审策略确认
═══════════════════════════════════════════════════════════════

## 1. 扫描策略
• 策略: ai-enhanced | Profile: default | 模式: 增量扫描

## 2. 规则配置
• 内部规则: 98 条（security 67 + design 16 + implementation 15）
• 外部规则: 0 条（尚未加载）
• 检测到项目语言: Java, Python
• 推荐: semgrep-official（15.8k stars）- OWASP Top 10 全集

## 3. AI 增强配置
• 温度: 0.1 | 置信度阈值: 0.7 | Few-shot 示例: 2 个

## 4. 预期输出
• report.json + report.md + summary.json → report/ 目录

═══════════════════════════════════════════════════════════════

请确认策略：
1. ✅ 确认执行
2. 📦 加载外部规则
3. 🔧 调整策略
4. ❌ 取消执行
```

### 1.5.2 处理用户反馈

**选择 1 "确认执行"** → 继续 Step 2

**选择 2 "加载外部规则"**（关键交互）：

**第一步**：展示推荐规则库

```
推荐的外部规则库：
1. semgrep-official（15.8k stars）- OWASP Top 10 全集，20000+ 规则
2. 0xdea-c-cpp（~500 stars）- C/C++ 内存安全
3. android-security（335 stars）- Android 移动安全
4. dom-xss（~30 stars）- JavaScript DOM XSS

请选择（可多选，如 1,3）：
```

**第二步**：用户选择后执行加载

```bash
python3 scripts/rule_loader.py --from recommended --repo-key <选择的库>
```

**第三步**：展示结果

```
已加载 50 条规则，来源: 0xdea-c-cpp
规则示例：raptor-write-into-stack-buffer、raptor-double-free...

是否继续加载？1. 继续  2. 完成，返回策略确认
```

**第四步**：更新策略展示，重新确认

**选择 3 "调整策略"** → 询问调整内容（策略/Profile/AI模式/置信度/外部规则管理）→ 重新展示

**选择 4 "取消执行"** → 取消

---

## Step 2: 确定性扫描（必须执行）

**这是确定性锚点，不依赖 LLM。**

```bash
# Git 差异分析
python3 scripts/diff_analyzer.py --repo <repo> --base master --target release/1.0 --output diff_result.json

# 调用图构建
python3 scripts/call_graph.py --repo <repo> --diff-result diff_result.json --output call_graph.json

# 规则匹配（Semgrep 或正则）
python3 scripts/rule_engine.py --repo <repo> --diff-result diff_result.json --specs-dir references/ --profile default --output deterministic_issues.json
```

**输出**：确定性问题列表，confidence=1.0，可重现。

---

## Step 3: AI 增强评审（可选）

```bash
python3 scripts/ai_enhancer.py \
  --deterministic-issues deterministic_issues.json \
  --diff-result diff_result.json \
  --call-graph call_graph.json \
  --prompt-template references/prompts/ai-enhancer-prompt.md \
  --enhance-mode full \
  --confidence-threshold 0.7 \
  --output enhanced_issues.json
```

### AI 约束

- ❌ 不能删除确定性问题
- ❌ 不能改变 severity / rule_id
- ✅ 可以标记误报（is_false_positive）
- ✅ 可以补充分析、修复建议、风险等级

### 提示词增强策略

详见 `references/prompts/ai-enhancer-prompt.md`：Few-shot 示例、JSON Schema 约束、角色设定、上下文锚定、温度 0.1、自我验证。

---

## Step 4: 结果合并与报告生成

```bash
python3 scripts/report_generator.py --scan-info scan_info.json --enhanced-issues enhanced_issues.json --output report/
```

输出：`report.json` + `report.md` + `summary.json`

---

## 规约库结构

```
references/
├── design/               # 设计规约（architecture/api-design/database）
├── implementation/       # 实现规约（naming/error-handling/concurrency/null-safety）
├── security/             # 安全规约（authorization/xxe/xss/path-traversal/...）
├── external/             # 外部加载规则（从 GitHub 高分仓库）
├── rules/                # 自定义业务规则
├── profiles/             # 规约配置（default/strict/minimal）
├── prompts/              # 提示词模板
└── test-cases/           # 测试案例
```

### Markdown 规约格式

```markdown
# XXE - DocumentBuilderFactory 未禁用外部实体
> XML 解析器未禁用外部实体，攻击者可读取服务器文件。

```yaml
id: xxe-java-document-builder
languages: [java]
severity: ERROR
cwe: CWE-611
```

## 违规示例
```java
DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
factory.parse(inputStream);
```

## 检测模式
```pattern
DocumentBuilderFactory $factory = DocumentBuilderFactory.newInstance();
...
$factory.parse(...);
```
```

---

## 规约预编译（推荐）

将自然语言规约转换为 Semgrep 规则，带安全审核机制。

**流程**：人写自然语言 → AI 生成规则草稿 → 差异对比 → **人工确认** → 部署

**⚠️ AI 行为要求**：禁止自动部署，必须等待用户确认。

详见 `references/rule-compiler-guide.md`

---

## 外部规则加载（推荐）

从高分开源规约库加载经过验证的规则，无需从零编写。

**推荐规则库**：Semgrep 官方（15.8k stars）、0xdea C/C++（~500）、Android Security（335）、DOM XSS（~30）

**⚠️ AI 行为要求**：策略确认阶段主动询问用户是否需要加载外部规则。

详见 `references/external-rules-guide.md`

---

## LLM 稳定性保障

**核心**：确定性锚点 + 结构化约束 + 提示词增强

1. **确定性锚点**：Python 脚本扫描的问题必须保留，AI 不能删除
2. **结构化输出**：强制 JSON Schema
3. **规则绑定**：severity/rule_id 由规则定义，AI 不能改
4. **置信度阈值**：AI 结果需达到 0.7 才被采纳
5. **回退机制**：AI 不稳定时回退到纯 Python 结果

无论使用 GPT-4/Claude/本地模型，**确定性问题列表始终一致**。

---

## 常见问题

**Q: 不同 LLM 结果不一致？** A: 确定性锚点保证核心结果一致，AI 增强只是锦上添花。

**Q: 如何选择扫描策略？** A: 快速→python-only | 日常→ai-enhanced | 严格→hybrid

**Q: AI 增强必须启用？** A: 不是必须，离线环境自动跳过。

**Q: 如何添加自定义规则？** A: 编辑 `references/rules/custom.md`，运行 `python scripts/test_rules.py` 验证。

**Q: 外部规则和内部规则冲突？** A: 独立管理，不会冲突。相同问题会分别报告。
