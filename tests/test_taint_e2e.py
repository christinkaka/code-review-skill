"""taint 规则真实 semgrep 端到端集成测试

依赖本机 semgrep（与 TestRealSemgrepSandbox 同级约定）。
验证 path-traversal-taint 规则的检出/降噪行为与 PoC 结论一致。
"""

import shutil
from pathlib import Path

import pytest

from rule_engine import RuleEngine

pytestmark = pytest.mark.skipif(
    shutil.which("semgrep") is None, reason="本机未安装 semgrep"
)

_JAVA = """import java.io.File;
import java.nio.file.Files;
import java.nio.file.Paths;
import javax.servlet.http.HttpServletRequest;
import org.springframework.web.multipart.MultipartFile;

class Upload {
    void readUserFile(HttpServletRequest request) throws Exception {
        String userPath = request.getParameter("path");
        File f = new File("/data", userPath);
        Files.readAllBytes(f.toPath());
    }

    void readConstFile() throws Exception {
        File f = new File("/data", "a.txt");
        Files.readAllBytes(f.toPath());
    }

    void readSanitized(HttpServletRequest request) throws Exception {
        String userPath = request.getParameter("path");
        String nameOnly = new File(userPath).getName();
        File f = new File("/data", nameOnly);
        Files.readAllBytes(f.toPath());
    }

    void upload(MultipartFile file) throws Exception {
        String filename = file.getOriginalFilename();
        File dest = new File("/upload", filename);
        file.transferTo(dest);
    }

    void normalized(HttpServletRequest request) throws Exception {
        String userPath = request.getParameter("path");
        java.nio.file.Path p = Paths.get("/data", userPath).normalize();
        if (!p.startsWith("/data")) { throw new SecurityException("bad"); }
        Files.readAllBytes(p);
    }
}
"""

_METHODS = ("readUserFile", "readConstFile", "readSanitized", "upload", "normalized")


def _method_hits(java_source: str, issues: list) -> dict:
    method_at = {}
    current = None
    for idx, text in enumerate(java_source.split("\n"), start=1):
        for name in _METHODS:
            if name in text:
                current = name
        method_at[idx] = current
        if text.strip() == "}":
            current = None
    hits = set()
    for i in issues:
        if i.get("file") == "Upload.java":
            m = method_at.get(i.get("line"))
            if m:
                hits.add(m)
    return hits


class TestPathTraversalTaintE2E:
    def test_taint_rule_tp_and_tn_behavior(self, tmp_path):
        """真阳性检出 + 三类误报场景零误报"""
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "Upload.java").write_text(_JAVA, encoding="utf-8")

        specs_dir = Path(__file__).parent.parent / "references" / "security"
        engine = RuleEngine(
            str(specs_dir),
            {"specs": [{"path": "path-traversal.md", "enabled": True}]},
        )

        issues = engine.run(str(repo), [{"path": "Upload.java"}])
        taint_issues = [
            i for i in issues if "path-traversal-taint" in str(i.get("rule_id"))
        ]
        assert taint_issues, "taint 规则未产生任何检出"

        hits = _method_hits(_JAVA, taint_issues)

        assert "readUserFile" in hits, "真阳性：请求参数流入 File 构造应报出"
        assert "upload" in hits, "真阳性：上传文件名流入 transferTo 应报出"
        assert "readConstFile" not in hits, "常量拼接不应误报（旧模式规则误报场景）"
        assert "readSanitized" not in hits, "basename 净化不应误报"
        assert "normalized" not in hits, "normalize 净化不应误报"

    def test_python_rules_unaffected(self, tmp_path):
        """Java 交给 taint 后，Python 规则仍正常检出"""
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "app.py").write_text(
            "from flask import request\n"
            "def read_config():\n"
            "    config_path = request.args.get('config')\n"
            "    with open(config_path, 'r') as f:\n"
            "        return f.read()\n",
            encoding="utf-8",
        )

        specs_dir = Path(__file__).parent.parent / "references" / "security"
        engine = RuleEngine(
            str(specs_dir),
            {"specs": [{"path": "path-traversal.md", "enabled": True}]},
        )

        issues = engine.run(str(repo), [{"path": "app.py"}])
        py_rules = {
            str(i.get("rule_id")) for i in issues if i.get("file") == "app.py"
        }
        assert any("path-" in r and "taint" not in r for r in py_rules), (
            f"Python 模式规则应仍检出: {py_rules}"
        )


