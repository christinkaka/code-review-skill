"""
开放重定向规则 e2e 测试
验证 redirect-pattern-2 规则的 TP/TN 矩阵
"""
import pytest
import sys
import os

# 添加 scripts 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from rule_engine import RuleEngine


class TestOpenRedirectE2E:
    @pytest.fixture
    def engine(self, tmp_path):
        """创建规则引擎实例"""
        specs_dir = os.path.join(os.path.dirname(__file__), '..', 'references')
        with open(os.path.join(specs_dir, 'profiles', 'default.yaml')) as f:
            import yaml
            profile = yaml.safe_load(f)
        return RuleEngine(specs_dir, profile)

    def test_vuln_direct_sendRedirect(self, engine, tmp_path):
        """TP: 直接将请求参数传入 sendRedirect"""
        code = '''
import javax.servlet.http.*;
public class Vuln {
    public void doGet(HttpServletRequest req, HttpServletResponse resp) throws Exception {
        String url = req.getParameter("url");
        resp.sendRedirect(url);  // marker: vuln-direct
    }
}
'''
        f = tmp_path / "Vuln.java"
        f.write_text(code)
        issues = engine.run(repo_path=str(tmp_path), changed_files=[{"path": "Vuln.java"}])
        assert any("redirect-pattern-2" in i.get("rule_id", "") for i in issues), \
            f"Expected redirect-pattern-2 to match, got: {issues}"

    def test_vuln_variable_propagation(self, engine, tmp_path):
        """TP: 变量传播后 sendRedirect"""
        code = '''
import javax.servlet.http.*;
public class Vuln {
    public void redirect(HttpServletRequest req, HttpServletResponse resp) throws Exception {
        String url = req.getParameter("url");
        HttpServletResponse response = resp;
        response.sendRedirect(url);  // marker: vuln-propagation
    }
}
'''
        f = tmp_path / "Vuln.java"
        f.write_text(code)
        issues = engine.run(repo_path=str(tmp_path), changed_files=[{"path": "Vuln.java"}])
        assert any("redirect-pattern-2" in i.get("rule_id", "") for i in issues), \
            f"Expected redirect-pattern-2 to match, got: {issues}"

    def test_safe_isAllowedDomain(self, engine, tmp_path):
        """TN: isAllowedDomain 白名单校验"""
        code = '''
import javax.servlet.http.*;
public class Safe {
    public void doGet(HttpServletRequest req, HttpServletResponse resp) throws Exception {
        String url = req.getParameter("url");
        if (isAllowedDomain(url)) {
            resp.sendRedirect(url);  // marker: safe-whitelist
        }
    }
    private boolean isAllowedDomain(String u) { return true; }
}
'''
        f = tmp_path / "Safe.java"
        f.write_text(code)
        issues = engine.run(repo_path=str(tmp_path), changed_files=[{"path": "Safe.java"}])
        assert not any("redirect-pattern-2" in i.get("rule_id", "") for i in issues), \
            f"Expected redirect-pattern-2 NOT to match, got: {issues}"

    def test_safe_startsWith(self, engine, tmp_path):
        """TN: startsWith 相对路径限制"""
        code = '''
import javax.servlet.http.*;
public class Safe {
    public void redirect(HttpServletRequest req, HttpServletResponse resp) throws Exception {
        String url = req.getParameter("url");
        if (url.startsWith("/")) {
            resp.sendRedirect(url);  // marker: safe-relative
        }
    }
}
'''
        f = tmp_path / "Safe.java"
        f.write_text(code)
        issues = engine.run(repo_path=str(tmp_path), changed_files=[{"path": "Safe.java"}])
        assert not any("redirect-pattern-2" in i.get("rule_id", "") for i in issues), \
            f"Expected redirect-pattern-2 NOT to match, got: {issues}"

    def test_safe_constant_url(self, engine, tmp_path):
        """TN: 常量 URL，无污点源"""
        code = '''
import javax.servlet.http.*;
public class Safe {
    public void constantRedirect(HttpServletResponse resp) throws Exception {
        resp.sendRedirect("https://trusted.com/home");  // marker: safe-constant
    }
}
'''
        f = tmp_path / "Safe.java"
        f.write_text(code)
        issues = engine.run(repo_path=str(tmp_path), changed_files=[{"path": "Safe.java"}])
        assert not any("redirect-pattern-2" in i.get("rule_id", "") for i in issues), \
            f"Expected redirect-pattern-2 NOT to match, got: {issues}"
