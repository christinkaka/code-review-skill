# XXE 漏洞 - DocumentBuilder 未禁用外部实体

## 问题描述
当代码使用 DocumentBuilder 解析 XML 输入时，如果 DocumentBuilderFactory 没有禁用外部实体，
攻击者可以构造恶意 XML 读取服务器文件或发起 SSRF 攻击。

## 违规场景
- 创建了 DocumentBuilderFactory 实例
- 没有调用 setFeature() 禁用外部实体
- 使用该 Factory 创建了 DocumentBuilder
- 调用了 parse() 方法解析输入

## 安全做法
在创建 DocumentBuilderFactory 后，立即调用：
- factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true)
- factory.setFeature("http://xml.org/sax/features/external-general-entities", false)

## 严重等级
ERROR - 可能导致敏感文件泄露或 SSRF

## 示例代码

### 违规代码
```java
DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
DocumentBuilder builder = factory.newDocumentBuilder();
Document doc = builder.parse(xmlInput);
```

### 安全代码
```java
DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
DocumentBuilder builder = factory.newDocumentBuilder();
Document doc = builder.parse(xmlInput);
```