_SSRF_JAVA = """import java.io.IOException;
import java.net.HttpURLConnection;
import java.net.URI;
import java.net.URL;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.Set;
import javax.servlet.http.HttpServletRequest;

class Fetch {
    private static final Set<String> ALLOWED_HOSTS = Set.of("api.example.com");
    private final HttpClient client = HttpClient.newHttpClient();

    void fetchUserUrl(HttpServletRequest request) throws IOException {
        String userUrl = request.getParameter("url");
        URL url = new URL(userUrl);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
    }

    void fetchViaHttpClient(HttpServletRequest request) throws Exception {
        String userUrl = request.getParameter("url");
        HttpRequest req = HttpRequest.newBuilder()
            .uri(URI.create(userUrl))
            .build();
        client.send(req, HttpResponse.BodyHandlers.ofString());
    }

    void fetchConstUrl() throws IOException {
        URL url = new URL("https://api.example.com/v1/health");
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
    }

    void fetchWhitelisted(HttpServletRequest request) throws IOException {
        String userUrl = request.getParameter("url");
        URL url = new URL(userUrl);
        if (!ALLOWED_HOSTS.contains(url.getHost())) {
            throw new SecurityException("URL not allowed");
        }
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
    }

    void fetchGuarded(HttpServletRequest request) throws IOException {
        String userUrl = request.getParameter("url");
        if (!isAllowedUrl(userUrl)) {
            throw new SecurityException("URL not allowed");
        }
        URL url = new URL(userUrl);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
    }

    private boolean isAllowedUrl(String u) {
        return ALLOWED_HOSTS.contains(u);
    }
}
"""

_SSRF_METHODS = (
    "fetchUserUrl", "fetchViaHttpClient", "fetchConstUrl",
    "fetchWhitelisted", "fetchGuarded", "isAllowedUrl",
)


def _ssrf_method_hits(java_source: str, issues: list) -> set:
    method_at = {}
    current = None
    for idx, text in enumerate(java_source.split("\n"), start=1):
        for name in _SSRF_METHODS:
            if f" {name}(" in text or f"boolean {name}(" in text:
                current = name
        method_at[idx] = current
        if text.strip() == "}":
            current = None
    hits = set()
    for i in issues:
        if i.get("file") == "Fetch.java":
            m = method_at.get(i.get("line"))
            if m:
                hits.add(m)
    return hits


class TestSsrfTaintE2E:
    def test_taint_rule_tp_and_tn_behavior(self, tmp_path):
        """真阳性检出 + 三类误报场景零误报"""
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "Fetch.java").write_text(_SSRF_JAVA, encoding="utf-8")

        specs_dir = Path(__file__).parent.parent / "references" / "security"
        engine = RuleEngine(
            str(specs_dir),
            {"specs": [{"path": "ssrf.md", "enabled": True}]},
        )

        issues = engine.run(str(repo), [{"path": "Fetch.java"}])
        taint_issues = [
            i for i in issues if "ssrf-taint" in str(i.get("rule_id"))
        ]
        assert taint_issues, "ssrf-taint 规则未产生任何检出"

        hits = _ssrf_method_hits(_SSRF_JAVA, taint_issues)

        assert "fetchUserUrl" in hits, "真阳性：请求参数流入 openConnection 应报出"
        assert "fetchViaHttpClient" in hits, (
            "真阳性：请求参数经 URI 构造流入 client.send 应报出"
        )
        assert "fetchConstUrl" not in hits, "常量 URL 不应误报（纯解析/常量场景）"
        assert "fetchWhitelisted" not in hits, "host 白名单校验后不应误报"
        assert "fetchGuarded" not in hits, "约定式校验函数净化后不应误报"

    def test_python_rules_unaffected(self, tmp_path):
        """Java 交给 taint 后，Python SSRF 规则仍正常检出"""
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "app.py").write_text(
            "import requests\n"
            "from flask import request\n"
            "def fetch():\n"
            "    url = request.args.get('url')\n"
            "    return requests.get(url).text\n",
            encoding="utf-8",
        )

        specs_dir = Path(__file__).parent.parent / "references" / "security"
        engine = RuleEngine(
            str(specs_dir),
            {"specs": [{"path": "ssrf.md", "enabled": True}]},
        )

        issues = engine.run(str(repo), [{"path": "app.py"}])
        py_rules = {
            str(i.get("rule_id")) for i in issues if i.get("file") == "app.py"
        }
        assert any("ssrf-python" in r for r in py_rules), (
            f"Python SSRF 规则应仍检出: {py_rules}"
        )


