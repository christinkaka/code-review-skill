# 代码评审工具 - 技术栈分析

## 一、核心技术栈

### 1.1 代码扫描技术层次

```
┌─────────────────────────────────────────────────────────┐
│  Level 3: Agent 评审（核心）                              │
│  - Agent 自身就是 LLM，直接执行评审                       │
│  - 上下文理解，过滤误报                                   │
│  - 生成修复建议和分析说明                                 │
│  - 无需外部 API，离线可用                                 │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  Level 2: Semgrep 规则引擎（可选增强）                    │
│  - 跨行模式匹配                                          │
│  - 数据流分析（source → sink）                            │
│  - 多文件关联分析                                         │
│  - 需要安装 Semgrep（可选）                               │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  Level 1: Tree-sitter AST 解析（精确语法分析）            │
│  - 方法定义提取（比正则更准确）                            │
│  - 调用图构建（方法间调用关系）                            │
│  - 多语言支持（Java/Python/JavaScript）                   │
│  - 离线可用（已集成）                                     │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  Level 0: Git 差异分析（变更检测）                        │
│  - 分支对比（release vs master）                          │
│  - 变更文件提取                                           │
│  - 变更方法定位                                           │
│  - 离线可用（已集成）                                     │
└─────────────────────────────────────────────────────────┘
```

### 1.2 技术选型对比

| 技术 | 精准度 | 性能 | 适用场景 | 外部依赖 | 当前状态 |
|------|--------|------|----------|----------|----------|
| **Agent 评审** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 核心评审，上下文理解 | 无 | ✅ 已集成 |
| **Semgrep** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 跨行模式、数据流分析 | 需安装 | ⚠️ 可选 |
| **Tree-sitter** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | AST 解析、调用图 | 无 | ✅ 已集成 |
| **GitPython** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 分支差异、变更检测 | 无 | ✅ 已集成 |

### 1.3 外部依赖分析

| 依赖 | 是否必须 | 用途 | 离线可用 |
|------|----------|------|----------|
| **Python 3.8+** | ✅ 必须 | 运行环境 | ✅ |
| **pyyaml** | ✅ 必须 | YAML 解析 | ✅ |
| **gitpython** | ✅ 必须 | Git 操作 | ✅ |
| **tree-sitter** | ✅ 必须 | AST 解析 | ✅ |
| **rich** | ✅ 必须 | 终端输出 | ✅ |
| **Semgrep** | ❌ 可选 | 精准模式匹配 | ✅（如果已安装） |
| **外部 LLM API** | ❌ 不需要 | Agent 自身就是 LLM | - |

**核心优势**：所有核心功能离线可用，无需外部 API 调用。

---

## 二、Agent 评审机制（核心）

### 2.1 Agent 评审流程

```
Agent 评审流程：
│
├─ [1] Agent 读取规约
│   ├─ 读取 specs.json（从 Markdown 规约解析）
│   ├─ 理解每条规则的检测模式
│   ├─ 理解问题描述和严重等级
│   └─ 理解修复建议
│
├─ [2] Agent 分析变更代码
│   ├─ 读取 diff_result.json
│   ├─ 理解哪些文件被修改
│   ├─ 理解哪些方法被变更
│   └─ 理解新增和删除的代码行
│
├─ [3] Agent 执行评审
│   ├─ 对于每个变更方法
│   ├─ 对于每条规约规则
│   ├─ Agent 分析代码是否匹配模式
│   ├─ Agent 判断是否为真正的问题
│   └─ Agent 生成修复建议
│
├─ [4] Agent 过滤误报
│   ├─ 基于上下文理解
│   ├─ 排除测试代码的"违规"
│   ├─ 排除已修复的代码
│   └─ 排除特殊场景的合理使用
│
└─ [5] Agent 生成分析说明
    ├─ 问题原因分析
    ├─ 风险等级评估
    ├─ 修复建议（具体代码）
    └─ 相关文档链接（如果有）
```

### 2.2 Agent 评审的优势

