# XXE - DocumentBuilder 解析 XML 未禁用外部实体

> DocumentBuilder 解析 XML 输入，但 DocumentBuilderFactory 未禁用外部实体。

```yaml
id: xxe-java-document-builder
languages: [java]
severity: ERROR
cwe: CWE-611
owasp: A05:2021
```

## 问题说明

即使 `DocumentBuilderFactory` 的创建和 `DocumentBuilder.parse()` 的调用不在同一段代码中，
只要 Factory 未禁用外部实体，整个解析流程就存在 XXE 风险。

## 违规示例

```java
DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
DocumentBuilder builder = factory.newDocumentBuilder();
Document doc = builder.parse(xmlInput); // 危险：Factory 未配置安全特性
```

## 检测模式

```pattern
DocumentBuilderFactory $FACTORY = DocumentBuilderFactory.newInstance();
...
DocumentBuilder $BUILDER = $FACTORY.newDocumentBuilder();
...
$BUILDER.parse(...);
```

```pattern-not
DocumentBuilderFactory $FACTORY = DocumentBuilderFactory.newInstance();
...
$FACTORY.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
...
DocumentBuilder $BUILDER = $FACTORY.newDocumentBuilder();
...
$BUILDER.parse(...);
```

---

# XXE - SAXParser 未禁用外部实体

> SAXParser 未禁用外部实体，存在 XXE 风险。

```yaml
id: xxe-java-sax-parser
languages: [java]
severity: ERROR
cwe: CWE-611
owasp: A05:2021
```

## 违规示例

```java
SAXParserFactory factory = SAXParserFactory.newInstance();
SAXParser parser = factory.newSAXParser();
parser.parse(inputStream, handler);
```

## 正确示例

```java
SAXParserFactory factory = SAXParserFactory.newInstance();
factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
SAXParser parser = factory.newSAXParser();
```

## 检测模式

```pattern
SAXParserFactory $FACTORY = SAXParserFactory.newInstance();
...
SAXParser $PARSER = $FACTORY.newSAXParser();
...
$PARSER.parse(...);
```

```pattern
SAXParserFactory $FACTORY = SAXParserFactory.newInstance();
...
$FACTORY.newSAXParser().parse(...);
```

```pattern-not
SAXParserFactory $FACTORY = SAXParserFactory.newInstance();
...
$FACTORY.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
...
SAXParser $PARSER = $FACTORY.newSAXParser();
...
$PARSER.parse(...);
```

```pattern-not
SAXParserFactory $FACTORY = SAXParserFactory.newInstance();
...
$FACTORY.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
...
$FACTORY.newSAXParser().parse(...);
```

---

# XXE - XMLReader 未配置安全特性

> XMLReader 未配置安全特性，存在 XXE 风险。

```yaml
id: xxe-java-xml-reader
languages: [java]
severity: ERROR
cwe: CWE-611
```

## 检测模式

```pattern
XMLReader $READER = XMLReaderFactory.createXMLReader();
...
$READER.parse(...);
```

---

# XXE - JAXB Unmarshaller 风险

> JAXB Unmarshaller 处理外部 XML 输入时可能存在 XXE 风险。

```yaml
id: xxe-java-unmarshaller
languages: [java]
severity: WARNING
cwe: CWE-611
```

## 检测模式

```pattern
Unmarshaller $UM = $JAXB_CONTEXT.createUnmarshaller();
...
$UM.unmarshal(...);
```

---

# XXE - Python lxml 不安全解析

> lxml.etree.parse() 默认可能解析外部实体，建议使用 defusedxml 替代。

```yaml
id: xxe-python-lxml
languages: [python]
severity: WARNING
cwe: CWE-611
```

## 违规示例

```python
from lxml import etree
tree = etree.parse(xml_file)
```

## 正确示例

```python
from defusedxml.lxml import fromstring, parse
tree = parse(xml_file)
```

## 检测模式

```pattern
from lxml import etree
...
etree.parse($SOURCE)
```

---

# XXE - Python xml.dom.minidom 不安全解析

> xml.dom.minidom 不安全处理外部实体，建议使用 defusedxml。

```yaml
id: xxe-python-xml-dom
languages: [python]
severity: ERROR
cwe: CWE-611
```

## 正确示例

```python
from defusedxml.minidom import parse
doc = parse(xml_file)
```

## 检测模式

```pattern
import xml.dom.minidom
...
xml.dom.minidom.parse($SOURCE)
```

---

# XXE - Python lxml XMLParser 默认配置

> lxml.etree.XMLParser() 使用默认配置，未禁用外部实体解析（resolve_entities 默认为 True），存在 XXE 漏洞。

```yaml
id: xxe-python-lxml-parser
languages: [python]
severity: ERROR
cwe: CWE-611
```

## 违规示例

```python
from lxml import etree
parser = etree.XMLParser()  # 危险：resolve_entities 默认为 True
tree = etree.parse(xml_file, parser)
```

## 正确示例

```python
from lxml import etree
parser = etree.XMLParser(resolve_entities=False, no_network=True, dtd_validation=False)
tree = etree.parse(xml_file, parser)
```

## 检测模式

```pattern
from lxml import etree
...
etree.XMLParser()
```

```pattern-not
from lxml import etree
...
etree.XMLParser(resolve_entities=False, ...)
```

---

# XXE - Python lxml etree.parse 未传入安全解析器

> lxml.etree.parse() 未传入安全解析器，使用默认配置解析 XML 文件，存在 XXE 漏洞。

```yaml
id: xxe-python-lxml-parse
languages: [python]
severity: ERROR
cwe: CWE-611
```

## 违规示例

```python
from lxml import etree
tree = etree.parse(xml_file)  # 危险：未传入安全解析器
```

## 正确示例

```python
from lxml import etree
parser = etree.XMLParser(resolve_entities=False, no_network=True)
tree = etree.parse(xml_file, parser)
```

## 检测模式

```pattern
from lxml import etree
...
etree.parse($FILE_PATH)
```

```pattern-not
from lxml import etree
...
$PARSER = etree.XMLParser(resolve_entities=False, ...)
...
etree.parse($FILE_PATH, $PARSER)
```

---

# XXE - Python lxml 显式启用 resolve_entities

> 显式设置 resolve_entities=True，主动启用了外部实体解析，存在 XXE 漏洞。

```yaml
id: xxe-python-lxml-resolve-entities
languages: [python]
severity: ERROR
cwe: CWE-611
```

## 违规示例

```python
from lxml import etree
parser = etree.XMLParser(resolve_entities=True)  # 危险：显式启用外部实体解析
```

## 正确示例

```python
from lxml import etree
parser = etree.XMLParser(resolve_entities=False)
```

## 检测模式

```pattern
from lxml import etree
...
etree.XMLParser(resolve_entities=True, ...)
```
