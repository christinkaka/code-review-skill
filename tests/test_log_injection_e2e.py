"""日志注入 taint 规则真实 semgrep 端到端集成测试

覆盖 log-injection.md（2026-08-26 平移改造，盲测实证驱动）：
- log-injection-taint：Java 由 pattern 平移为 taint（pattern 版仅匹配字面
  `log.` 接收者且无法区分常量实参；java-sec-code 盲测 2 命中 → 36 命中
  全为真实用户数据流，含 Log4j.java Log4Shell PoC 端点）
- log-injection-python：pattern 规则提升为独立规则

依赖本机 semgrep（与 test_pattern_rules_e2e.py 同级约定）。
"""

import shutil
from pathlib import Path

import pytest

from rule_engine import RuleEngine

pytestmark = pytest.mark.skipif(
    shutil.which("semgrep") is None, reason="本机未安装 semgrep"
)

_SPECS_DIR = Path(__file__).parent.parent / "references" / "security"

_LOG_JAVA = """import javax.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;

class LogCases {

    // TP1: 请求参数拼接进日志（经典 CRLF 注入形态）
    @RequestMapping("/login")
    void concat(HttpServletRequest request) {
        String username = request.getParameter("username");
        log.info("User login: " + username);
    }

    // TP2: SLF4J 参数化占位不净化 CRLF，仍报
    @RequestMapping("/param")
    void parameterized(HttpServletRequest request) {
        String username = request.getParameter("username");
        log.info("User login: {}", username);
    }

    // TP3: 接收者命名 logger（pattern 版字面 log. 全漏，taint 版命中）
    @RequestMapping("/logger")
    void loggerReceiver(HttpServletRequest request) {
        String host = request.getHeader("host");
        logger.info(host);
    }

    // TP4: 入口点参数经不透明辅助调用传播（request 为污点对象，
    // WebUtils.getRequestBody(request) 同型——java-sec-code XXE.java 实测）
    @RequestMapping("/helper")
    void opaqueHelper(HttpServletRequest request) {
        String body = WebUtils.getRequestBody(request);
        logger.info(body);
    }

    // TP5: 入口点方法参数直接入日志（java-sec-code Log4j.java
    // Log4Shell PoC 端点同型：logger.error(token)）
    @GetMapping("/log4j")
    void entryParam(String token) {
        logger.error(token);
    }

    // TN1: replaceAll 换行剥离（源码拼写一：\\n\\r）
    @RequestMapping("/clean1")
    void clean1(HttpServletRequest request) {
        String username = request.getParameter("username");
        String safe = username.replaceAll("[\\n\\r]", "_");
        log.info("User login: {}", safe);
    }

    // TN2: replaceAll 换行剥离（源码拼写二：双反斜杠）
    @RequestMapping("/clean2")
    void clean2(HttpServletRequest request) {
        String username = request.getParameter("username");
        String safe = username.replaceAll("[\\\\n\\\\r]", "_");
        log.info("User login: {}", safe);
    }

    // TN3: OWASP Encoder 净化
    @RequestMapping("/encode")
    void encode(HttpServletRequest request) {
        String username = request.getParameter("username");
        log.info("User login: {}", org.owasp.encoder.Encode.forHtml(username));
    }

    // TN4: 常量日志无污点源
    @RequestMapping("/const")
    void constant() {
        log.info("start processing");
        log.debug("step done");
    }

    // TN5: 异常消息无入口点污点（XXE/SSRF 12 处实测零误报）
    @RequestMapping("/exception")
    void exception(HttpServletRequest request) {
        try {
            request.getInputStream();
        } catch (Exception e) {
            logger.error(e.toString());
        }
    }

    // TN6: 环境属性非用户可控
    @RequestMapping("/sysprop")
    void sysProp() {
        logger.info("Working directory: " + System.getProperty("user.dir"));
    }
}
"""


