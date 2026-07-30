import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.DocumentBuilder;
import org.w3c.dom.Document;
import java.io.InputStream;

/**
 * 安全示例：XXE 防护
 *
 * 安全说明：
 * 通过设置多个安全特性，完全禁用了外部实体和 DTD 处理，
 * 从根本上防止了 XXE 攻击。
 *
 * 预期检出：无（不应被检出为漏洞）
 */
public class Safe {

    public Document parseXml(InputStream input) throws Exception {
        // 安全：已禁用外部实体和 DTD
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
        factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
        factory.setFeature("http://apache.org/xml/features/nonvalidating/load-external-dtd", false);
        factory.setXIncludeAware(false);
        DocumentBuilder builder = factory.newDocumentBuilder();
        return builder.parse(input);
    }

    public Document parseXmlFromFile(String filePath) throws Exception {
        // 安全：同样禁用了外部实体
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
        factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
        factory.setXIncludeAware(false);
        DocumentBuilder builder = factory.newDocumentBuilder();
        return builder.parse(new java.io.File(filePath));
    }
}