| 优势 | 说明 |
|------|------|
| **上下文理解** | Agent 能理解代码上下文，不仅匹配模式，还理解语义 |
| **误报过滤** | Agent 能识别测试代码、已修复代码、特殊场景，过滤误报 |
| **灵活判断** | Agent 能根据具体情况调整严重等级和修复建议 |
| **无需外部 API** | Agent 自身就是 LLM，无需调用外部服务，离线可用 |
| **生成分析说明** | Agent 能生成详细的问题分析和修复建议 |

### 2.3 Agent 评审 vs Semgrep 评审

| 特性 | Agent 评审 | Semgrep 评审 |
|------|-----------|--------------|
| **外部依赖** | 无 | 需要安装 Semgrep |
| **离线可用** | ✅ | ✅（如果已安装） |
| **上下文理解** | ✅ 强 | ❌ 弱（仅模式匹配） |
| **误报过滤** | ✅ 强 | ❌ 弱 |
| **跨行匹配** | ✅ | ✅ |
| **数据流分析** | ❌ | ✅ |
| **生成分析说明** | ✅ | ❌ |
| **性能** | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **适用场景** | 默认推荐 | 精准度要求极高时 |

**建议**：默认使用 Agent 评审（无需外部依赖），如果安装了 Semgrep 可以结合使用（Agent + Semgrep 双重评审）。

---

## 三、精准度优化策略

### 3.1 多层检测机制

```python
# 伪代码示例：多层检测流程
def scan_code(repo_path, changed_files):
    # Level 0: Git 差异分析（精准定位变更）
    diff_result = git_diff_analyzer.analyze(base, target)
    
    # Level 1: Tree-sitter AST 解析（精确提取方法）
    methods = tree_sitter_parser.extract_methods(diff_result.changed_files)
    
    # Level 2: Semgrep 规则引擎（可选，跨行模式匹配）
    if semgrep_available() and config.review.mode in ["semgrep", "hybrid"]:
        semgrep_issues = semgrep_engine.run(rules, changed_files)
    else:
        semgrep_issues = []
    
    # Level 3: Agent 评审（核心，上下文理解）
    agent_issues = agent_reviewer.review(
        rules=rules,
        diff_result=diff_result,
        methods=methods,
        semgrep_issues=semgrep_issues  # 如果有 Semgrep 结果，作为参考
    )
    
    return agent_issues
```

### 3.2 精准度提升技巧

#### 技巧 1: Agent 上下文理解
```
Agent 能理解代码上下文，例如：

# 这段代码虽然匹配 XXE 模式，但 Agent 能识别出已有防护措施
DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
// Agent 识别出：虽然未显式禁用外部实体，但后续代码使用了安全的解析方式
Document doc = safeParse(inputStream);  // safeParse 内部已禁用外部实体
```

#### 技巧 2: Agent 误报过滤
```
Agent 能过滤以下误报：
- 测试代码中的"违规"（测试代码允许某些模式）
- 已修复的代码（虽然匹配模式，但已有防护措施）
- 特殊场景的合理使用（如某些 API 在特定上下文中是安全的）
```

#### 技巧 3: Semgrep 跨行模式（如果可用）
```yaml
# 精准：跨行模式匹配
rules:
  - id: xxe-vulnerable
    pattern: |
      DocumentBuilderFactory $factory = DocumentBuilderFactory.newInstance();
      ...
      $factory.parse(...);
    message: "XXE 漏洞：未禁用外部实体"
```

#### 技巧 4: Tree-sitter 精确提取方法
```python
# 精准：使用 Tree-sitter 提取方法定义（比正则更准确）
import tree_sitter

parser = tree_sitter.Parser()
parser.set_language(tree_sitter_java.language())
tree = parser.parse(source_code)

# 精确提取所有方法定义
methods = extract_methods_from_ast(tree.root_node)
```

---

## 四、性能优化策略

### 4.1 分层性能优化

| 层级 | 优化策略 | 预期提升 |
|------|----------|----------|
| **Level 0: Git** | 只扫描变更文件（非全量扫描） | 10x-100x |
| **Level 1: Tree-sitter** | 缓存 AST 解析结果 | 2x-5x |
| **Level 2: Semgrep** | 并行扫描多个文件 | 3x-10x |
| **Level 3: Agent** | 分批处理，避免超出上下文限制 | 2x-5x |

### 4.2 性能优化技巧

