import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.PrintWriter;
import java.io.IOException;

/**
 * 漏洞示例：XSS（Cross-Site Scripting）跨站脚本攻击
 *
 * 问题说明：
 * Servlet 直接将用户输入的请求参数写入 HTTP 响应，
 * 未进行任何编码或过滤，攻击者可以注入恶意脚本。
 *
 * 预期检出：
 * - 行号：24
 * - 规则 ID：xss-java-servlet-output
 * - 严重级别：ERROR
 */
public class Vulnerable extends HttpServlet {

    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response)
            throws IOException {
        response.setContentType("text/html;charset=UTF-8");
        PrintWriter out = response.getWriter();

        // 漏洞：直接将用户输入写入响应，未进行 HTML 编码
        String userName = request.getParameter("name");
        out.println("<html><body>");
        out.println("<h1>Welcome, " + userName + "</h1>");  // 第 29 行 - XSS 漏洞点
        out.println("</body></html>");
        out.flush();
    }

    @Override
    protected void doPost(HttpServletRequest request, HttpServletResponse response)
            throws IOException {
        response.setContentType("text/html;charset=UTF-8");
        PrintWriter out = response.getWriter();

        // 漏洞：同样未编码，直接回显用户输入
        String comment = request.getParameter("comment");
        out.println("<html><body>");
        out.println("<div class='comment'>" + comment + "</div>");  // 第 41 行 - XSS 漏洞点
        out.println("</body></html>");
        out.flush();
    }
}