_XSS_JAVA = """import java.io.IOException;
import java.io.PrintWriter;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import org.springframework.web.util.HtmlUtils;

class OutputServlet {
    void writeUserInput(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {
        String name = request.getParameter("name");
        response.getWriter().write("Hello, " + name);
    }

    void printlnUserInput(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {
        String comment = request.getParameter("comment");
        PrintWriter out = response.getWriter();
        out.println("<p>" + comment + "</p>");
    }

    void writeConstString(HttpServletResponse response)
            throws ServletException, IOException {
        response.getWriter().write("<html><body>Hello</body></html>");
    }

    void writeEscaped(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {
        String name = request.getParameter("name");
        response.getWriter().write("Hello, " + HtmlUtils.htmlEscape(name));
    }

    void writeCustomEscape(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {
        String name = request.getParameter("name");
        response.getWriter().write("Hello, " + escapeHtml(name));
    }

    private String escapeHtml(String s) {
        return s.replace("<", "&lt;").replace(">", "&gt;");
    }
}
"""

_XSS_METHODS = (
    "writeUserInput", "printlnUserInput", "writeConstString",
    "writeEscaped", "writeCustomEscape", "escapeHtml",
)


def _xss_method_hits(java_source: str, issues: list) -> set:
    method_at = {}
    current = None
    for idx, text in enumerate(java_source.split("\n"), start=1):
        for name in _XSS_METHODS:
            if f" {name}(" in text or f"void {name}(" in text:
                current = name
        method_at[idx] = current
        if text.strip() == "}":
            current = None
    hits = set()
    for i in issues:
        if i.get("file") == "OutputServlet.java":
            m = method_at.get(i.get("line"))
            if m:
                hits.add(m)
    return hits


class TestXssTaintE2E:
    def test_taint_rule_tp_and_tn_behavior(self, tmp_path):
        """真阳性检出 + 三类误报场景零误报"""
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "OutputServlet.java").write_text(_XSS_JAVA, encoding="utf-8")

        specs_dir = Path(__file__).parent.parent / "references" / "security"
        engine = RuleEngine(
            str(specs_dir),
            {"specs": [{"path": "xss.md", "enabled": True}]},
        )

        issues = engine.run(str(repo), [{"path": "OutputServlet.java"}])
        taint_issues = [
            i for i in issues if "xss-taint" in str(i.get("rule_id"))
        ]
        assert taint_issues, "xss-taint 规则未产生任何检出"

        hits = _xss_method_hits(_XSS_JAVA, taint_issues)

        assert "writeUserInput" in hits, "真阳性：请求参数流入 response.getWriter().write 应报出"
        assert "printlnUserInput" in hits, "真阳性：请求参数流入 out.println 应报出"
        assert "writeConstString" not in hits, "常量字符串输出不应误报"
        assert "writeEscaped" not in hits, "HtmlUtils.htmlEscape 转义后不应误报"
        assert "writeCustomEscape" not in hits, "自定义 escapeHtml 转义后不应误报"

    def test_file_write_is_not_xss_sink(self, tmp_path):
        """hello-world 盲测实证（FileController:105）：Files.write 是文件写入，
        不是 HTTP 响应输出，不应报 XSS。旧 sink $WRITER.write(...) 曾误报。
        同时验证全限定名 HtmlUtils 转义净化。"""
        java = (
            "import java.nio.file.Files;\n"
            "import java.nio.file.Paths;\n"
            "import javax.servlet.http.HttpServletResponse;\n"
            "import org.springframework.web.bind.annotation.*;\n"
            "import org.springframework.web.multipart.MultipartFile;\n"
            "\n"
            "class Upload {\n"
            "    @PostMapping(\"/upload\")\n"
            "    String uploadProfile(@RequestParam(\"file\") MultipartFile file)\n"
            "            throws Exception {\n"
            "        String filename = file.getOriginalFilename();\n"
            "        java.nio.file.Path filePath = Paths.get(\"/app/uploads/\" + filename);\n"
            "        Files.write(filePath, file.getBytes());\n"
            "        return \"ok\";\n"
            "    }\n"
            "\n"
            "    @GetMapping(\"/greet\")\n"
            "    void greet(@RequestParam String name, HttpServletResponse response)\n"
            "            throws Exception {\n"
            "        response.getWriter().write(\n"
            "            org.springframework.web.util.HtmlUtils.htmlEscape(name));\n"
            "    }\n"
            "}\n"
        )
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "Upload.java").write_text(java, encoding="utf-8")

        specs_dir = Path(__file__).parent.parent / "references" / "security"
        engine = RuleEngine(
            str(specs_dir),
            {"specs": [{"path": "xss.md", "enabled": True}]},
        )

        issues = engine.run(str(repo), [{"path": "Upload.java"}])
        xss = [i for i in issues if "xss-taint" in str(i.get("rule_id"))]
        assert not xss, (
            f"文件写入/转义输出不应报 XSS（旧 $WRITER.write(...) sink 误报场景）: {xss}"
        )

    def test_js_rules_unaffected(self, tmp_path):
        """Java 交给 taint 后，JS XSS 规则仍正常检出"""
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "app.js").write_text(
            "function displayUserContent(userInput) {\n"
            "    const container = document.getElementById('content');\n"
            "    container.innerHTML = userInput;\n"
            "}\n",
            encoding="utf-8",
        )

        specs_dir = Path(__file__).parent.parent / "references" / "security"
        engine = RuleEngine(
            str(specs_dir),
            {"specs": [{"path": "xss.md", "enabled": True}]},
        )

        issues = engine.run(str(repo), [{"path": "app.js"}])
        js_rules = {
            str(i.get("rule_id")) for i in issues if i.get("file") == "app.js"
        }
        assert any("xss-js" in r for r in js_rules), (
            f"JS XSS 规则应仍检出: {js_rules}"
        )


