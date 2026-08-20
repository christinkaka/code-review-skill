---
name: "code-review"
description: "自动化代码评审工具。对指定 Git 仓库执行分支差异扫描、调用链分析、多规约（设计/实现/安全）自动评审，输出结构化问题报告与修复建议。当用户需要代码扫描、代码评审、安全规约检查、分支差异分析、调用链追踪时调用。"
---

# Code Review Skill

自动化代码评审技能，支持定期扫描 release 分支与 master 分支的差异，基于分层规约库（设计规约、代码实现规约、安全规约、自定义 rules）执行自动评审，输出结构化的问题报告与修复建议。

**核心设计理念**：
- **确定性锚点**：Python 脚本（Semgrep/正则）作为确定性锚点，确保结果稳定
- **AI 增强**：AI 只负责增强和过滤，不能改变确定性结果
- **离线优先**：所有核心功能离线可用，最小化外部依赖
- **LLM 无关**：通过结构化输出和规则绑定，确保不同 LLM 结果一致
- **用户确认**：执行前与用户确认策略，确保符合预期

---

## 触发条件

当用户请求以下操作时激活本 Skill：
- 对代码仓库执行代码评审 / 代码扫描
- 检查 release 分支与 master 分支的差异
- 运行安全规约检查（越权、XXE、XSS、目录穿越等）
- 分析代码调用链或血缘关系
- 生成评审报告

---

## 工作流概览

```
┌─────────────────────────────────────────────────────────────┐
│  Step 0: 环境准备                                            │
│  ├─ 检测 Python 版本                                         │
│  ├─ 安装依赖（离线包优先）                                    │
│  └─ 检测 Semgrep 是否可用（可选增强）                         │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 1: 策略识别与路由                                       │
│  ├─ 识别用户意图（全量扫描/安全扫描/严格审查）                  │
│  ├─ 评估仓库规模（小/中/大）                                  │
│  ├─ 选择扫描策略（python-only / ai-enhanced / hybrid）        │
│  └─ 选择规约 Profile（default/strict/minimal）                │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 1.5: 策略确认（用户确认点）                             │
│  ├─ 展示完整策略（扫描策略 + 提示词增强 + 预期输出）          │
│  ├─ 等待用户确认                                             │
│  └─ 用户可选择调整策略或继续执行                             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 2: 确定性扫描（Python 脚本，必须执行）                   │
│  ├─ Git 差异分析（提取变更文件和方法）                         │
│  ├─ 调用图构建（追踪血缘关系）                                │
│  ├─ 规则匹配（Semgrep/正则）                                 │
│  └─ 输出：确定性问题列表（deterministic_issues）              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 3: AI 增强评审（可选，如果策略包含 AI）                  │
│  ├─ 读取确定性问题列表                                        │
│  ├─ AI 分析上下文（过滤误报）                                 │
│  ├─ AI 补充分析说明（问题原因、风险等级）                     │
│  ├─ AI 生成修复建议（具体代码）                               │
│  └─ 输出：增强后的问题列表（enhanced_issues）                 │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 4: 结果合并与报告生成                                   │
│  ├─ 合并确定性问题 + AI 增强结果                              │
│  ├─ 格式化报告（JSON + Markdown）                            │
│  ├─ 统计摘要（按规约类型、严重等级、文件维度）                  │
│  └─ 输出到 report/ 目录                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Step 0: 环境准备

### 0.1 检测 Python 版本

```bash
python3 --version  # 需要 Python 3.8+
```

### 0.2 安装依赖

**优先使用离线安装**（无需网络，更快）：

```bash
cd <skill-root>

# 检查离线包是否存在
if [ -d "offline-packages" ] && [ "$(ls -A offline-packages)" ]; then
    echo "使用离线安装..."
    pip3 install --no-index --find-links=offline-packages -r requirements.txt
else
    echo "使用在线安装..."
    pip3 install -r requirements.txt --break-system-packages
fi
```

**离线包位置**：`<skill-root>/offline-packages/`（约 19MB，包含 20 个依赖包）

### 0.3 检测 Semgrep 是否可用（可选增强）

```bash
# 检测 Semgrep（可选，不是必须的）
if command -v semgrep &> /dev/null; then
    SEMGREP_AVAILABLE=true
    echo "Semgrep 已安装: $(semgrep --version)"
    echo "将使用 Semgrep 进行精准模式匹配"
else
    SEMGREP_AVAILABLE=false
    echo "Semgrep 未安装，将使用正则引擎"
fi
```

### 0.4 环境检测结果汇总

```
环境检测结果：
├─ Python: 3.10.20 ✅
├─ 依赖安装: 离线安装 ✅
├─ Semgrep: 已安装 ✅ / 未安装（使用正则）⚠️
└─ 外部 API: 不需要 ✅（AI 增强可选）
```

---

## Step 1: 策略识别与路由

### 1.1 识别用户意图

根据用户的请求，自动选择合适的扫描策略：

| 用户意图 | 关键词 | 推荐策略 | 说明 |
|----------|--------|----------|------|
| **快速扫描** | "快速检查"、"简单扫描" | `python-only` | 仅 Python 脚本，最快 |
| **全量扫描** | "代码评审"、"全面检查" | `ai-enhanced` | Python + AI 增强（推荐） |
| **严格审查** | "严格审查"、"深度检查" | `hybrid` | Semgrep + AI（最精准） |
| **安全扫描** | "安全扫描"、"漏洞检查" | `ai-enhanced` | Python + AI 增强 |

### 1.2 评估仓库规模

```bash
# 统计仓库文件数
FILE_COUNT=$(find <repo-path> -type f \( -name "*.java" -o -name "*.py" -o -name "*.js" -o -name "*.ts" \) | wc -l)

