#!/usr/bin/env python3
"""
Harness CLI 入口脚本
用于 AI 评审质量管控
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from harness.cli import main

if __name__ == "__main__":
    main()