# ==================== SQL Injection Taint E2E ====================

_SQLI_JAVA = """
import java.sql.*;
import javax.servlet.http.HttpServletRequest;

class UserDao {
    private Connection conn;

    // TP1: 请求参数 → 字符串拼接 → executeQuery
    void findUserById(HttpServletRequest request) throws SQLException {
        String userId = request.getParameter("id");
        String sql = "SELECT * FROM users WHERE id = " + userId;
        Statement stmt = conn.createStatement();
        ResultSet rs = stmt.executeQuery(sql);
    }

    // TP2: 请求参数 → 直接拼接到 execute 参数
    void findUserByName(HttpServletRequest request) throws SQLException {
        String name = request.getParameter("name");
        Statement stmt = conn.createStatement();
        stmt.execute("SELECT * FROM users WHERE name = '" + name + "'");
    }

    // TP3: 请求参数 → prepareStatement SQL 构造
    void findUserViaPrepare(HttpServletRequest request) throws SQLException {
        String userId = request.getParameter("id");
        String sql = "SELECT * FROM users WHERE id = " + userId;
        PreparedStatement ps = conn.prepareStatement(sql);
        ps.executeQuery();
    }

    // TN1: PreparedStatement + setString 参数绑定（安全）
    void findUserSafe(HttpServletRequest request) throws SQLException {
        String userId = request.getParameter("id");
        String sql = "SELECT * FROM users WHERE id = ?";
        PreparedStatement ps = conn.prepareStatement(sql);
        ps.setString(1, userId);
        ResultSet rs = ps.executeQuery();
    }

    // TN2: 常量 SQL 执行（无污点源）
    void listAllUsers() throws SQLException {
        Statement stmt = conn.createStatement();
        ResultSet rs = stmt.executeQuery("SELECT * FROM users");
    }

    // TN3: PreparedStatement + setInt 参数绑定（安全）
    void findUserByAge(HttpServletRequest request) throws SQLException {
        String ageStr = request.getParameter("age");
        int age = Integer.parseInt(ageStr);
        String sql = "SELECT * FROM users WHERE age = ?";
        PreparedStatement ps = conn.prepareStatement(sql);
        ps.setInt(1, age);
        ResultSet rs = ps.executeQuery();
    }
}
"""


def _sqli_method_hits(java_source: str, issues: list) -> set:
    """Map issue line numbers to method names."""
    method_at = {}
    current = None
    for idx, text in enumerate(java_source.split("\n"), start=1):
        for name in (
            "findUserById", "findUserByName", "findUserViaPrepare",
            "findUserSafe", "listAllUsers", "findUserByAge",
        ):
            if f" {name}(" in text:
                current = name
        method_at[idx] = current
        if text.strip() == "}":
            current = None
    hits = set()
    for i in issues:
        if i.get("file") == "UserDao.java":
            m = method_at.get(i.get("line"))
            if m:
                hits.add(m)
    return hits


