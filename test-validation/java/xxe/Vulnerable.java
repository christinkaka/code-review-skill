import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.DocumentBuilder;
import org.w3c.dom.Document;
import java.io.InputStream;

/**
 * 漏洞示例：XXE（XML External Entity）注入
 *
 * 问题说明：
 * DocumentBuilderFactory 创建后未禁用外部实体解析，
 * 攻击者可以构造恶意 XML 读取服务器文件或发起 SSRF 攻击。
 *
 * 预期检出：
 * - 行号：16
 * - 规则 ID：xxe-java-document-builder
 * - 严重级别：ERROR
 */
public class Vulnerable {

    public Document parseXml(InputStream input) throws Exception {
        // 漏洞：未禁用外部实体，直接创建解析器
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        DocumentBuilder builder = factory.newDocumentBuilder();
        return builder.parse(input);  // 第 23 行 - XXE 漏洞点
    }

    public Document parseXmlFromFile(String filePath) throws Exception {
        // 漏洞：同样未禁用外部实体
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        DocumentBuilder builder = factory.newDocumentBuilder();
        return builder.parse(new java.io.File(filePath));  // 第 29 行 - XXE 漏洞点
    }
}
