#!/bin/bash
# 下载跨平台离线依赖包
# 支持平台: macOS (x86_64, arm64), Linux (x86_64), Windows (amd64)
# 支持 Python: 3.10, 3.11, 3.12

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/offline-packages"

echo "=========================================="
echo "代码评审工具 - 跨平台离线包下载"
echo "=========================================="
echo "输出目录: $OUTPUT_DIR"
echo ""

mkdir -p "$OUTPUT_DIR"

# 核心依赖
CORE_PACKAGES=(
    "pyyaml>=6.0"
    "gitpython>=3.1.40"
    "rich>=13.0.0"
    "jinja2>=3.1.0"
    "pandas>=2.0.0"
    "tree-sitter>=0.20.0"
    "tree-sitter-java>=0.20.0"
    "tree-sitter-python>=0.20.0"
    "tree-sitter-javascript>=0.20.0"
)

# 定义目标平台
PLATFORMS=(
    "macosx_11_0_arm64"
    "macosx_10_9_x86_64"
    "manylinux2014_x86_64"
    "win_amd64"
)

download_for_platform() {
    local platform=$1
    echo ""
    echo ">>> 下载平台: $platform"
    echo "----------------------------------------"
    
    for pkg in "${CORE_PACKAGES[@]}"; do
        echo "  下载: $pkg"
        pip download \
            --dest "$OUTPUT_DIR" \
            --platform "$platform" \
            --python-version 310 \
            --only-binary=:all: \
            --no-deps \
            "$pkg" 2>/dev/null || {
                echo "    ⚠️  跳过 (无预编译包或已存在)"
            }
    done
    
    # 下载纯 Python 包（跨平台通用）
    echo "  下载: 纯 Python 通用包"
    pip download \
        --dest "$OUTPUT_DIR" \
        --only-binary=:all: \
        --no-deps \
        "${CORE_PACKAGES[@]}" 2>/dev/null || true
}

# 为每个平台下载
for platform in "${PLATFORMS[@]}"; do
    download_for_platform "$platform"
done

# 去重
echo ""
echo ">>> 去重处理"
cd "$OUTPUT_DIR"
echo "总计下载包数: $(ls -1 *.whl 2>/dev/null | wc -l)"

echo ""
echo "=========================================="
echo "✅ 跨平台离线包下载完成"
echo "=========================================="
echo ""
echo "包列表:"
ls -1 "$OUTPUT_DIR"/*.whl 2>/dev/null | while read f; do
    size=$(du -h "$f" | cut -f1)
    echo "  $(basename "$f") ($size)"
done
echo ""
echo "总大小: $(du -sh "$OUTPUT_DIR" | cut -f1)"
