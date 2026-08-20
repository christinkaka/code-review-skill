import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Path;

/**
 * 安全示例：路径穿越防护
 *
 * 安全说明：
 * 通过规范化路径并验证其是否位于允许的基目录内，
 * 确保无法通过路径穿越访问基目录之外的文件。
 *
 * 预期检出：无（不应被检出为漏洞）
 */
public class Safe {

    private static final String BASE_DIR = "/var/data/uploads";

    /**
     * 安全：规范化路径后验证是否在允许的基目录内
     */
    public InputStream readFile(String fileName) throws IOException {
        File baseDir = new File(BASE_DIR).getCanonicalFile();
        File file = new File(baseDir, fileName);

        // 安全：规范化后检查路径是否在基目录内
        if (!file.getCanonicalPath().startsWith(baseDir.getCanonicalPath())) {
            throw new SecurityException("Path traversal detected: " + fileName);
        }

        return new FileInputStream(file);
    }

    /**
     * 安全：使用 NIO Path 进行路径校验
     */
    public InputStream readFileNio(String fileName) throws IOException {
        Path basePath = Path.of(BASE_DIR).toRealPath();
        Path filePath = basePath.resolve(fileName).normalize();

        // 安全：使用 NIO 的 startsWith 验证路径
        if (!filePath.startsWith(basePath)) {
            throw new SecurityException("Path traversal detected: " + fileName);
        }

        return new FileInputStream(filePath.toFile());
    }
}
