import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;

/**
 * 漏洞示例：路径穿越（Path Traversal）
 *
 * 问题说明：
 * 直接使用用户输入的文件名构造文件路径，未做任何校验，
 * 攻击者可以通过 "../" 等路径遍历字符访问系统任意文件。
 *
 * 预期检出：
 * - 行号：22
 * - 规则 ID：path-traversal-java-file
 * - 严重级别：ERROR
 */
public class Vulnerable {

    private static final String BASE_DIR = "/var/data/uploads";

    /**
     * 漏洞：直接使用用户输入构造文件路径，未校验路径穿越
     */
    public InputStream readFile(String fileName) throws IOException {
        // 漏洞：直接拼接用户输入，未过滤 "../" 等路径穿越字符
        File file = new File(BASE_DIR, fileName);  // 第 24 行 - 路径穿越漏洞点
        return new FileInputStream(file);
    }

    /**
     * 漏洞：使用 replace 过滤但不完整，可被绕过
     */
    public InputStream readFileWeakFilter(String fileName) throws IOException {
        // 漏洞：仅过滤 "../" 但不过滤 "..\" 或 URL 编码的 "../"
        String sanitized = fileName.replace("../", "");  // 第 32 行 - 不完整的过滤
        File file = new File(BASE_DIR, sanitized);  // 第 33 行 - 仍可被绕过
        return new FileInputStream(file);
    }
}
