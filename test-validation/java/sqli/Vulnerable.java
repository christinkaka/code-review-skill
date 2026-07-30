import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.Statement;
import java.sql.ResultSet;
import java.sql.SQLException;

/**
 * 漏洞示例：SQL 注入（SQL Injection）
 *
 * 问题说明：
 * 直接将用户输入拼接到 SQL 语句中执行，
 * 攻击者可以通过构造恶意输入执行任意 SQL 命令。
 *
 * 预期检出：
 * - 行号：27, 42
 * - 规则 ID：sqli-java-statement-execute
 * - 严重级别：ERROR
 */
public class Vulnerable {

    private Connection getConnection() throws SQLException {
        return DriverManager.getConnection("jdbc:mysql://localhost:3306/mydb", "user", "pass");
    }

    /**
     * 漏洞：字符串拼接构造 SQL，存在 SQL 注入
     */
    public ResultSet findUserByName(String userName) throws SQLException {
        Connection conn = getConnection();
        Statement stmt = conn.createStatement();

        // 漏洞：直接拼接用户输入到 SQL 语句中
        String sql = "SELECT * FROM users WHERE name = '" + userName + "'";  // 第 29 行 - SQL 注入漏洞点
        return stmt.executeQuery(sql);  // 第 30 行 - 执行注入 SQL
    }

    /**
     * 漏洞：字符串拼接构造 SQL，存在 SQL 注入
     */
    public boolean authenticate(String user, String pass) throws SQLException {
        Connection conn = getConnection();
        Statement stmt = conn.createStatement();

        // 漏洞：直接拼接用户名和密码到 SQL 中
        String sql = "SELECT * FROM users WHERE username='" + user
                + "' AND password='" + pass + "'";  // 第 40-41 行 - SQL 注入漏洞点
        ResultSet rs = stmt.executeQuery(sql);  // 第 42 行 - 执行注入 SQL
        return rs.next();
    }
}
