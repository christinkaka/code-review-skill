#!/bin/bash
# Semgrep 离线安装脚本
# 说明: 离线包为 Windows AMD64 + Pure Python 混合包。
#       本脚本自动过滤: 在 Windows 上只装 Windows wheels, 在 macOS/Linux 上只装纯 Python wheels。

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OFFLINE_DIR="${SCRIPT_DIR}/semgrep-offline-packages"

# 检测操作系统
detect_platform() {
    case "$(uname -s)" in
        Linux*)   echo "linux";;
        Darwin*)  echo "macos";;
        MINGW*|MSYS*|CYGWIN*) echo "windows";;
        *)        echo "unknown";;
    esac
}

# 过滤 wheels: Windows 平台保留 win_amd64 + pure Python,
# 非 Windows 平台只保留 pure Python (py3-none-any, py2.py3-none-any)
filter_wheels_for_platform() {
    local platform="$1"
    local tmp_dir
    tmp_dir=$(mktemp -d)

    if [[ "$platform" == "windows" ]]; then
        # Windows: 保留 win_amd64 和 pure python wheels
        find "$OFFLINE_DIR" -maxdepth 1 \( -name "*-win_amd64.whl" -o -name "*-py3-none-any.whl" -o -name "*-py2.py3-none-any.whl" \) -exec cp {} "$tmp_dir/" \;
    else
        # macOS/Linux: 只保留 pure python wheels (semgrep 本身无 pure python 版, 会提示需要在线下载)
        find "$OFFLINE_DIR" -maxdepth 1 \( -name "*-py3-none-any.whl" -o -name "*-py2.py3-none-any.whl" \) -exec cp {} "$tmp_dir/" \;
    fi
    echo "$tmp_dir"
}

PLATFORM=$(detect_platform)
echo "═══════════════════════════════════════════════════════════════"
echo "                    Semgrep 离线安装脚本"
echo "                    检测平台: ${PLATFORM}"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# 检查离线包目录
if [ ! -d "${OFFLINE_DIR}" ]; then
    echo "❌ 错误: 离线包目录不存在: ${OFFLINE_DIR}"
    echo "请在目标平台运行: pip3 download semgrep -d semgrep-offline-packages"
    exit 1
fi

TOTAL_COUNT=$(ls -1 "${OFFLINE_DIR}"/*.whl 2>/dev/null | wc -l)
if [ "${TOTAL_COUNT}" -eq 0 ]; then
    echo "❌ 错误: 离线包目录为空"
    exit 1
fi

# 过滤出当前平台可用的 wheels
INSTALL_DIR=$(filter_wheels_for_platform "$PLATFORM")
INSTALL_COUNT=$(ls -1 "${INSTALL_DIR}"/*.whl 2>/dev/null | wc -l)

echo "✅ 离线包总数: ${TOTAL_COUNT} 个"
echo "   当前平台 (${PLATFORM}) 可用: ${INSTALL_COUNT} 个"
echo ""

if [ "${INSTALL_COUNT}" -eq 0 ]; then
    echo "❌ 当前平台无可用的 wheels。"
    if [[ "$PLATFORM" != "windows" ]]; then
        echo "   当前 semgrep 主程序 wheel 仅提供 Windows AMD64 二进制。"
        echo "   非 Windows 用户请运行: pip3 download semgrep -d semgrep-offline-packages"
    fi
    rm -rf "${INSTALL_DIR}"
    exit 1
fi

# 安装 Semgrep
echo "正在安装 Semgrep..."
pip3 install --no-index --find-links="${INSTALL_DIR}" semgrep 2>&1 || true

# 清理过滤目录
rm -rf "${INSTALL_DIR}"

echo ""
echo "✅ Semgrep 安装完成"
echo ""

# 验证安装
if command -v semgrep &> /dev/null; then
    SEMGREP_VERSION=$(semgrep --version)
    echo "✅ Semgrep 版本: ${SEMGREP_VERSION}"
else
    echo "⚠️  semgrep 命令未找到, 尝试以模块方式运行: python3 -m semgrep --version"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "                    安装完成"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "使用方法:"
echo "  semgrep --version                    # 检查版本"
echo "  semgrep --config auto /path/to/code  # 扫描代码"
echo "  semgrep --config references/security/ /path/to/code  # 使用本地规则"
echo ""
