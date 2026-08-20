#!/bin/bash
# Semgrep 离线安装脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OFFLINE_DIR="${SCRIPT_DIR}/semgrep-offline-packages"

echo "═══════════════════════════════════════════════════════════════"
echo "                    Semgrep 离线安装脚本"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# 检查离线包目录
if [ ! -d "${OFFLINE_DIR}" ]; then
    echo "❌ 错误: 离线包目录不存在: ${OFFLINE_DIR}"
    echo "请先运行: pip3 download semgrep -d semgrep-offline-packages"
    exit 1
fi

# 检查离线包数量
PACKAGE_COUNT=$(ls -1 "${OFFLINE_DIR}"/*.whl 2>/dev/null | wc -l)
if [ "${PACKAGE_COUNT}" -eq 0 ]; then
    echo "❌ 错误: 离线包目录为空"
    exit 1
fi

echo "✅ 找到 ${PACKAGE_COUNT} 个离线包"
echo ""

# 安装 Semgrep
echo "正在安装 Semgrep..."
pip3 install --no-index --find-links="${OFFLINE_DIR}" semgrep --break-system-packages

echo ""
echo "✅ Semgrep 安装成功"
echo ""

# 验证安装
if command -v semgrep &> /dev/null; then
    SEMGREP_VERSION=$(semgrep --version)
    echo "✅ Semgrep 版本: ${SEMGREP_VERSION}"
else
    echo "❌ 错误: Semgrep 安装失败"
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "                    安装完成"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "使用方法:"
echo "  semgrep --version                    # 检查版本"
echo "  semgrep --config auto /path/to/code  # 扫描代码"
echo "  semgrep --config references/security/xxe.md /path/to/code  # 使用自定义规则"
echo ""
