# 离线安装说明

## 离线包清单

已下载 20 个依赖包到 `offline-packages/` 目录，总计约 19MB：

### 核心依赖（9 个）
- `pyyaml-6.0.3` - YAML 解析（规约文件）
- `gitpython-3.1.57` - Git 操作（分支差异分析）
- `gitdb-4.0.12` - Git 数据库
- `smmap-5.0.3` - Git 内存映射
- `rich-15.0.0` - 终端美化输出
- `pygments-2.20.0` - 语法高亮
- `jinja2-3.1.6` - 模板引擎（报告生成）
- `markupsafe-3.0.3` - Jinja2 依赖
- `markdown_it_py-4.2.0` - Markdown 解析

### 多语言解析（4 个）
- `tree-sitter-0.26.0` - 多语言 AST 解析器
- `tree-sitter-java-0.23.5` - Java 语法树
- `tree-sitter-python-0.25.0` - Python 语法树
- `tree-sitter-javascript-0.25.0` - JavaScript 语法树

### 数据处理（7 个）
- `pandas-2.3.3` - 数据分析
- `numpy-2.2.6` - 数值计算
- `python_dateutil-2.9.0` - 日期处理
- `pytz-2026.3` - 时区处理
- `tzdata-2026.3` - 时区数据
- `six-1.17.0` - Python 2/3 兼容
- `mdurl-0.1.2` - URL 处理

## 离线安装命令

```bash
# 进入项目目录
cd /Users/chris/Documents/代码评审工具集/code-review-skill

# 从离线包安装（无需网络）
pip3 install --no-index --find-links=offline-packages -r requirements.txt

# 或者安装单个包
pip3 install --no-index --find-links=offline-packages pyyaml gitpython rich
```

## 可选依赖

### Semgrep（规则引擎）
```bash
# macOS
brew install semgrep

# 或从 PyPI 安装
pip3 install semgrep
```

### AI API（可选）
如果使用 AI 增强评审，需要配置 LLM API：
```bash
export OPENAI_API_KEY="your-api-key"
```

## 验证安装

```bash
# 验证核心依赖
python3 -c "import yaml, git, rich; print('核心依赖 OK')"

# 验证 Tree-sitter
python3 -c "import tree_sitter; print('Tree-sitter OK')"

# 运行测试
python3 -m pytest tests/ -v
```

## 依赖用途说明

| 依赖 | 用途 | 精准度影响 | 性能影响 |
|------|------|-----------|---------|
| **pyyaml** | 解析 Markdown 规约中的 YAML 元数据 | 中 | 低 |
| **gitpython** | Git 分支差异分析、变更文件提取 | 高 | 中 |
| **tree-sitter** | 多语言 AST 解析，精确提取方法定义 | 高 | 中 |
| **rich** | 终端彩色输出、进度条 | 无 | 低 |
| **jinja2** | Markdown/HTML 报告模板渲染 | 无 | 低 |
| **pandas** | 问题统计、报告数据分析 | 无 | 中 |
| **semgrep** | 跨行模式匹配、数据流分析（可选） | 高 | 高 |

## 性能优化建议

### 1. 精准度优先
- 使用 **Semgrep** 进行跨行模式匹配（比正则更精准）
- 使用 **Tree-sitter** 进行精确的 AST 解析（比正则提取方法更准确）
- 启用 **AI 评审** 过滤误报（置信度阈值 0.7）

### 2. 性能优先
- 使用 **内置正则引擎**（Semgrep 不可用时）
- 限制扫描文件数量（`--max-files 100`）
- 使用 **增量扫描**（只扫描上次以来的变更）
- 禁用 AI 评审（`ai_review.enabled: false`）

### 3. 平衡模式（推荐）
- 优先使用 Semgrep（精准度高）
- 对大文件使用正则后备（性能好）
- AI 评审只处理 ERROR 级别问题（减少 API 调用）