class TestSqliTaintE2E:
    def test_taint_rule_tp_and_tn_behavior(self, tmp_path):
        """真阳性检出 + 三类误报场景零误报"""
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "UserDao.java").write_text(_SQLI_JAVA, encoding="utf-8")

        specs_dir = Path(__file__).parent.parent / "references" / "security"
        engine = RuleEngine(
            str(specs_dir),
            {"specs": [{"path": "sql-injection.md", "enabled": True}]},
        )

        issues = engine.run(str(repo), [{"path": "UserDao.java"}])
        taint_issues = [
            i for i in issues if "sqli-taint" in str(i.get("rule_id"))
        ]
        assert taint_issues, "sqli-taint 规则未产生任何检出"

        hits = _sqli_method_hits(_SQLI_JAVA, taint_issues)

        # 真阳性
        assert "findUserById" in hits, "TP1: 请求参数 → 字符串拼接 → executeQuery 应报出"
        assert "findUserByName" in hits, "TP2: 请求参数直接拼接到 execute 应报出"
        assert "findUserViaPrepare" in hits, "TP3: 请求参数流入 prepareStatement SQL 应报出"

        # 真阴性
        assert "findUserSafe" not in hits, "TN1: PreparedStatement + setString 不应误报"
        assert "listAllUsers" not in hits, "TN2: 常量 SQL 执行不应误报"
        assert "findUserByAge" not in hits, "TN3: PreparedStatement + setInt 不应误报"

    def test_untyped_execute_receivers_not_flagged(self, tmp_path):
        """类型化 sink（2026-08-26，java-sec-code 盲测实证）：非 JDBC/JPA
        receiver 的 execute(...) 不应命中。盲测中 QLExpress 的
        ExpressRunner.execute()（加固后的 sec 方法）误报；ExecutorService
        .execute() 是真实代码高频调用，同为过宽 sink 的误报面。
        注意 semgrep 类型化元变量不做子类型匹配，PreparedStatement 声明
        的变量需由显式 PreparedStatement sink 命中（盲测漏报场景）。
        """
        java = (
            "import java.sql.*;\n"
            "import java.util.concurrent.*;\n"
            "import javax.servlet.http.HttpServletRequest;\n"
            "import org.springframework.web.bind.annotation.*;\n"
            "\n"
            "class Mixed {\n"
            "    private Connection conn;\n"
            "\n"
            "    // TN: ExpressRunner.execute 是表达式执行，非 SQL（QLExpress sec 场景）\n"
            "    @PostMapping(\"/express\")\n"
            "    String express(@RequestParam String input) throws Exception {\n"
            "        Object r = new ExpressRunner().execute(input, null, null, true, false);\n"
            "        return r.toString();\n"
            "    }\n"
            "\n"
            "    // TN: ExecutorService.execute 是线程池提交，非 SQL\n"
            "    @PostMapping(\"/async\")\n"
            "    String async(@RequestParam String input) {\n"
            "        ExecutorService pool = Executors.newFixedThreadPool(2);\n"
            "        pool.execute(() -> System.out.println(input));\n"
            "        return \"ok\";\n"
            "    }\n"
            "\n"
            "    // TP: PreparedStatement 声明变量的 executeQuery（无 prepareStatement\n"
            "    // 中间 sink，直接命中 PreparedStatement 类型化 sink；对应 java-sec-code\n"
            "    // SQLI.java:153 场景——类型化不做子类型匹配时此用例会漏报）\n"
            "    @PostMapping(\"/ps\")\n"
            "    String psVuln(@RequestParam String username) throws SQLException {\n"
            "        PreparedStatement st = getPs();\n"
            "        return String.valueOf(st.executeQuery(\n"
            "            \"select * from users where name = '\" + username + \"'\"));\n"
            "    }\n"
            "\n"
            "    PreparedStatement getPs() throws SQLException {\n"
            "        return conn.prepareStatement(\"select 1\");\n"
            "    }\n"
            "}\n"
            "\n"
            "class ExpressRunner {\n"
            "    Object execute(String s, Object c, Object l, boolean a, boolean b) {\n"
            "        return s;\n"
            "    }\n"
            "}\n"
        )
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "Mixed.java").write_text(java, encoding="utf-8")

        specs_dir = Path(__file__).parent.parent / "references" / "security"
        engine = RuleEngine(
            str(specs_dir),
            {"specs": [{"path": "sql-injection.md", "enabled": True}]},
        )

        issues = engine.run(str(repo), [{"path": "Mixed.java"}])
        lines = {
            i["line"] for i in issues
            if "sqli-taint" in str(i.get("rule_id")) and i.get("file") == "Mixed.java"
        }
        src = java.split("\n")
        express_line = next(
            n for n, t in enumerate(src, 1) if "ExpressRunner().execute" in t)
        pool_line = next(
            n for n, t in enumerate(src, 1) if "pool.execute" in t)
        ps_line = next(
            n for n, t in enumerate(src, 1) if "st.executeQuery(" in t)

        assert express_line not in lines, (
            "TN: ExpressRunner.execute 是表达式执行，不应命中 SQL sink"
        )
        assert pool_line not in lines, (
            "TN: ExecutorService.execute 是线程池提交，不应命中 SQL sink"
        )
        assert ps_line in lines, (
            "TP: PreparedStatement 声明变量的 executeQuery 应命中"
        )

    def test_python_rules_unaffected(self, tmp_path):
        """Java 交给 taint 后，Python SQL 注入规则仍正常检出"""
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "app.py").write_text(
            "from flask import request\n"
            "def find_user():\n"
            "    user_id = request.args.get('id')\n"
            "    cursor.execute(f\"SELECT * FROM users WHERE id = {user_id}\")\n"
            "    return cursor.fetchone()\n",
            encoding="utf-8",
        )

        specs_dir = Path(__file__).parent.parent / "references" / "security"
        engine = RuleEngine(
            str(specs_dir),
            {"specs": [{"path": "sql-injection.md", "enabled": True}]},
        )

        issues = engine.run(str(repo), [{"path": "app.py"}])
        py_rules = {
            str(i.get("rule_id")) for i in issues if i.get("file") == "app.py"
        }
        assert any("sqli-python" in r for r in py_rules), (
            f"Python SQL 注入规则应仍检出: {py_rules}"
        )


