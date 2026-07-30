"""
漏洞示例：路径穿越（Path Traversal）- Python

问题说明：
直接使用用户输入构造文件路径，未做任何校验，
攻击者可以通过 "../" 等路径遍历字符访问系统任意文件。

预期检出：
- 行号：18, 27
- 规则 ID：priv-python-open-user-input
- 严重级别：ERROR
"""

import os

BASE_DIR = "/var/data/uploads"


def read_file_unsafe(filename: str) -> str:
    """漏洞：直接使用用户输入构造文件路径"""
    # 漏洞：直接拼接用户输入，未校验路径穿越
    filepath = os.path.join(BASE_DIR, filename)  # 第 19 行 - 路径穿越漏洞点
    with open(filepath, "r") as f:  # 第 20 行 - 打开未校验的文件
        return f.read()


def read_file_weak_filter(filename: str) -> str:
    """漏洞：仅简单替换 '../'，可被绕过"""
    # 漏洞：仅过滤 "../"，不过滤 "..\\" 或 URL 编码
    sanitized = filename.replace("../", "")  # 第 28 行 - 不完整的过滤
    filepath = os.path.join(BASE_DIR, sanitized)  # 第 29 行 - 仍可被绕过
    with open(filepath, "r") as f:
        return f.read()


def write_file_unsafe(filename: str, content: str) -> None:
    """漏洞：写入文件时未校验路径"""
    # 漏洞：直接拼接用户输入写文件
    filepath = os.path.join(BASE_DIR, filename)  # 第 37 行 - 路径穿越漏洞点
    with open(filepath, "w") as f:
        f.write(content)
