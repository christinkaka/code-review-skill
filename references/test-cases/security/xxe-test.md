# XXE 测试案例

## 违规代码 - DocumentBuilderFactory

```java
public Document parseXml(InputStream inputStream) throws Exception {
    DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
    DocumentBuilder builder = factory.newDocumentBuilder();
    return builder.parse(inputStream);
}
```

**预期命中**: `xxe-java-document-builder`
**文件类型**: `.java`

---

## 违规代码 - SAXParser

```java
public void parseWithSax(InputStream input, Handler handler) throws Exception {
    SAXParserFactory factory = SAXParserFactory.newInstance();
    SAXParser parser = factory.newSAXParser();
    parser.parse(input, handler);
}
```

**预期命中**: `xxe-java-sax-parser`
**文件类型**: `.java`

---

## 违规代码 - Python lxml

```python
from lxml import etree

def parse_xml(file_path):
    tree = etree.parse(file_path)
    return tree.getroot()
```

**预期命中**: `xxe-python-lxml`
**文件类型**: `.py`

---

## 正确代码 - DocumentBuilderFactory 已禁用外部实体

```java
public Document parseXml(InputStream inputStream) throws Exception {
    DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
    factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
    factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
    DocumentBuilder builder = factory.newDocumentBuilder();
    return builder.parse(inputStream);
}
```

**预期命中**: 无
**文件类型**: `.java`