class TestLogInjectionTaintE2E:
    def _scan(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "LogCases.java").write_text(_LOG_JAVA, encoding="utf-8")
        engine = RuleEngine(
            str(_SPECS_DIR),
            {"specs": [{"path": "log-injection.md", "enabled": True}]},
        )
        return engine.run(str(repo), [{"path": "LogCases.java"}])

    @staticmethod
    def _line_of(marker: str) -> int:
        return next(
            n for n, t in enumerate(_LOG_JAVA.split("\n"), 1) if marker in t
        )

    def _taint_lines(self, tmp_path):
        issues = self._scan(tmp_path)
        return {
            i["line"] for i in issues
            if "log-injection-taint" in str(i.get("rule_id"))
        }

    def test_true_positives(self, tmp_path):
        """拼接/参数化/logger 接收者/不透明辅助调用/入口参数 5 TP"""
        lines = self._taint_lines(tmp_path)
        assert self._line_of('log.info("User login: " + username)') in lines, (
            "TP1: 拼接形态应报出"
        )
        assert self._line_of('log.info("User login: {}", username)') in lines, (
            "TP2: SLF4J 参数化不净化 CRLF 应报出"
        )
        assert self._line_of("logger.info(host)") in lines, (
            "TP3: logger 接收者（pattern 版字面 log. 漏报场景）应报出"
        )
        assert self._line_of("logger.info(body)") in lines, (
            "TP4: 入口点参数经不透明辅助调用传播应报出"
        )
        # marker 带 ; 后缀：行 37 注释含同样代码文本会抢先命中
        assert self._line_of("logger.error(token);") in lines, (
            "TP5: 入口点方法参数直入日志应报出"
        )

    def test_sanitizers_and_true_negatives(self, tmp_path):
        """两种 replaceAll 拼写/Encode 净化；常量/异常/环境属性 TN"""
        lines = self._taint_lines(tmp_path)
        # marker 按源码拼写精确区分：TN1 单反斜杠 [\n\r]，TN2 双反斜杠 [\\n\\r]
        assert self._line_of('String safe = username.replaceAll("[\\n\\r]", "_");') not in lines, (
            "TN1: replaceAll 换行剥离（拼写一）后不应报"
        )
        assert self._line_of('String safe = username.replaceAll("[\\\\n\\\\r]", "_");') not in lines, (
            "TN2: replaceAll 换行剥离（拼写二）后不应报"
        )
        assert self._line_of("Encode.forHtml(username)") not in lines, (
            "TN3: OWASP Encoder 净化后不应报"
        )
        assert self._line_of('log.info("start processing")') not in lines, (
            "TN4: 常量日志无污点源不应报"
        )
        assert self._line_of("logger.error(e.toString())") not in lines, (
            "TN5: 异常消息不应报（XXE/SSRF 实测零误报场景）"
        )
        assert self._line_of('System.getProperty("user.dir")') not in lines, (
            "TN6: 环境属性非用户可控不应报"
        )

    def test_sinks_cover_five_log_levels(self):
        """DSL 构建：五个日志级别 sink + 三条净化器正确生成"""
        engine = RuleEngine(
            str(_SPECS_DIR),
            {"specs": [{"path": "log-injection.md", "enabled": True}]},
        )
        rules = engine._rules_to_semgrep()
        taint = next(
            r for r in rules["rules"] if r["id"] == "log-injection-taint"
        )
        sink_texts = [s["pattern"] for s in taint["pattern-sinks"]]
        for level in ("info", "debug", "warn", "error", "trace"):
            assert f"$LOG.{level}(...)" in sink_texts, (
                f"缺少 {level} 级别 sink"
            )
        san_texts = [s["pattern"] for s in taint.get("pattern-sanitizers", [])]
        assert any("replaceAll" in t for t in san_texts), "缺少 replaceAll 净化器"
        assert any("Encode.forHtml" in t for t in san_texts), "缺少 Encode 净化器"