# ==================== Deserialization Taint E2E ====================

_DESER_JAVA = """import java.io.ByteArrayInputStream;
import java.io.FileInputStream;
import java.io.ObjectInputStream;
import javax.naming.InitialContext;
import javax.servlet.http.HttpServletRequest;

class Serializer {
    private final InitialContext ctx = new InitialContext();

    // TP1: 请求输入流直接流入反序列化
    void deserializeRequestStream(HttpServletRequest request) throws Exception {
        ObjectInputStream ois = new ObjectInputStream(request.getInputStream());
        Object obj = ois.readObject();
    }

    // TP2: 请求参数经字节包装传播后流入反序列化
    void deserializeRequestParam(HttpServletRequest request) throws Exception {
        String payload = request.getParameter("payload");
        byte[] data = payload.getBytes();
        ObjectInputStream ois = new ObjectInputStream(new ByteArrayInputStream(data));
        Object obj = ois.readObject();
    }

    // TP3: 请求参数流入 JNDI lookup（旧模式规则未覆盖）
    void lookupUserInput(HttpServletRequest request) throws Exception {
        String name = request.getParameter("name");
        Object obj = ctx.lookup(name);
    }

    // TN1: 常量本地文件反序列化（无污点源）
    void deserializeLocalConfig() throws Exception {
        ObjectInputStream ois = new ObjectInputStream(new FileInputStream("config/data.ser"));
        Object obj = ois.readObject();
    }
}
"""

_DESER_METHODS = (
    "deserializeRequestStream", "deserializeRequestParam",
    "lookupUserInput", "deserializeLocalConfig",
)


def _deser_method_hits(
    java_source: str,
    issues: list,
    filename: str = "Serializer.java",
    methods: tuple = _DESER_METHODS,
) -> set:
    method_at = {}
    current = None
    for idx, text in enumerate(java_source.split("\n"), start=1):
        for name in methods:
            if f" {name}(" in text:
                current = name
        method_at[idx] = current
        if text.strip() == "}":
            current = None
    hits = set()
    for i in issues:
        if i.get("file") == filename:
            m = method_at.get(i.get("line"))
            if m:
                hits.add(m)
    return hits