if [ $FILE_COUNT -lt 100 ]; then
    REPO_SIZE="small"
    SCAN_MODE="full"        # 全量扫描
elif [ $FILE_COUNT -lt 1000 ]; then
    REPO_SIZE="medium"
    SCAN_MODE="incremental" # 增量扫描
else
    REPO_SIZE="large"
    SCAN_MODE="incremental" # 增量扫描 + 分批处理
fi
```

### 1.3 选择扫描策略

**策略说明**：

| 策略 | 确定性扫描 | AI 增强 | 适用场景 | LLM 依赖 |
|------|-----------|---------|----------|----------|
| **python-only** | ✅ Semgrep/正则 | ❌ 无 | 快速扫描、离线环境 | 无 |
| **ai-enhanced** | ✅ Semgrep/正则 | ✅ 增强 | 日常评审（推荐） | 可选 |
| **hybrid** | ✅ Semgrep（必须） | ✅ 增强 | 严格审查、安全审计 | 可选 |

**策略选择逻辑**：

```python
def select_scan_strategy(user_intent, semgrep_available, repo_size):
    if user_intent == "快速扫描":
        return "python-only"
    
    if user_intent == "严格审查" and semgrep_available:
        return "hybrid"
    
    # 默认推荐：ai-enhanced
    return "ai-enhanced"
```

### 1.4 策略选择结果汇总

```
策略选择结果：
├─ 用户意图: 全量扫描
├─ 仓库规模: 中型 (450 个文件)
├─ 扫描策略: ai-enhanced（Python + AI 增强）
├─ 扫描 Profile: default
├─ 扫描模式: 增量扫描
└─ LLM 依赖: 可选（AI 增强可选）
```

---

## Step 1.5: 策略确认（用户确认点）

**⚠️ 这是用户确认点，执行前必须与用户确认策略。**

### 1.5.0 规则配置检测（AI 主动执行）

在展示策略前，AI 必须**主动执行以下检测**：

1. **检测项目语言**：扫描目标仓库的主要编程语言
2. **检测已有外部规则**：检查 `references/external/` 目录是否已有加载的规则
3. **匹配推荐规则库**：根据项目语言，从推荐规则库中匹配合适的库

**AI 必须根据检测结果，在策略展示中主动推荐外部规则**，而不是等用户自己发现。

推荐匹配逻辑：

| 项目语言 | 推荐规则库 | 说明 |
|---|---|---|
| Java / Kotlin | android-security | OWASP MASTG 移动安全 |
| C / C++ | 0xdea-c-cpp | 内存安全、缓冲区溢出 |
| JavaScript / TypeScript | dom-xss | DOM XSS 深度检测 |
| 任意语言 | semgrep-official | OWASP Top 10 全集 |

### 1.5.1 展示完整策略

在执行扫描前，向用户展示完整的执行策略，包括：

```
═══════════════════════════════════════════════════════════════
                    代码评审策略确认
═══════════════════════════════════════════════════════════════

## 1. 扫描策略

┌─────────────────────────────────────────────────────────────┐
│ 扫描策略: ai-enhanced（Python + AI 增强）                    │
├─────────────────────────────────────────────────────────────┤
│ • 确定性扫描: Semgrep/正则（确保结果稳定）                   │
│ • AI 增强: 启用（补充分析 + 修复建议）                       │
│ • 扫描 Profile: default（全部规约）                          │
│ • 扫描模式: 增量扫描（只扫描变更文件）                       │
└─────────────────────────────────────────────────────────────┘

## 2. 规则配置

┌─────────────────────────────────────────────────────────────┐
│ 内部规则: 98 条（security 67 + design 16 + implementation 15）│
│ 外部规则: 0 条（尚未加载）                                    │
├─────────────────────────────────────────────────────────────┤
│ 检测到项目语言: Java, Python                                  │
│ 推荐加载的外部规则库:                                         │
│   • semgrep-official（15.8k stars）- OWASP Top 10 全集       │
│   • android-security（335 stars）- 移动安全（如适用）         │
└─────────────────────────────────────────────────────────────┘

## 3. 提示词增强配置
...（其余配置不变）

═══════════════════════════════════════════════════════════════
```

### 1.5.2 等待用户确认

**向用户提问**：

```
请确认以上策略是否符合您的预期？

选项：
1. ✅ 确认执行 - 按照以上策略执行扫描
2. 📦 加载外部规则 - 从推荐规则库加载经过验证的规则
3. 🔧 调整策略 - 修改扫描策略或提示词配置
4. ❌ 取消执行 - 取消本次扫描

请输入选项（1/2/3/4）：
```

### 1.5.3 处理用户反馈

**如果用户选择"确认执行"**：
- 继续执行 Step 2（确定性扫描）

**如果用户选择"加载外部规则"**（关键交互流程）：

AI 必须按以下步骤引导用户：

**第一步：展示推荐规则库**

```
以下是推荐的外部规则库：

1. semgrep-official（15.8k stars）
   覆盖: OWASP Top 10 全集，20000+ 规则
   语言: Java, Python, JavaScript, TypeScript, Go, C, C++

2. 0xdea-c-cpp（~500 stars）
   覆盖: C/C++ 内存安全（缓冲区溢出、use-after-free、整数溢出）
   语言: C, C++

