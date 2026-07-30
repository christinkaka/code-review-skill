# Semgrep 离线安装指南

## 什么是 Semgrep

Semgrep 是一个开源的静态代码分析工具，基于 AST（抽象语法树）进行模式匹配，比正则引擎更精准。

**核心优势**：
- ✅ 支持 30+ 种语言
- ✅ 基于 AST 的模式匹配（比正则更精准）
- ✅ 支持跨行匹配
- ✅ 自定义 YAML 规则
- ✅ 误报率低（5-10%）

---

## 离线包说明

本项目的 `semgrep-offline-packages/` 目录包含预下载的 Semgrep wheels:

| Wheel 类型 | 数量 | 平台 |
|---|---|---|
| `semgrep-*` 主程序 | 1 | **Windows AMD64** (`win_amd64`, cp310-cp314) |
| 编译依赖 (cffi, cryptography, pydantic_core 等) | ~10 | **Windows AMD64** (`cp311-*_win_amd64`) |
| Pure Python 依赖 | ~56 | **跨平台** (`py3-none-any`) |

> ⚠️ **当前离线包仅适用于 Windows AMD64 平台**（Python 3.11）。  
> 若需在 macOS/Linux 使用，请在目标平台重新执行 `pip download semgrep -d semgrep-offline-packages` 替换现有 wheels。

---

## 安装方法

### Windows（推荐）

```powershell
# 在项目根目录执行
.\install-semgrep-offline.ps1
```

### macOS / Linux (bash)

```bash
# 在项目根目录执行
chmod +x install-semgrep-offline.sh
./install-semgrep-offline.sh
```

脚本会自动检测平台并过滤合适的 wheels 进行安装。

---

## 在线安装（推荐环境）

```bash
# macOS
brew install semgrep

# Windows / Linux / macOS 通用
pip3 install semgrep

# 验证安装
semgrep --version
```

---

## 与代码评审工具集成

在 `config.yaml` 中启用 Semgrep：

```yaml
review:
  mode: "hybrid"   # 推荐: Agent + Semgrep 双重评审

semgrep:
  enabled: true
  binary: ""        # 留空则使用 PATH 中的 semgrep
  timeout: 300
  max_memory: 4096
```

## 验证安装

```bash
# 检查版本
semgrep --version

# 运行测试扫描 (自动选择语言)
semgrep --config auto /path/to/code

# 使用自定义规则
semgrep --config references/security/xxe.md /path/to/code

# 使用整个规则目录
semgrep --config references/security/ --config references/implementation/ /path/to/code
```

## 完整扫描示例

```bash
# 扫描 flyway 仓库, 使用 default profile
python scripts/scan.py \
  --repo D:\dev\Git\flyway \
  --base flyway-8.5.5 --target HEAD \
  --profile default \
  --output report/ \
  --language java
```

---

## 重新生成离线包

如需为新平台重新下载 wheels:

```bash
# 删除旧包
rm -rf semgrep-offline-packages/
mkdir semgrep-offline-packages

# 下载当前平台对应的 wheels (Windows AMD64 + Pure Python)
pip download semgrep --python-version 3.11 --only-binary :all: -d semgrep-offline-packages

# 或用 Docker (获取多平台 wheels)
docker run -v "${PWD}/semgrep-offline-packages:/out" \
  python:3.11-slim \
  pip download semgrep --platform linux_x86_64 --platform win_amd64 --only-binary :all: -d /out
```

---

## 常见问题

### Q1: 离线装好后 `semgrep` 命令找不到?

在 Windows 上有时 PATH 未刷新：
```powershell
semgrep --version        # 不行则用
python -m semgrep --version  # 备选方案
```

### Q2: 扫描速度慢?

```bash
# 启用多核扫描
semgrep --jobs 8 --config auto .

# 排除不必要目录
semgrep --exclude-dir node_modules --exclude-dir .git --config auto .

# 只扫描特定语言
semgrep --include "*.java" --config auto .
```

### Q3: Windows AMD64 wheels 与 Python 版本不匹配?

当前 wheels 针对 Python 3.11 (cp311)。如需其他 Python 版本，重新生成离线包：
```bash
pip download semgrep --python-version 3.12 --only-binary :all: -d semgrep-offline-packages/
```

### Q4: 误报率高怎么办?

- 切换到 `hybrid` 模式, Agent + Semgrep 双重过滤
- 使用更精准的自定义规则替换 Semgrep 默认规则
- 检查 `references/rules/` 下的规则是否需要调优
