"""命令注入 taint 规则真实 semgrep 端到端集成测试

覆盖 command-injection.md（2026-08-26 新增，盲测缺口实证驱动：
java-sec-code Rce.java runtime/exec、ProcessBuilder 与
CommandInject.java 此前零规则检出）：
- cmdi-taint：三形态 sink（类型化声明 receiver / 链式 / ProcessBuilder
  构造器含数组初始化器拼接），cmdFilter 约定式净化豁免

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

_CMDI_JAVA = """import javax.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;

class CmdiCases {

    // TP1: 声明变量 receiver（java-sec-code Rce.java runtime/exec 同型）
    @GetMapping("/exec")
    String declared(String cmd) throws Exception {
        Runtime run = Runtime.getRuntime();
        Process p = run.exec(cmd);
        return p.getInputStream().toString();
    }

    // TP2: 链式 receiver（类型化元变量对链式返回值不推断，需单列 sink）
    @GetMapping("/exec2")
    String chained(HttpServletRequest request) throws Exception {
        String cmd = request.getParameter("cmd");
        Runtime.getRuntime().exec(cmd);
        return "ok";
    }

    // TP3: 数组初始化器内拼接污点（CommandInject.java codeinject 同型）
    @GetMapping("/pb1")
    String arrayInline(String filepath) throws Exception {
        String[] cmdList = new String[]{"sh", "-c", "ls -la " + filepath};
        ProcessBuilder builder = new ProcessBuilder(cmdList);
        return builder.start().getInputStream().toString();
    }

    // TP4: 污点数组变量传 ProcessBuilder（Rce.java ProcessBuilder 同型）
    @RequestMapping("/pb2")
    String directArray(String cmd) throws Exception {
        String[] arrCmd = {"/bin/sh", "-c", cmd};
        ProcessBuilder pb = new ProcessBuilder(arrCmd);
        return pb.start().getInputStream().toString();
    }

    // TP5: header 污点拼接（CommandInject.java host injection 同型）
    @GetMapping("/host")
    String hostHeader(HttpServletRequest request) throws Exception {
        String host = request.getHeader("host");
        String[] cmdList = new String[]{"sh", "-c", "curl " + host};
        ProcessBuilder hostBuilder = new ProcessBuilder(cmdList);
        return hostBuilder.start().getInputStream().toString();
    }

    // TN1: cmdFilter 约定式净化（CommandInject.java sec 同型）
    @GetMapping("/sec")
    String sanitized(String filepath) throws Exception {
        String clean = SecurityUtil.cmdFilter(filepath);
        String[] cmdList = new String[]{"sh", "-c", "ls -la " + clean};
        ProcessBuilder builder = new ProcessBuilder(cmdList);
        return builder.start().getInputStream().toString();
    }

    // TN2: 常量命令无污点源
    @GetMapping("/const")
    void constant() throws Exception {
        Runtime.getRuntime().exec("touch /tmp/x");
        ProcessBuilder pb = new ProcessBuilder("ls", "-la");
        pb.start();
    }

    // TN3: 非入口方法常量（main——Rce.java main 同型，入口点锚定不生效）
    public static void main(String[] args) throws Exception {
        Runtime.getRuntime().exec("touch /tmp/x");
    }
}
"""


class TestCommandInjectionE2E:
    def _scan(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "CmdiCases.java").write_text(_CMDI_JAVA, encoding="utf-8")
        engine = RuleEngine(
            str(_SPECS_DIR),
            {"specs": [{"path": "command-injection.md", "enabled": True}]},
        )
        return engine.run(str(repo), [{"path": "CmdiCases.java"}])

    @staticmethod
    def _line_of(marker: str) -> int:
        return next(
            n for n, t in enumerate(_CMDI_JAVA.split("\n"), 1) if marker in t
        )

    def _lines(self, tmp_path):
        issues = self._scan(tmp_path)
        return {
            i["line"] for i in issues
            if "cmdi-taint" in str(i.get("rule_id"))
        }

    def test_true_positives(self, tmp_path):
        """声明/链式 receiver、数组内联/变量、header 拼接 5 TP

        注：数组场景断言 sink 命中行（ProcessBuilder 构造行），semgrep
        报告位置是 sink 而非污点产生行（数组初始化行）。
        """
        lines = self._lines(tmp_path)
        assert self._line_of("Process p = run.exec(cmd);") in lines, (
            "TP1: 声明变量 receiver 的 exec 应报出"
        )
        assert self._line_of("Runtime.getRuntime().exec(cmd);") in lines, (
            "TP2: 链式 exec 应报出"
        )
        assert self._line_of("ProcessBuilder builder = new ProcessBuilder(cmdList);") in lines, (
            "TP3: 数组初始化器内拼接污点应报出（污点经数组传播到构造器）"
        )
        assert self._line_of("ProcessBuilder pb = new ProcessBuilder(arrCmd);") in lines, (
            "TP4: 污点数组变量传 ProcessBuilder 应报出"
        )
        assert self._line_of("ProcessBuilder hostBuilder = new ProcessBuilder(cmdList);") in lines, (
            "TP5: header 污点拼接应报出"
        )

    def test_sanitizer_and_true_negatives(self, tmp_path):
        """cmdFilter 净化；常量命令（含 main 方法）TN"""
        lines = self._lines(tmp_path)
        assert self._line_of("String clean = SecurityUtil.cmdFilter(filepath);") not in lines, (
            "TN1: cmdFilter 约定式净化后不应报"
        )
        assert self._line_of('Runtime.getRuntime().exec("touch /tmp/x");') not in lines, (
            "TN2: 常量命令无污点源不应报"
        )
        assert self._line_of('ProcessBuilder pb = new ProcessBuilder("ls", "-la");') not in lines, (
            "TN2: 常量参数 ProcessBuilder 不应报"
        )

    def test_rule_structure(self):
        """DSL 构建：三形态 sink 与净化器正确生成"""
        engine = RuleEngine(
            str(_SPECS_DIR),
            {"specs": [{"path": "command-injection.md", "enabled": True}]},
        )
        rules = engine._rules_to_semgrep()
        taint = next(
            r for r in rules["rules"] if r["id"] == "cmdi-taint"
        )
        sink_texts = [s["pattern"] for s in taint["pattern-sinks"]]
        assert "(Runtime $R).exec(...)" in sink_texts, (
            "缺少类型化 sink（简单名形式——java.lang 隐式导入不做全限定解析）"
        )
        assert "Runtime.getRuntime().exec(...)" in sink_texts, "缺少链式 sink"
        assert "new ProcessBuilder(...)" in sink_texts, "缺少 ProcessBuilder sink"
        san = [s["pattern"] for s in taint.get("pattern-sanitizers", [])]
        assert "$X.cmdFilter(...)" in san, (
            "缺少 cmdFilter 净化器（须带 receiver 元变量匹配静态调用）"
        )