3. android-security（335 stars）
   覆盖: Android 移动安全，基于 OWASP MASTG
   语言: Java, Kotlin

4. dom-xss（~30 stars）
   覆盖: JavaScript DOM XSS 深度检测
   语言: JavaScript, TypeScript

请选择要加载的规则库（可多选，如 1,3）：
```

**第二步：等待用户选择**

用户选择后，AI 执行加载命令：

```bash
python3 scripts/rule_loader.py --from recommended --repo-key <用户选择的库>
```

**第三步：展示加载结果**

```
已加载 50 条规则，来源: 0xdea-c-cpp

规则示例：
  - raptor-write-into-stack-buffer（栈缓冲区溢出）
  - raptor-double-free（双重释放）
  - raptor-command-injection（命令注入）
  ...

是否继续加载其他规则库？
1. 继续加载
2. 完成，返回策略确认
```

**第四步：更新策略并重新确认**

加载完成后，AI 更新策略展示中的"规则配置"板块，重新展示完整策略，等待用户最终确认。

**如果用户选择"调整策略"**：
- 询问用户要调整的内容：
  - 扫描策略（python-only / ai-enhanced / hybrid）
  - 扫描 Profile（default / strict / minimal）
  - AI 增强模式（full / analysis-only / filter-only / none）
  - 提示词模板（使用自定义模板）
  - 置信度阈值（0.5 / 0.7 / 0.9）
  - 管理外部规则（查看已加载 / 移除规则 / 从自定义仓库加载）
- 根据用户反馈调整策略
- 重新展示策略，等待用户确认

**如果用户选择"取消执行"**：
- 取消本次扫描
- 输出取消信息

### 1.5.4 策略确认记录

```
策略确认记录：
├─ 确认时间: 2026-07-28T10:30:00
├─ 用户选择: 确认执行
├─ 扫描策略: ai-enhanced
├─ 提示词模板: COMPREHENSIVE_AI_PROMPT
├─ AI 增强模式: full
├─ 置信度阈值: 0.7
├─ 内部规则: 98 条
└─ 外部规则: 50 条（来源: 0xdea-c-cpp）
```

---

## Step 2: 确定性扫描（Python 脚本，必须执行）

**这是确定性锚点，确保结果稳定，不依赖 LLM。**

### 2.1 Git 差异分析

```bash
cd <skill-root>

# 提取分支差异
python3 scripts/diff_analyzer.py \
  --repo <repo-path> \
  --base master \
  --target release/1.0 \
  --output diff_result.json
```

**输出**：
```json
{
  "changed_files": [
    {"path": "src/main/java/com/example/Parser.java", "status": "modified", "additions": 15, "deletions": 3}
  ],
  "changed_methods": [
    {"file": "src/main/java/com/example/Parser.java", "name": "parseXml", "line": 42}
  ],
  "stats": {"files_changed": 5, "insertions": 45, "deletions": 12}
}
```

### 2.2 调用图构建

```bash
# 构建调用图（追踪血缘关系）
python3 scripts/call_graph.py \
  --repo <repo-path> \
  --diff-result diff_result.json \
  --output call_graph.json
```

### 2.3 规则匹配（确定性扫描）

```bash
# 执行规则匹配（Semgrep 或正则）
python3 scripts/rule_engine.py \
  --repo <repo-path> \
  --diff-result diff_result.json \
  --specs-dir references/ \
  --profile default \
  --output deterministic_issues.json
```

**输出（确定性问题列表）**：
```json
{
  "scan_info": {
    "engine": "semgrep",
    "timestamp": "2026-07-28T10:30:00",
    "duration_seconds": 12.5
  },
  "deterministic_issues": [
    {
      "rule_id": "xxe-java-document-builder",
      "category": "security",
      "severity": "ERROR",
      "file": "src/main/java/com/example/Parser.java",
      "line": 42,
      "end_line": 45,
      "message": "DocumentBuilderFactory 未禁用外部实体，存在 XXE 风险",
      "code_snippet": "DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();",
      "fix": "factory.setFeature(\"http://apache.org/xml/features/disallow-doctype-decl\", true);",
      "metadata": {"cwe": "CWE-611", "owasp": "A05:2021"},
      "confidence": 1.0,
      "source": "semgrep"
    }
  ]
}
```

**关键特性**：
- **确定性**：同样的代码、同样的规则，结果完全一致
- **可重现**：不依赖 LLM，可以重复验证
- **高置信度**：confidence = 1.0，表示确定性匹配

---

## Step 3: AI 增强评审（可选，如果策略包含 AI）

**AI 只负责增强和过滤，不能改变确定性结果。**

### 3.1 AI 增强策略

```bash
# 执行 AI 增强评审（可选）
python3 scripts/ai_enhancer.py \
  --deterministic-issues deterministic_issues.json \
  --diff-result diff_result.json \
  --call-graph call_graph.json \
  --prompt-template references/prompts/ai-enhancer-prompt.md \
  --enhance-mode full \
  --confidence-threshold 0.7 \
  --output enhanced_issues.json