#### 技巧 1: 增量扫描
```python
# 只扫描上次以来的变更
def incremental_scan(repo_path, last_scan_time):
    changed_files = git_diff_analyzer.get_changes_since(last_scan_time)
    if not changed_files:
        return []  # 无变更，跳过扫描
    return scan_files(changed_files)
```

#### 技巧 2: 文件过滤
```python
# 跳过测试文件和生成文件
EXCLUDE_PATTERNS = [
    "**/test/**",
    "**/tests/**",
    "**/generated/**",
    "**/node_modules/**",
    "**/target/**",
    "**/build/**"
]

def filter_files(files):
    return [f for f in files if not matches_any_pattern(f, EXCLUDE_PATTERNS)]
```

#### 技巧 3: 分批处理
```python
# 大仓库分批评审，避免超出上下文限制
def batch_review(files, batch_size=50):
    all_issues = []
    for i in range(0, len(files), batch_size):
        batch = files[i:i+batch_size]
        issues = agent_reviewer.review(batch)
        all_issues.extend(issues)
    return all_issues
```

---

## 五、作为 AI Skill 的最佳实践

### 5.1 默认配置（推荐）

```yaml
# config.yaml - 默认配置（Agent 主导）
review:
  mode: "agent"  # Agent 直接评审，无需外部依赖
  
  agent:
    context_aware: true      # 启用上下文理解
    generate_fix: true       # 生成修复建议
    generate_analysis: true  # 生成分析说明

semgrep:
  enabled: false  # 不启用 Semgrep（可选增强）
```

### 5.2 精准度优先配置

```yaml
# config.yaml - 精准度优先（如果安装了 Semgrep）
review:
  mode: "hybrid"  # Agent + Semgrep 双重评审
  
  agent:
    context_aware: true
    generate_fix: true
    generate_analysis: true

semgrep:
  enabled: true  # 启用 Semgrep
```

### 5.3 性能优先配置

```yaml
# config.yaml - 性能优先
review:
  mode: "agent"
  
  agent:
    context_aware: false     # 禁用上下文理解（更快）
    generate_fix: true
    generate_analysis: false # 禁用分析说明（更快）

performance:
  incremental: true          # 增量扫描
  parallel_files: 8          # 并行处理
  batch_size: 100            # 大批次
  skip_tests: true           # 跳过测试文件
```

---

## 六、技术栈依赖关系

```
代码评审工具
├── 核心依赖（必需，全部离线可用）
│   ├── pyyaml          # YAML 解析
│   ├── gitpython       # Git 操作
│   ├── tree-sitter     # AST 解析
│   │   ├── tree-sitter-java
│   │   ├── tree-sitter-python
│   │   └── tree-sitter-javascript
│   └── rich            # 终端输出
│
├── 可选增强（不是必须的）
│   └── semgrep         # 跨行模式匹配（需要安装）
│
├── Agent 评审（核心，无外部依赖）
│   └── Agent 自身就是 LLM
│       ├── 读取规约
│       ├── 分析代码
│       ├── 执行评审
│       ├── 过滤误报
│       └── 生成建议
│
└── 报告生成（离线可用）
    ├── jinja2          # 模板引擎
    └── pandas          # 数据分析
```

---

## 七、总结与建议

### 7.1 技术栈优势

1. **Agent 主导**：Agent 自身就是 LLM，直接执行评审，无需外部 API
2. **离线优先**：所有核心功能离线可用，最小化外部依赖
3. **上下文理解**：Agent 能理解代码上下文，过滤误报，生成精准修复建议
4. **灵活扩展**：Markdown 规约格式，人机都好维护，易于扩展

### 7.2 使用建议

**作为 AI Skill 使用时**：
1. **默认使用 Agent 评审**：无需外部依赖，离线可用
2. **大仓库启用增量扫描**：只扫描变更文件
3. **分批处理**：大仓库分批评审，避免超出上下文限制
4. **定期更新规约库**：保持规则的时效性

### 7.3 未来优化方向

1. **缓存优化**：缓存 AST 解析结果和 Agent 评审结果
2. **分布式评审**：支持多 Agent 并行评审大仓库
3. **自定义规则学习**：从历史问题中学习新的检测规则
4. **实时评审**：Git Hook 集成，提交时实时评审
