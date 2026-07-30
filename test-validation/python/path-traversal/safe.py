"""
安全示例：路径穿越防护 - Python

安全说明：
通过规范化路径并验证其是否位于允许的基目录内，
确保无法通过路径穿越访问基目录之外的文件。

预期检出：无（不应被检出为漏洞）
"""

import os
from pathlib import Path

BASE_DIR = "/var/data/uploads"


def read_file_safe(filename: str) -> str:
    """安全：规范化路径后验证是否在基目录内"""
    # 安全：规范化路径并验证
    base_path = os.path.realpath(BASE_DIR)
    filepath = os.path.realpath(os.path.join(BASE_DIR, filename))

    if not filepath.startswith(base_path):
        raise ValueError(f"Path traversal detected: {filename}")

    with open(filepath, "r") as f:
        return f.read()


def read_file_pathlib_safe(filename: str) -> str:
    """安全：使用 pathlib 进行路径校验"""
    # 安全：使用 pathlib 的 resolve 和 is_relative_to
    base_path = Path(BASE_DIR).resolve()
    filepath = (base_path / filename).resolve()

    if not filepath.is_relative_to(base_path):
        raise ValueError(f"Path traversal detected: {filename}")

    with open(filepath, "r") as f:
        return f.read()


def write_file_safe(filename: str, content: str) -> None:
    """安全：写入文件时验证路径"""
    # 安全：同样验证路径
    base_path = Path(BASE_DIR).resolve()
    filepath = (base_path / filename).resolve()

    if not filepath.is_relative_to(base_path):
        raise ValueError(f"Path traversal detected: {filename}")

    with open(filepath, "w") as f:
        f.write(content)