```

**AI 增强模式**：

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| **full** | 完整增强（分析 + 修复建议） | 日常评审 |
| **analysis-only** | 仅分析说明 | 快速评审 |
| **filter-only** | 仅过滤误报 | 高精度要求 |
| **none** | 不增强 | 离线环境 |

### 3.2 AI 增强流程

```
AI 增强流程：
│
├─ [1] 读取确定性问题列表
│   └─ 读取 deterministic_issues.json
│
├─ [2] 加载提示词模板
│   └─ 加载 references/prompts/ai-enhancer-prompt.md
│
├─ [3] AI 分析上下文（过滤误报）
│   ├─ 对于每个确定性问题
│   ├─ AI 分析代码上下文
│   ├─ AI 判断是否为误报
│   └─ 标记：is_false_positive = true/false
│
├─ [4] AI 补充分析说明
│   ├─ 问题原因分析
│   ├─ 风险等级评估
│   └─ 影响范围分析
│
├─ [5] AI 生成修复建议
│   ├─ 具体的代码修改
│   ├─ 修改原因说明
│   └─ 相关文档链接（如果有）
│
├─ [6] 置信度过滤
│   ├─ 检查 ai_confidence >= 0.7
│   └─ 低于阈值的问题不采纳 AI 结果
│
└─ [7] 输出增强后的问题列表
    └─ enhanced_issues.json
```

### 3.3 AI 增强输出

```json
{
  "enhanced_issues": [
    {
      "rule_id": "xxe-java-document-builder",
      "category": "security",
      "severity": "ERROR",
      "file": "src/main/java/com/example/Parser.java",
      "line": 42,
      "message": "DocumentBuilderFactory 未禁用外部实体，存在 XXE 风险",
      "code_snippet": "DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();",
      "fix": "factory.setFeature(\"http://apache.org/xml/features/disallow-doctype-decl\", true);",
      "metadata": {"cwe": "CWE-611", "owasp": "A05:2021"},
      
      "deterministic_fields": {
        "confidence": 1.0,
        "source": "semgrep"
      },
      
      "ai_enhancement": {
        "is_false_positive": false,
        "ai_confidence": 0.92,
        "analysis": "该代码处理外部 XML 输入，未禁用外部实体，攻击者可构造恶意 XML 读取服务器文件。建议立即修复。",
        "risk_level": "CRITICAL",
        "impact_scope": "影响所有调用 parseXml() 方法的地方",
        "enhanced_fix": "factory.setFeature(\"http://apache.org/xml/features/disallow-doctype-decl\", true);\nfactory.setFeature(\"http://xml.org/sax/features/external-general-entities\", false);",
        "references": ["https://owasp.org/Top10/A05_2021-Security_Misconfiguration/"]
      }
    }
  ]
}
```

### 3.4 AI 增强的关键约束

**AI 不能做的事**：
- ❌ 删除确定性问题（确定性问题是必须保留的）
- ❌ 改变问题的 severity（severity 由规则定义）
- ❌ 改变问题的 rule_id（rule_id 由规则定义）

**AI 可以做的事**：
- ✅ 标记误报（is_false_positive = true）
- ✅ 补充分析说明（analysis）
- ✅ 生成修复建议（enhanced_fix）
- ✅ 评估风险等级（risk_level）
- ✅ 分析影响范围（impact_scope）

---

## Step 4: 结果合并与报告生成

### 4.1 结果合并

```bash
# 合并结果并生成报告
python3 scripts/report_generator.py \
  --scan-info scan_info.json \
  --enhanced-issues enhanced_issues.json \
  --output report/
```

### 4.2 输出文件

```
report/
├─ report.json          # 结构化 JSON 报告（供下游系统消费）
├─ report.md            # 可读的 Markdown 报告
└─ summary.json         # 统计摘要（按规约类型、严重等级、文件维度）
```

### 4.3 报告内容

**JSON 报告结构**：
```json
{
  "scan_info": {
    "repo": "/path/to/repo",
    "base_branch": "master",
    "target_branch": "release/1.0",
    "profile": "default",
    "strategy": "ai-enhanced",
    "deterministic_engine": "semgrep",
    "ai_enhancement": true,
    "prompt_template": "COMPREHENSIVE_AI_PROMPT",
    "confidence_threshold": 0.7,
    "timestamp": "2026-07-28T10:30:00",
    "duration_seconds": 45.2
  },
  "summary": {
    "total": 10,
    "deterministic": 10,
    "ai_enhanced": 10,
    "false_positives": 2,
    "critical": 2,
    "high": 3,
    "medium": 5,
    "by_category": {
      "security": 6,
      "design": 2,
      "implementation": 2
    }
  },
  "issues": [
    {
      "rule_id": "xxe-java-document-builder",
      "category": "security",
      "severity": "ERROR",
      "file": "src/main/java/com/example/Parser.java",
      "line": 42,
      "message": "DocumentBuilderFactory 未禁用外部实体，存在 XXE 风险",
      "fix": "factory.setFeature(\"http://apache.org/xml/features/disallow-doctype-decl\", true);",
      "call_chain": ["Parser.parseXml()", "XmlHelper.load()", "Config.init()"],
      
      "deterministic": {
        "confidence": 1.0,
        "source": "semgrep"
      },
      
      "ai_enhancement": {
        "is_false_positive": false,
        "ai_confidence": 0.92,
        "analysis": "该代码处理外部 XML 输入，未禁用外部实体，攻击者可构造恶意 XML 读取服务器文件。建议立即修复。",
        "risk_level": "CRITICAL",
        "impact_scope": "影响所有调用 parseXml() 方法的地方",
        "enhanced_fix": "factory.setFeature(\"http://apache.org/xml/features/disallow-doctype-decl\", true);\nfactory.setFeature(\"http://xml.org/sax/features/external-general-entities\", false);",
        "references": ["https://owasp.org/Top10/A05_2021-Security_Misconfiguration/"]
      }
    }
  ]
}
```

---

## LLM 稳定性保障

### 问题：不同 LLM 结果不一致

**挑战**：
- GPT-4、Claude、本地模型能力差异大
- 同一个问题，不同 LLM 可能给出不同的分析说明
- 严重等级评估可能不一致

### 解决方案：确定性锚点 + 结构化约束 + 提示词增强

**核心思路**：
1. **确定性锚点**：Python 脚本扫描出的问题是**必须保留的**，AI 不能删除
2. **结构化输出**：强制 AI 输出结构化 JSON，而不是自由文本
3. **规则绑定**：每条规则有明确的 pattern 和 severity，AI 不能随意改变
4. **置信度阈值**：AI 评审结果需要达到置信度阈值才被采纳
5. **提示词增强**：通过 Few-shot 示例、角色设定、上下文锚定等提升 LLM 稳定性

### 提示词增强策略

详见 `references/prompts/ai-enhancer-prompt.md`：

1. **Few-shot 示例**（最有效）：提供 2-3 个具体的输入输出示例
2. **结构化约束**：明确定义输出 JSON schema
3. **角色设定 + 负面示例**：明确 LLM 的角色和职责，告诉它什么不能做
4. **上下文锚定**：明确引用确定性结果，强调哪些字段不能改变
5. **思维链**：让 LLM 先分析，再输出结论
6. **温度控制 + 输出验证**：降低 temperature（0.1-0.3），要求 LLM 自我验证

### 具体实现

#### 1. 确定性锚点

```python
# 确定性问题列表（Python 脚本输出）
deterministic_issues = [
    {
        "rule_id": "xxe-java-document-builder",
        "severity": "ERROR",  # 由规则定义，AI 不能改变
        "message": "DocumentBuilderFactory 未禁用外部实体",  # 由规则定义
        "confidence": 1.0,  # 确定性匹配
        "source": "semgrep"
    }
]

