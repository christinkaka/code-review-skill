"""
漏洞示例：命令注入（Command Injection）- Python

问题说明：
使用 subprocess 模块执行系统命令时，直接拼接用户输入，
攻击者可以通过构造恶意输入执行任意系统命令。

预期检出：
- 行号：18, 27, 36
- 规则 ID：priv-python-subprocess-run
- 严重级别：ERROR
"""

import subprocess
import os


def run_command_unsafe(user_input: str) -> str:
    """漏洞：subprocess.run 使用 shell=True 拼接用户输入"""
    # 漏洞：shell=True 且拼接用户输入，可执行任意命令
    cmd = f"echo {user_input}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)  # 第 19 行 - 命令注入漏洞点
    return result.stdout


def os_system_unsafe(filename: str) -> int:
    """漏洞：os.system 直接拼接用户输入"""
    # 漏洞：os.system 总是通过 shell 执行
    cmd = f"cat /tmp/{filename}"
    return os.system(cmd)  # 第 27 行 - 命令注入漏洞点


def popen_unsafe(user_input: str) -> str:
    """漏洞：subprocess.Popen 使用 shell=True"""
    # 漏洞：Popen 配合 shell=True 同样危险
    cmd = f"grep -r '{user_input}' /var/log/"
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)  # 第 35 行 - 命令注入漏洞点
    stdout, _ = process.communicate()
    return stdout.decode()


def check_output_unsafe(user_input: str) -> str:
    """漏洞：subprocess.check_output 使用 shell=True"""
    # 漏洞：check_output 配合 shell=True
    cmd = f"find / -name {user_input}"
    result = subprocess.check_output(cmd, shell=True, text=True)  # 第 43 行 - 命令注入漏洞点
    return result
