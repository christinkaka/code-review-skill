"""
漏洞示例：XXE（XML External Entity）注入 - Python

问题说明：
使用 lxml 的 etree.parse() 解析 XML 时，未禁用外部实体解析，
攻击者可以构造恶意 XML 读取服务器文件或发起 SSRF 攻击。

预期检出：
- 行号：22
- 规则 ID：xxe-python-lxml-parse
- 严重级别：ERROR
"""

from lxml import etree


def parse_xml_unsafe(xml_string: str) -> etree._Element:
    """漏洞：使用 lxml 解析 XML 时未禁用外部实体"""
    # 漏洞：直接使用默认解析器，未禁用外部实体
    parser = etree.XMLParser()  # 第 21 行 - 不安全的解析器
    root = etree.fromstring(xml_string.encode(), parser)  # 第 22 行 - XXE 漏洞点
    return root


def parse_xml_file_unsafe(file_path: str) -> etree._ElementTree:
    """漏洞：解析 XML 文件时未禁用外部实体"""
    # 漏洞：直接使用 etree.parse，未设置安全解析器
    tree = etree.parse(file_path)  # 第 28 行 - XXE 漏洞点
    return tree


def parse_xml_with_resolve(xml_string: str) -> etree._Element:
    """漏洞：显式启用 resolve_entities"""
    # 漏洞：显式设置 resolve_entities=True
    parser = etree.XMLParser(resolve_entities=True)  # 第 34 行 - XXE 漏洞点
    root = etree.fromstring(xml_string.encode(), parser)
    return root
