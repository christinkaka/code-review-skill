#!/bin/bash
# 智能安装离线依赖包（自动选择匹配当前平台的包）

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OFFLINE_DIR="$SCRIPT_DIR/offline-packages"

echo "=========================================="
echo "代码评审工具 - 离线依赖安装"
echo "=========================================="
echo "离线包目录: $OFFLINE_DIR"
echo ""

# 检测当前平台
OS=$(uname -s)
ARCH=$(uname -m)

case "$OS" in
    Darwin)
        if [ "$ARCH" = "arm64" ]; then
            PLATFORM="macosx_11_0_arm64"
            echo "检测到平台: macOS ARM64 (Apple Silicon)"
        else
            PLATFORM="macosx_10_9_x86_64"
            echo "检测到平台: macOS x86_64 (Intel)"
        fi
        ;;
    Linux)
        PLATFORM="manylinux"
        echo "检测到平台: Linux x86_64"
        ;;
    MINGW*|MSYS*|CYGWIN*)
        PLATFORM="win_amd64"
        echo "检测到平台: Windows amd64"
        ;;
    *)
        echo "❌ 不支持的平台: $OS $ARCH"
        exit 1
        ;;
esac

echo ""
echo ">>> 安装纯 Python 通用包"
pip3 install --no-index --find-links="$OFFLINE_DIR" \
    gitdb gitpython jinja2 markdown-it-py mdurl pygments python-dateutil \
    pytz rich six smmap tzdata 2>&1 | grep -E "(Successfully|already satisfied)" | head -20

echo ""
echo ">>> 安装平台特定包 ($PLATFORM)"

# 根据平台选择对应的包
if [ "$PLATFORM" = "macosx_11_0_arm64" ]; then
    pip3 install --no-index --find-links="$OFFLINE_DIR" \
        "markupsafe-3.0.3-cp310-cp310-macosx_11_0_arm64.whl" \
        "numpy-2.2.6-cp310-cp310-macosx_14_0_arm64.whl" \
        "pandas-2.3.3-cp310-cp310-macosx_11_0_arm64.whl" \
        "pyyaml-6.0.3-cp310-cp310-macosx_11_0_arm64.whl" \
        "tree_sitter-0.26.0-cp310-cp310-macosx_11_0_arm64.whl" \
        "tree_sitter_java-0.23.5-cp39-abi3-macosx_11_0_arm64.whl" \
        "tree_sitter_python-0.25.0-cp310-abi3-macosx_11_0_arm64.whl" \
        "tree_sitter_javascript-0.25.0-cp310-abi3-macosx_11_0_arm64.whl" \
        2>&1 | grep -E "(Successfully|already satisfied)" | head -20
elif [ "$PLATFORM" = "macosx_10_9_x86_64" ]; then
    pip3 install --no-index --find-links="$OFFLINE_DIR" \
        "PyYAML-6.0.2-cp310-cp310-macosx_10_9_x86_64.whl" \
        "markupsafe-3.0.3-cp310-cp310-macosx_10_9_x86_64.whl" \
        "numpy-2.2.6-cp310-cp310-macosx_10_9_x86_64.whl" \
        "pandas-2.3.3-cp310-cp310-macosx_10_9_x86_64.whl" \
        "tree_sitter-0.26.0-cp310-cp310-macosx_10_9_x86_64.whl" \
        "tree_sitter_java-0.23.5-cp39-abi3-macosx_10_9_x86_64.whl" \
        "tree_sitter_python-0.25.0-cp310-abi3-macosx_10_9_x86_64.whl" \
        "tree_sitter_javascript-0.25.0-cp310-abi3-macosx_10_9_x86_64.whl" \
        2>&1 | grep -E "(Successfully|already satisfied)" | head -20
elif [ "$PLATFORM" = "manylinux" ]; then
    pip3 install --no-index --find-links="$OFFLINE_DIR" \
        "pyyaml-6.0.3-cp310-cp310-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl" \
        "markupsafe-3.0.3-cp310-cp310-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl" \
        "numpy-2.2.6-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl" \
        "pandas-2.3.2-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl" \
        "tree_sitter-0.26.0-cp310-cp310-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl" \
        "tree_sitter_java-0.23.5-cp39-abi3-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64.whl" \
        "tree_sitter_python-0.25.0-cp310-abi3-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl" \
        "tree_sitter_javascript-0.25.0-cp310-abi3-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl" \
        2>&1 | grep -E "(Successfully|already satisfied)" | head -20
elif [ "$PLATFORM" = "win_amd64" ]; then
    pip3 install --no-index --find-links="$OFFLINE_DIR" \
        "pyyaml-6.0.3-cp310-cp310-win_amd64.whl" \
        "markupsafe-3.0.3-cp310-cp310-win_amd64.whl" \
        "numpy-2.2.6-cp310-cp310-win_amd64.whl" \
        "pandas-2.3.3-cp310-cp310-win_amd64.whl" \
        "tree_sitter-0.26.0-cp310-cp310-win_amd64.whl" \
        "tree_sitter_java-0.23.5-cp39-abi3-win_amd64.whl" \
        "tree_sitter_python-0.25.0-cp310-abi3-win_amd64.whl" \
        "tree_sitter_javascript-0.25.0-cp310-abi3-win_amd64.whl" \
        2>&1 | grep -E "(Successfully|already satisfied)" | head -20
fi

echo ""
echo "=========================================="
echo "✅ 离线依赖安装完成"
echo "=========================================="
echo ""
echo "验证安装："
python3 -c "import yaml, git, rich, jinja2, pandas, tree_sitter; print('✅ 所有依赖包已正确安装')" 2>&1 || echo "⚠️ 部分依赖包可能未安装成功"
