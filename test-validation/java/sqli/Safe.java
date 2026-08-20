import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;

/**
 * 安全示例：SQL 注入防护
 *
 * 安全说明：
 * 使用 PreparedStatement 和参数化查询，
 * 用户输入作为参数绑定，不会被解释为 SQL 代码，
 * 从根本上防止了 SQL 注入攻击。
 *
 * 预期检出：无（不应被检出为漏洞）
 */
public class Safe {

    private Connection getConnection() throws SQLException {
        return DriverManager.getConnection("jdbc:mysql://localhost:3306/mydb", "user", "pass");
    }

    /**
     * 安全：使用 PreparedStatement 参数化查询
     */
    public ResultSet findUserByName(String userName) throws SQLException {
        Connection conn = getConnection();

        // 安全：使用 ? 占位符，参数化查询
        String sql = "SELECT * FROM users WHERE name = ?";
        PreparedStatement pstmt = conn.prepareStatement(sql);
        pstmt.setString(1, userName);
        return pstmt.executeQuery();
    }

    /**
     * 安全：使用 PreparedStatement 参数化查询
     */
    public boolean authenticate(String user, String pass) throws SQLException {
        Connection conn = getConnection();

        // 安全：使用 ? 占位符，参数化查询
        String sql = "SELECT * FROM users WHERE username = ? AND password = ?";
        PreparedStatement pstmt = conn.prepareStatement(sql);
        pstmt.setString(1, user);
        pstmt.setString(2, pass);
        ResultSet rs = pstmt.executeQuery();
        return rs.next();
    }
}
