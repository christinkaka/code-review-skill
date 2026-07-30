# Semgrep 离线安装脚本 (Windows PowerShell)
# 用法: .\install-semgrep-offline.ps1

$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$OfflineDir = Join-Path $ScriptDir "semgrep-offline-packages"

Write-Host "======================================================================"
Write-Host "              Semgrep 离线安装脚本 (Windows)"
Write-Host "======================================================================"
Write-Host ""

# 检查离线包目录
if (-not (Test-Path $OfflineDir)) {
    Write-Host "❌ 错误: 离线包目录不存在: $OfflineDir"
    Write-Host "请先运行: pip download semgrep -d semgrep-offline-packages"
    exit 1
}

# 检查离线包数量
$Wheels = Get-ChildItem -Path $OfflineDir -Filter "*.whl" -File
if ($Wheels.Count -eq 0) {
    Write-Host "❌ 错误: 离线包目录为空"
    exit 1
}

# 统计平台分布
$WinAmd64 = ($Wheels | Where-Object { $_.Name -match "win_amd64" }).Count
$Py3None  = ($Wheels | Where-Object { $_.Name -match "py3-none-any|py2\.py3-none-any" }).Count
$Other    = $Wheels.Count - $WinAmd64 - $Py3None
Write-Host "✅ 找到 $($Wheels.Count) 个离线包"
Write-Host "   - Windows AMD64 专用: $WinAmd64 个"
Write-Host "   - Pure Python (跨平台): $Py3None 个"
Write-Host "   - 其他: $Other 个"
Write-Host ""

# 安装 Semgrep
Write-Host "正在安装 Semgrep..."
pip install --no-index --find-links="$OfflineDir" semgrep 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Semgrep 安装失败 (exit code: $LASTEXITCODE)"
    exit 1
}

Write-Host ""

# 验证安装
try {
    $Version = (semgrep --version 2>$null)
    if ($Version) {
        Write-Host "✅ Semgrep 安装成功, 版本: $Version"
    } else {
        Write-Host "❌ 无法获取 Semgrep 版本"
        exit 1
    }
} catch {
    Write-Host "❌ Semgrep 验证失败: $_"
    exit 1
}

Write-Host ""
Write-Host "======================================================================"
Write-Host "              安装完成"
Write-Host "======================================================================"
Write-Host ""
Write-Host "使用方法:"
Write-Host "  semgrep --version                              # 检查版本"
Write-Host "  semgrep --config auto D:\path\to\code          # 自动扫描"
Write-Host "  semgrep --config references\security\ /code    # 使用本地规则"
Write-Host ""