# AI 增强后的问题列表
enhanced_issues = [
    {
        "rule_id": "xxe-java-document-builder",  # 保持不变
        "severity": "ERROR",  # 保持不变
        "message": "DocumentBuilderFactory 未禁用外部实体",  # 保持不变
        
        # AI 只能增强，不能改变
        "ai_enhancement": {
            "is_false_positive": false,  # AI 可以标记误报
            "analysis": "...",  # AI 补充分析
            "enhanced_fix": "..."  # AI 生成修复建议
        }
    }
]
```

#### 2. 结构化输出约束

```python
# AI 必须输出以下结构化 JSON
AI_OUTPUT_SCHEMA = {
    "rule_id": str,  # 必须与确定性问题一致
    "severity": str,  # 必须与确定性问题一致
    "is_false_positive": bool,  # 是否误报
    "ai_confidence": float,  # AI 置信度（0-1）
    "analysis": str,  # 分析说明
    "risk_level": str,  # 风险等级（CRITICAL/HIGH/MEDIUM/LOW）
    "impact_scope": str,  # 影响范围
    "enhanced_fix": str,  # 修复建议
    "references": list  # 相关文档
}
```

#### 3. 置信度阈值

```python
# AI 评审结果需要达到置信度阈值才被采纳
CONFIDENCE_THRESHOLD = 0.7

def should_accept_ai_result(ai_result):
    if ai_result["ai_confidence"] < CONFIDENCE_THRESHOLD:
        return False  # 置信度太低，不采纳
    return True
```

#### 4. 回退机制

```python
# 如果 AI 结果不稳定，回退到纯 Python 结果
def merge_results(deterministic_issues, ai_enhanced_issues):
    merged = []
    
    for det_issue in deterministic_issues:
        # 查找对应的 AI 增强结果
        ai_result = find_ai_result(ai_enhanced_issues, det_issue["rule_id"])
        
        if ai_result and should_accept_ai_result(ai_result):
            # AI 结果可用，合并
            merged.append(merge_issue(det_issue, ai_result))
        else:
            # AI 结果不可用，使用确定性结果
            merged.append(det_issue)
    
    return merged
```

### 不同 LLM 的结果对比

| LLM | 确定性结果 | AI 增强结果 | 最终结果 |
|-----|-----------|------------|----------|
| **GPT-4** | ✅ 10 个问题 | ✅ 增强 10 个 | ✅ 10 个问题（增强） |
| **Claude** | ✅ 10 个问题 | ✅ 增强 10 个 | ✅ 10 个问题（增强） |
| **本地模型** | ✅ 10 个问题 | ⚠️ 增强 8 个（2 个置信度低） | ✅ 10 个问题（8 个增强 + 2 个原始） |

**关键**：无论使用哪个 LLM，**确定性问题列表（10 个）始终保持一致**，AI 增强只是锦上添花。

---

## 规约库结构

规约库位于 `references/` 目录，**全部使用 Markdown 格式**，人机都好维护：

```
references/
├── design/               # 设计规约
│   ├── architecture.md   # 架构合规（分层依赖、循环引用）
│   ├── api-design.md     # API 设计规范
│   └── database.md       # 数据库设计规范
├── implementation/       # 代码实现规约
│   ├── naming.md         # 命名规范
│   ├── error-handling.md # 异常处理
│   ├── concurrency.md    # 并发安全
│   └── null-safety.md    # 空指针防护
├── security/             # 安全规约
│   ├── authorization.md    # 越权访问
│   ├── xxe.md              # XML 外部实体注入
│   ├── xss.md              # 跨站脚本
│   ├── path-traversal.md   # 目录穿越
│   ├── privilege-escalation.md # 提权
│   ├── signature-bypass.md     # 签名绕过
│   ├── sql-injection.md        # SQL 注入
│   └── ssrf.md                 # SSRF
├── rules/                # 自定义业务规则
│   └── custom.md         # 用户自定义规则模板
├── profiles/             # 规约配置（YAML，控制启用哪些规约）
│   ├── default.yaml      # 默认规约集
│   ├── strict.yaml       # 严格模式
│   └── minimal.yaml      # 最小集
├── prompts/              # 提示词模板
│   └── ai-enhancer-prompt.md  # AI 增强评审提示词模板
└── test-cases/           # 测试案例（验证规则是否正确生效）
    ├── security/         # 安全规约测试案例
    ├── design/           # 设计规约测试案例
    └── implementation/   # 实现规约测试案例
