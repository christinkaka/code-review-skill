"""
安全示例：命令注入防护 - Python

安全说明：
使用 subprocess 模块时，避免 shell=True，将命令和参数分开传递，
用户输入作为参数列表元素，不会被 shell 解释为命令。

预期检出：无（不应被检出为漏洞）
"""

import subprocess
import shlex


def run_command_safe(user_input: str) -> str:
    """安全：使用列表形式传递参数，避免 shell=True"""
    # 安全：shell=False（默认值），参数以列表形式传递
    result = subprocess.run(
        ["echo", user_input],
        capture_output=True,
        text=True,
    )
    return result.stdout


def run_command_with_shlex_safe(user_input: str) -> str:
    """安全：使用 shlex.quote 转义用户输入"""
    # 安全：shlex.quote 对用户输入进行 shell 转义
    safe_input = shlex.quote(user_input)
    result = subprocess.run(
        f"echo {safe_input}",
        shell=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def find_files_safe(search_term: str) -> str:
    """安全：使用列表形式传递 find 命令参数"""
    # 安全：参数列表传递，不使用 shell
    result = subprocess.run(
        ["find", "/var/log", "-name", search_term],
        capture_output=True,
        text=True,
    )
    return result.stdout


def grep_files_safe(pattern: str) -> str:
    """安全：使用列表形式传递 grep 命令参数"""
    # 安全：参数列表传递，不使用 shell
    process = subprocess.Popen(
        ["grep", "-r", pattern, "/var/log/"],
        stdout=subprocess.PIPE,
    )
    stdout, _ = process.communicate()
    return stdout.decode()
