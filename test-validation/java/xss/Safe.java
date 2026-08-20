import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.PrintWriter;
import java.io.IOException;

/**
 * 安全示例：XSS 防护
 *
 * 安全说明：
 * 对用户输入进行了 HTML 实体编码后再写入响应，
 * 确保特殊字符被转义，防止脚本注入。
 *
 * 预期检出：无（不应被检出为漏洞）
 */
public class Safe extends HttpServlet {

    /**
     * HTML 实体编码，防止 XSS
     */
    private String encodeHtml(String input) {
        if (input == null) {
            return "";
        }
        return input.replace("&", "&amp;")
                     .replace("<", "&lt;")
                     .replace(">", "&gt;")
                     .replace("\"", "&quot;")
                     .replace("'", "&#x27;");
    }

    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response)
            throws IOException {
        response.setContentType("text/html;charset=UTF-8");
        PrintWriter out = response.getWriter();

        // 安全：对用户输入进行 HTML 编码后再输出
        String userName = request.getParameter("name");
        String safeName = encodeHtml(userName);
        out.println("<html><body>");
        out.println("<h1>Welcome, " + safeName + "</h1>");
        out.println("</body></html>");
        out.flush();
    }

    @Override
    protected void doPost(HttpServletRequest request, HttpServletResponse response)
            throws IOException {
        response.setContentType("text/html;charset=UTF-8");
        PrintWriter out = response.getWriter();

        // 安全：同样进行了 HTML 编码
        String comment = request.getParameter("comment");
        String safeComment = encodeHtml(comment);
        out.println("<html><body>");
        out.println("<div class='comment'>" + safeComment + "</div>");
        out.println("</body></html>");
        out.flush();
    }
}