```

### Markdown 规约格式

每个 Markdown 规约文件的格式约定：
- `# 标题` — 规则名称
- `> 引用` — 一句话描述
- ` ```yaml ` 代码块 — 规则元数据（id, languages, severity, cwe 等）
- `## 违规示例` / `## 正确示例` — 代码示例（人读）
- ` ```pattern ` 代码块 — 检测模式（机器解析）
- ` ```pattern-not ` 代码块 — 排除模式（机器解析）

**示例**：

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

## 规约预编译流程（推荐）

为了降低规约编写门槛并提高规则质量，推荐使用**规约预编译器**将自然语言规约转换为 Semgrep 规则，并通过安全审核机制确保规则质量。

### ⚠️ AI 行为要求（必须遵守）

**在执行预编译流程时，AI 必须遵循以下原则：**

1. **禁止自动部署**：AI 不得直接执行 `--approve` 命令部署规则，必须等待用户明确确认
2. **展示差异报告**：编译后必须向用户展示新旧规则差异，包括：
   - 检测模式的变化
   - 可能新增的误报或漏报
   - 建议的测试用例
3. **等待用户确认**：在展示差异报告后，必须明确询问用户是否确认部署，例如：
   ```
   以上是规则变更的差异报告，请确认是否部署此规则？
   - 确认部署
   - 取消部署
   - 查看完整规则文件
   ```
4. **记录确认过程**：用户确认后，AI 应记录确认时间和确认内容，便于后续审计

**为什么必须这样做？**
- 避免 AI 幻觉导致规则错乱
- 确保人工对规则变更有最终控制权
- 符合安全审核机制的设计初衷

### 预编译流程概览

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

### 自然语言规约格式

人只需要写自然语言描述，不需要会写 Semgrep 语法：

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

### 预编译命令

```bash
# 编译所有自然语言规约
python3 scripts/rule_compiler.py --specs-dir references/security/

# 强制重新编译（忽略缓存）
python3 scripts/rule_compiler.py --specs-dir references/security/ --force

# 对比新旧规则差异
python3 scripts/rule_compiler.py --diff references/security/compiled/xxe.yaml

# 回归测试验证规则效果
python3 scripts/rule_compiler.py --diff references/security/compiled/xxe.yaml --test references/test-cases/security/

# 人工确认后部署规则
python3 scripts/rule_compiler.py --approve references/security/compiled/xxe.yaml
```

### 安全审核机制

预编译器内置了安全审核机制，避免 AI 幻觉导致规则错乱：

1. **AI 对比解读**：生成新旧规则的语义差异报告，说明检测范围变化、可能新增的误报或漏报
2. **回归测试**：用测试用例验证新规则的检出率和误报率
3. **人工确认**：检查人审核差异报告和测试结果后，确认是否部署
4. **版本管理**：保留历史版本，支持回滚

### 预编译输出

预编译后的规则保存在 `references/security/compiled/` 目录：

```
references/security/compiled/
├── xxe.yaml              # 编译后的 Semgrep 规则
├── xxe.approved.yaml     # 已批准的规则（人工确认后生成）
├── .history/             # 版本历史
│   ├── xxe_20260819_103000.yaml
│   └── xxe_20260819_110000.yaml
└── .approval_log.json    # 审批记录
```

### 使用预编译规则

扫描时可以使用预编译后的规则：

```bash
# 使用预编译规则扫描
python3 scripts/rule_engine.py \
  --repo <repo-path> \
  --diff-result diff_result.json \
  --specs-dir references/security/compiled/ \
  --profile default \
  --output deterministic_issues.json
```

---

## 自定义规约

用户可在 `references/rules/custom.md` 中添加自定义规则。格式就是普通 Markdown，用 `---` 分隔不同规则：

```markdown
# 我的规则 - 简要描述

> 一句话说明

```yaml
id: custom-my-rule
languages: [java]
severity: WARNING
category: custom
```

## 检测模式

```pattern
your_pattern_here
```
```

---

## 定期扫描

### 配置 Cron 定时扫描

编辑 `config.yaml`：

```yaml
schedule:
  cron: "0 2 * * *"  # 每天凌晨 2 点
  notify: true
  notify_method: "webhook"
  notify_target: "https://hooks.example.com/scan-result"
```

### CI/CD 集成

**GitHub Actions**：
```yaml
name: Code Review
on:
  push:
    branches: [release/*]
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: python scripts/scan.py --repo . --base master --target HEAD --output report/
      - uses: actions/upload-artifact@v4
        with:
          name: review-report
          path: report/
```

