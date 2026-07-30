"""
安全示例：XXE 防护 - Python

安全说明：
通过配置 lxml 的 XMLParser 禁用外部实体和 DTD 处理，
从根本上防止 XXE 攻击。

预期检出：无（不应被检出为漏洞）
"""

from lxml import etree


def parse_xml_safe(xml_string: str) -> etree._Element:
    """安全：禁用外部实体和 DTD 加载"""
    # 安全：显式禁用外部实体和 DTD
    parser = etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        dtd_validation=False,
        load_dtd=False,
    )
    root = etree.fromstring(xml_string.encode(), parser)
    return root


def parse_xml_file_safe(file_path: str) -> etree._ElementTree:
    """安全：使用安全的解析器解析文件"""
    # 安全：使用禁用了外部实体的解析器
    parser = etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        dtd_validation=False,
        load_dtd=False,
    )
    tree = etree.parse(file_path, parser)
    return tree


def parse_xml_defusedxml(xml_string: str) -> etree._Element:
    """安全：使用 defusedxml 库替代 lxml"""
    # 安全：defusedxml 默认禁用所有危险特性
    from defusedxml import ElementTree as safe_etree
    root = safe_etree.fromstring(xml_string)
    return root