class TestDeserTaintE2E:
    def test_taint_rule_tp_and_tn_behavior(self, tmp_path):
        """真阳性检出（含 JNDI 新覆盖）+ 常量文件零误报"""
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "Serializer.java").write_text(_DESER_JAVA, encoding="utf-8")

        specs_dir = Path(__file__).parent.parent / "references" / "security"
        engine = RuleEngine(
            str(specs_dir),
            {"specs": [{"path": "deserialization.md", "enabled": True}]},
        )

        issues = engine.run(str(repo), [{"path": "Serializer.java"}])
        taint_issues = [
            i for i in issues if "deser-taint" in str(i.get("rule_id"))
        ]
        assert taint_issues, "deser-taint 规则未产生任何检出"

        hits = _deser_method_hits(_DESER_JAVA, taint_issues)

        # 真阳性
        assert "deserializeRequestStream" in hits, (
            "TP1: 请求输入流直接流入 new ObjectInputStream 应报出"
        )
        assert "deserializeRequestParam" in hits, (
            "TP2: 请求参数经 ByteArrayInputStream 包装流入反序列化应报出"
        )
        assert "lookupUserInput" in hits, "TP3: 请求参数流入 ctx.lookup 应报出（JNDI）"

        # 真阴性
        assert "deserializeLocalConfig" not in hits, (
            "TN1: 常量本地文件反序列化不应误报（旧模式规则误报场景）"
        )

    def test_snakeyaml_taint_tp_and_tn(self, tmp_path):
        """deser-yaml-taint（2026-08-26 新增，java-sec-code Rce.java 缺口）：
        默认构造器 load TP；SafeConstructor 加固豁免；常量 TN
        """
        java = (
            "import org.springframework.web.bind.annotation.GetMapping;\n"
            "import org.yaml.snakeyaml.Yaml;\n"
            "import org.yaml.snakeyaml.constructor.SafeConstructor;\n"
            "\n"
            "class YamlCases {\n"
            "    @GetMapping(\"/vuln\")\n"
            "    void vuln(String content) {\n"
            "        Yaml y = new Yaml();\n"
            "        y.load(content);\n"
            "    }\n"
            "\n"
            "    @GetMapping(\"/sec\")\n"
            "    void sec(String content) {\n"
            "        Yaml y = new Yaml(new SafeConstructor());\n"
            "        y.load(content);\n"
            "    }\n"
            "\n"
            "    @GetMapping(\"/const\")\n"
            "    void constLoad() {\n"
            "        Yaml y = new Yaml();\n"
            "        y.load(\"a: 1\");\n"
            "    }\n"
            "}\n"
        )
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "YamlCases.java").write_text(java, encoding="utf-8")

        specs_dir = Path(__file__).parent.parent / "references" / "security"
        engine = RuleEngine(
            str(specs_dir),
            {"specs": [{"path": "deserialization.md", "enabled": True}]},
        )

        issues = engine.run(str(repo), [{"path": "YamlCases.java"}])
        yaml_methods = ("vuln", "sec", "constLoad")
        yaml_issues = [
            i for i in issues if "deser-yaml-taint" in str(i.get("rule_id"))
        ]
        hits = _deser_method_hits(
            java, yaml_issues, filename="YamlCases.java", methods=yaml_methods
        )
        assert "vuln" in hits, "TP: 默认构造器 Yaml.load(污点) 应报出"
        assert "sec" not in hits, "TN: SafeConstructor 加固后不应报"
        assert "constLoad" not in hits, "TN: 常量内容无污点源不应报"

        # 原 deser-taint 不受新规则影响：SnakeYAML 场景不产 ObjectInputStream 告警
        deser_hits = _deser_method_hits(
            java,
            [i for i in issues if str(i.get("rule_id", "")).endswith("deser-taint")],
            filename="YamlCases.java",
            methods=yaml_methods,
        )
        assert not deser_hits, "deser-taint 不应命中 SnakeYAML 场景"

    def test_python_rules_unaffected(self, tmp_path):
        """Java 交给 taint 后，Python pickle 规则仍正常检出"""
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "app.py").write_text(
            "import pickle\n"
            "from flask import request\n"
            "def load():\n"
            "    payload = request.args.get('payload')\n"
            "    return pickle.loads(payload)\n",
            encoding="utf-8",
        )

        specs_dir = Path(__file__).parent.parent / "references" / "security"
        engine = RuleEngine(
            str(specs_dir),
            {"specs": [{"path": "deserialization.md", "enabled": True}]},
        )

        issues = engine.run(str(repo), [{"path": "app.py"}])
        py_rules = {
            str(i.get("rule_id")) for i in issues if i.get("file") == "app.py"
        }
        assert any("deser-python" in r for r in py_rules), (
            f"Python pickle 规则应仍检出: {py_rules}"
        )


# ==================== Spring Entry-Point Anchoring E2E ====================

_ENTRYPOINT_JAVA = """import java.io.ObjectInputStream;
import java.io.ByteArrayInputStream;
import javax.persistence.EntityManager;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestBody;

class Api {
    private EntityManager entityManager;

    @PostMapping("/deserialize")
    String deserialize(@RequestBody String payload) throws Exception {
        ObjectInputStream ois = new ObjectInputStream(new ByteArrayInputStream(payload.getBytes()));
        return ois.readObject().toString();
    }

    @GetMapping("/search")
    String search(String q) {
        String jpql = "SELECT u FROM User u WHERE u.name LIKE '%" + q + "%'";
        return entityManager.createQuery(jpql).getResultList().toString();
    }

    @RequestMapping("/legacy")
    String legacy(String id) {
        String sql = "SELECT * FROM users WHERE id = " + id;
        return entityManager.createNativeQuery(sql).getResultList().toString();
    }

    @javax.transaction.Transactional
    void txMethod(String payload) throws Exception {
        ObjectInputStream ois = new ObjectInputStream(new ByteArrayInputStream(payload.getBytes()));
        ois.readObject();
    }

    void plainHelper(String q) {
        String jpql = "SELECT u FROM User u WHERE u.name LIKE '%" + q + "%'";
        entityManager.createQuery(jpql);
    }

    @GetMapping("/constant")
    String constant() {
        String jpql = "SELECT u FROM User u";
        return entityManager.createQuery(jpql).getResultList().toString();
    }
}
"""