**Jenkins Pipeline**：
```groovy
stage('Code Review') {
    steps {
        sh 'python scripts/scan.py --repo . --base master --target ${BRANCH_NAME} --profile default --output report/'
    }
    post {
        always {
            archiveArtifacts 'report/**'
        }
    }
}
```

---

## 扩展指南

- **新增安全规则**：在 `references/security/` 下添加 Markdown 文件
- **新增设计规约**：在 `references/design/` 下添加 Markdown 文件
- **新增测试案例**：在 `references/test-cases/` 对应子目录下添加测试
- **自定义提示词模板**：在 `references/prompts/` 下添加提示词模板
- **接入新语言**：在 `scripts/call_graph.py` 中添加对应语言的 Tree-sitter 解析器
- **自定义报告格式**：扩展 `scripts/report_generator.py`

---

## 测试验证

运行规则测试，验证规约是否正确生效：

```bash
python scripts/test_rules.py
```

测试案例位于 `references/test-cases/`，每个规约对应一个测试文件，包含违规代码样本和正确代码样本。

---

## 常见问题

### Q1: 不同 LLM 结果不一致怎么办？

**A**: 
- **确定性锚点**：Python 脚本扫描出的问题是**必须保留的**，AI 不能删除
- **结构化约束**：强制 AI 输出结构化 JSON，而不是自由文本
- **置信度阈值**：AI 评审结果需要达到置信度阈值（0.7）才被采纳
- **提示词增强**：通过 Few-shot 示例、角色设定、上下文锚定等提升 LLM 稳定性
- **回退机制**：如果 AI 结果不稳定，回退到纯 Python 结果

**关键**：无论使用哪个 LLM，**确定性问题列表始终保持一致**，AI 增强只是锦上添花。

### Q2: 如何选择扫描策略？

**A**: 
- **python-only**：快速扫描、离线环境，仅 Python 脚本
- **ai-enhanced**：日常评审（推荐），Python + AI 增强
- **hybrid**：严格审查、安全审计，Semgrep + AI（最精准）

### Q3: AI 增强是否必须启用？

**A**: 
- **不是必须的**。AI 增强是可选功能，用于补充分析说明和生成修复建议
- 如果没有配置 LLM，会自动跳过 AI 增强，使用纯 Python 结果
- **建议**：日常评审启用 AI 增强（补充分析 + 修复建议）

### Q4: 如何优化大仓库的扫描性能？

**A**: 
1. **增量扫描**：只扫描变更文件（提升 10x-100x）
2. **分批处理**：大仓库分批评审，避免超出上下文限制
3. **文件过滤**：跳过测试文件和生成文件
4. **并行处理**：多个文件并行分析（如果 Agent 支持）

### Q5: 如何添加自定义规则？

**A**: 
1. 编辑 `references/rules/custom.md`
2. 按照 Markdown 规约格式添加规则
3. 运行 `python scripts/test_rules.py` 验证规则是否正确生效

### Q6: 如何自定义提示词模板？

**A**: 
1. 在 `references/prompts/` 下创建新的提示词模板文件
2. 参考 `references/prompts/ai-enhancer-prompt.md` 的格式
3. 在 `config.yaml` 中指定使用的提示词模板：
   ```yaml
   ai_review:
     prompt_template: "references/prompts/my-custom-prompt.md"
   ```

### Q7: 策略确认点是什么？

**A**: 
- **策略确认点**是 Step 1.5，在执行扫描前与用户确认策略
- 展示完整的执行策略（扫描策略 + 提示词增强 + 预期输出）
- 用户可以选择：确认执行、调整策略、取消执行
- 确保执行策略符合用户预期，避免不必要的执行

---

## 核心优势

1. **确定性锚点**：Python 脚本确保结果稳定，不依赖 LLM
2. **AI 增强**：AI 只负责增强和过滤，不能改变确定性结果
3. **LLM 无关**：通过结构化输出、规则绑定和提示词增强，确保不同 LLM 结果一致
4. **离线优先**：所有核心功能离线可用，最小化外部依赖
5. **用户确认**：执行前与用户确认策略，确保符合预期
6. **灵活扩展**：Markdown 规约格式，人机都好维护，易于扩展
7. **外部规则加载**：支持从高分开源规约库加载经过验证的规则，无需从零编写

---

## 外部规则加载（推荐）

为了降低规约编写门槛并提高规则质量，推荐从高分开源规约库加载经过验证的规则，而不是让人从零编写。

### ⚠️ AI 行为要求（必须遵守）

**在引导用户使用外部规则时，AI 必须遵循以下原则：**

1. **优先推荐外部规则**：当用户需要新增规则时，首先询问是否需要从外部规则库加载，而不是直接让人编写
2. **展示推荐规则库**：向用户展示推荐的高分开源规约库，说明每个库的覆盖范围和适用场景
3. **解释加载流程**：说明外部规则加载后会自动进入 `references/external/` 目录，与内部规则隔离管理
4. **提示规则管理**：告知用户可以查看已加载规则、移除不需要的规则、从自定义 GitHub 仓库加载

**为什么这样做？**
- 外部规则经过社区验证，质量有保障
- 降低用户编写门槛，无需学习 Semgrep 语法
- 覆盖更多场景（C/C++ 内存安全、移动安全、DOM XSS 等）
- 保持内部规则的简洁性

### 推荐的开源规约库

| 规则库 | Stars | 语言覆盖 | 适用场景 |
|---|---|---|---|
| **Semgrep 官方规则** | 15.8k | 30+ 语言 | OWASP Top 10 全集，20000+ 规则 |
| **0xdea/semgrep-rules** | ~500 | C/C++ | 缓冲区溢出、use-after-free、整数溢出等 |
| **mindedsecurity/android-security** | 335 | Java/Kotlin | Android 移动安全，基于 OWASP MASTG |
| **dipa96/semgrep-rules** | ~30 | JavaScript | DOM XSS 深度检测 |

### 使用外部规则加载器

#### 1. 列出推荐的规则库

```bash
python3 scripts/rule_loader.py --list
```

输出示例：
```json
{
  "status": "success",
  "recommended_repos": {
    "semgrep-official": {
      "url": "https://github.com/semgrep/semgrep-rules",
      "stars": "15.8k",
      "description": "Semgrep 官方规则库，覆盖 OWASP Top 10，20000+ 规则",
      "languages": ["java", "python", "javascript", "typescript", "go", "c", "cpp"],
      "categories": ["security", "best-practices", "performance"]
    },
    "0xdea-c-cpp": {
      "url": "https://github.com/0xdea/semgrep-rules",
      "stars": "~500",
      "description": "C/C++ 内存安全规则：缓冲区溢出、use-after-free、整数溢出等",
      "languages": ["c", "cpp"],
      "categories": ["security", "memory-safety"]
    }
  }
}
```

#### 2. 从推荐规则库加载

```bash
# 从 Semgrep 官方规则库加载
python3 scripts/rule_loader.py --from recommended --repo-key semgrep-official

# 从 0xdea C/C++ 规则库加载
python3 scripts/rule_loader.py --from recommended --repo-key 0xdea-c-cpp

# 只加载安全类规则
python3 scripts/rule_loader.py --from recommended --repo-key semgrep-official --categories security
```

#### 3. 从自定义 GitHub 仓库加载

```bash
# 从任意 GitHub 仓库加载
python3 scripts/rule_loader.py --from github --repo https://github.com/user/semgrep-rules

# 指定规则在仓库中的子目录
python3 scripts/rule_loader.py --from github --repo https://github.com/user/rules --subdir rules/security
```

#### 4. 查看已加载规则

```bash
python3 scripts/rule_loader.py --status
```

输出示例：
```json
{
  "status": "success",
  "external_dir": "/path/to/references/external",
  "total_loaded": 150,
  "sources": {
    "semgrep-official": {
      "url": "https://github.com/semgrep/semgrep-rules",
      "loaded_at": "2026-08-20T10:30:00",
      "rule_count": 120
    }
  },
  "rules": [
    {
      "rule_id": "java-spring-csrf-disabled",
      "source": "semgrep-official",
      "loaded_at": "2026-08-20T10:30:00",
      "file": "/path/to/references/external/semgrep-official_java-spring-csrf-disabled.yaml"
    }
  ]
}
```

#### 5. 移除外部规则

```bash
# 移除指定规则
python3 scripts/rule_loader.py --remove java-spring-csrf-disabled
```

### 外部规则目录结构

加载的外部规则保存在 `references/external/` 目录：

```
references/external/
├── semgrep-official_java-spring-csrf-disabled.yaml
├── semgrep-official_python-sql-injection.yaml
├── 0xdea-c-cpp_buffer-overflow-gets.yaml
├── .loaded_rules.json          # 已加载规则元数据
└── .temp/                       # 临时目录（克隆后自动清理）
```

### 使用外部规则扫描

扫描时自动包含外部规则：

```bash
# 扫描时自动加载 references/external/ 下的所有规则
python3 scripts/rule_engine.py \
  --repo <repo-path> \
  --diff-result diff_result.json \
  --specs-dir references/ \
  --profile default \
  --output deterministic_issues.json
```

`rule_engine.py` 会自动扫描 `references/` 下的所有子目录，包括 `external/`。

### 外部规则 vs 内部规则

| 维度 | 内部规则（security/design/implementation） | 外部规则（external） |
|---|---|---|
| **来源** | 团队自己编写 | 从开源仓库加载 |
| **格式** | Markdown（自然语言 + pattern） | Semgrep YAML |
| **维护** | 团队自主维护 | 可从源仓库更新 |
| **适用场景** | 团队特定规范、业务规则 | 通用安全规则、行业标准 |
| **管理命令** | 直接编辑 MD 文件 | `rule_loader.py` |

### 最佳实践

1. **优先使用外部规则**：通用安全规则（XXE、XSS、SQL 注入等）直接从 Semgrep 官方库加载
2. **内部规则专注业务**：团队特定的设计规范、业务逻辑规则用 Markdown 编写
3. **定期更新外部规则**：定期从源仓库重新加载，获取最新规则
4. **按需加载**：不要一次性加载所有规则，根据项目语言和需求选择性加载
5. **移除不需要的规则**：使用 `--remove` 移除不适用的规则，减少误报

### 常见问题

**Q: 外部规则和内部规则冲突怎么办？**
A: 外部规则和内部规则独立管理，不会冲突。如果检测到相同问题，会分别报告。

**Q: 如何更新外部规则？**
A: 重新执行加载命令即可，新规则会覆盖旧规则。

**Q: 外部规则太多会影响性能吗？**
A: 建议按需加载，不要一次性加载所有规则。可以使用 `--categories` 过滤只加载需要的类别。

**Q: 可以从私有 GitHub 仓库加载吗？**
A: 可以，使用 `--from github --repo <private-url>`，需要确保有访问权限。