_ENTRYPOINT_METHODS = (
    "deserialize", "search", "legacy", "txMethod", "plainHelper", "constant",
)


def _entrypoint_method_hits(issues: list) -> dict:
    """按方法名归类命中行（行号 -> 最近上方方法名）"""
    method_at = {}
    current = None
    for idx, text in enumerate(_ENTRYPOINT_JAVA.split("\n"), start=1):
        for name in _ENTRYPOINT_METHODS:
            if name in text:
                current = name
        method_at[idx] = current
        if text.strip() == "}":
            current = None
    hits = {}
    for i in issues:
        if i.get("file") == "Api.java":
            m = method_at.get(i.get("line"))
            if m:
                hits.setdefault(m, set()).add(str(i.get("rule_id")))
    return hits


class TestSpringEntrypointE2E:
    """入口点锚定（2026-08-26）：参数级注解过滤在 Semgrep Java 签名
    匹配中不可靠（@Transactional 参数同样命中），改为方法级 mapping
    注解锚定：入口点方法全部参数视为用户可控（Spring 隐式绑定语义）。
    """

    def _run_engine(self, tmp_path, spec_name):
        repo = tmp_path / "repo"
        repo.mkdir(exist_ok=True)
        (repo / "Api.java").write_text(_ENTRYPOINT_JAVA, encoding="utf-8")
        specs_dir = Path(__file__).parent.parent / "references" / "security"
        engine = RuleEngine(
            str(specs_dir),
            {"specs": [{"path": spec_name, "enabled": True}]},
        )
        return engine.run(str(repo), [{"path": "Api.java"}])

    def test_deser_entrypoint_tp_and_tn(self, tmp_path):
        issues = self._run_engine(tmp_path, "deserialization.md")
        taint = [i for i in issues if "deser-taint" in str(i.get("rule_id"))]
        hits = _entrypoint_method_hits(taint)

        assert "deserialize" in hits, (
            "TP: @PostMapping + @RequestBody 参数流入 ObjectInputStream 应报出"
        )
        assert "txMethod" not in hits, (
            "TN: @Transactional 非入口方法参数不应作为污点源（此前参数级注解写法误报）"
        )

    def test_sqli_entrypoint_tp_and_tn(self, tmp_path):
        issues = self._run_engine(tmp_path, "sql-injection.md")
        taint = [i for i in issues if "sqli-taint" in str(i.get("rule_id"))]
        hits = _entrypoint_method_hits(taint)

        assert "search" in hits, (
            "TP: @GetMapping 隐式参数绑定流入 createQuery 拼接应报出（hello-world 盲测漏检场景）"
        )
        assert "legacy" in hits, (
            "TP: @RequestMapping 参数流入 createNativeQuery 应报出"
        )
        assert "plainHelper" not in hits, (
            "TN: 无注解普通方法参数不应作为污点源"
        )
        assert "constant" not in hits, (
            "TN: 入口方法常量 SQL 不应误报"
        )

    def test_entrypoint_mark_expands_to_composite_sources(self):
        """引擎将 spring-entrypoint-param 标记展开为复合 source 结构"""
        specs_dir = Path(__file__).parent.parent / "references" / "security"
        engine = RuleEngine(
            str(specs_dir),
            {"specs": [{"path": "deserialization.md", "enabled": True}]},
        )
        semgrep_rules = engine._rules_to_semgrep()
        deser = next(
            r for r in semgrep_rules["rules"] if r.get("id") == "deser-taint"
        )
        sources = deser["pattern-sources"]
        composite = [s for s in sources if "patterns" in s]
        assert len(composite) == 6, (
            f"应展开 6 个入口注解复合 source，实际 {len(composite)}"
        )
        for c in composite:
            keys = [list(p.keys())[0] for p in c["patterns"]]
            assert keys == ["pattern-inside", "focus-metavariable"], (
                f"复合 source 结构异常: {keys}"
            )
