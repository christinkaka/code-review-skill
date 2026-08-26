"""表达式注入 taint 规则真实 semgrep 端到端集成测试

覆盖 expression-injection.md 三条规则（2026-08-26 新增，盲测缺口实证驱动：
java-sec-code QLExpress vuln1 真实 RCE 此前零规则检出）：
- spel-taint：双 sink（类型化 Expression + 链式 parseExpression），
  SimpleEvaluationContext 加固排除，cookie.getValue() 误报收窄
- qlexpress-taint：类型化 ExpressRunner.execute + 全局安全策略豁免
- script-engine-taint：ScriptEngine.eval / GroovyShell.evaluate

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

_EXPR_JAVA = """import com.ql.util.express.ExpressRunner;
import com.ql.util.express.config.QLExpressRunStrategy;
import groovy.lang.GroovyShell;
import javax.servlet.http.Cookie;
import javax.servlet.http.HttpServletRequest;
import javax.script.Bindings;
import javax.script.ScriptContext;
import javax.script.ScriptEngine;
import javax.script.ScriptEngineManager;
import org.springframework.expression.Expression;
import org.springframework.expression.spel.standard.SpelExpressionParser;
import org.springframework.expression.spel.support.SimpleEvaluationContext;
import org.springframework.expression.spel.support.StandardEvaluationContext;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;

class ExprCases {

    // TP1: SpEL 链式 parseExpression(value).getValue()（java-sec-code vuln1）
    @GetMapping("/spel/vuln1")
    String spelVuln1(@RequestParam String value) {
        SpelExpressionParser parser = new SpelExpressionParser();
        return parser.parseExpression(value).getValue().toString();
    }

    // TP2: SpEL getValue(StandardEvaluationContext)（java-sec-code vuln2）
    @GetMapping("/spel/vuln2")
    String spelVuln2(@RequestParam String value) {
        StandardEvaluationContext context = new StandardEvaluationContext();
        Expression expression = new SpelExpressionParser().parseExpression(value);
        Object x = expression.getValue(context);
        return x.toString();
    }

    // TN1: getValue(SimpleEvaluationContext) 加固（java-sec-code sec）
    @GetMapping("/spel/sec")
    String spelSec(@RequestParam String value) {
        SimpleEvaluationContext context =
            SimpleEvaluationContext.forReadOnlyDataBinding().build();
        Expression expression = new SpelExpressionParser().parseExpression(value);
        Object x = expression.getValue(context);
        return x.toString();
    }

    // TN2: cookie.getValue() 是 Cookie 取值，非 SpEL 求值
    // （java-sec-code Cookies/Deserialize/Shiro 实测 6 处误命中过宽 sink）
    @GetMapping("/cookie")
    String cookieValue(HttpServletRequest req) {
        Cookie[] cookies = req.getCookies();
        if (cookies != null) {
            for (Cookie cookie : cookies) {
                String nick = cookie.getValue();
                if (nick != null) {
                    return "Cookie: " + nick;
                }
            }
        }
        return "none";
    }

    // TN3: parseExpression 只解析不求值，无执行点
    @GetMapping("/spel/parseonly")
    String parseOnly(@RequestParam String value) {
        Expression expression = new SpelExpressionParser().parseExpression(value);
        return expression.getExpressionString();
    }

    // TP3: QLExpress 污点流入 execute（java-sec-code vuln1）
    @GetMapping("/ql/vuln1")
    String qlVuln1(@RequestParam String input) throws Exception {
        ExpressRunner runner = new ExpressRunner();
        Object r = runner.execute(input, null, null, true, false);
        return r.toString();
    }

    // TN4: setForbidInvokeSecurityRiskMethods 全局加固（java-sec-code sec）
    @GetMapping("/ql/sec")
    String qlSec(@RequestParam String input) throws Exception {
        QLExpressRunStrategy.setForbidInvokeSecurityRiskMethods(true);
        ExpressRunner runner = new ExpressRunner();
        Object r = runner.execute(input, null, null, true, false);
        return r.toString();
    }

    // TP4: ScriptEngine.eval，污点经 String.format 传播（java-sec-code jscmd）
    @GetMapping("/rce/jscmd")
    void jsEngine(@RequestParam String jsurl) throws Exception {
        ScriptEngine engine = new ScriptEngineManager().getEngineByName("js");
        Bindings bindings = engine.getBindings(ScriptContext.ENGINE_SCOPE);
        String cmd = String.format("load(\\"%s\\")", jsurl);
        engine.eval(cmd, bindings);
    }

    // TP5: GroovyShell.evaluate（java-sec-code groovyshell）
    @GetMapping("/rce/groovy")
    void groovyshell(@RequestParam String content) {
        GroovyShell groovyShell = new GroovyShell();
        groovyShell.evaluate(content);
    }

    // TN5: 常量脚本无污点源
    @GetMapping("/rce/const")
    void constEval() throws Exception {
        ScriptEngine engine = new ScriptEngineManager().getEngineByName("js");
        engine.eval("print('hello')");
    }

    // TN6: ExecutorService.execute 是线程池提交，非表达式执行
    // （类型化 sink 验证；sqli-taint 类型化教训的同型防护）
    @GetMapping("/rce/pool")
    void poolExecute(@RequestParam String input) {
        java.util.concurrent.ExecutorService pool =
            java.util.concurrent.Executors.newFixedThreadPool(2);
        pool.execute(() -> System.out.println(input));
    }
}
"""


class TestExpressionInjectionE2E:
    def _scan(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "ExprCases.java").write_text(_EXPR_JAVA, encoding="utf-8")
        engine = RuleEngine(
            str(_SPECS_DIR),
            {"specs": [{"path": "expression-injection.md", "enabled": True}]},
        )
        return engine.run(str(repo), [{"path": "ExprCases.java"}])

    @staticmethod
    def _line_of(marker: str) -> int:
        return next(
            n for n, t in enumerate(_EXPR_JAVA.split("\n"), 1) if marker in t
        )

    def test_spel_taint_tp_and_tn(self, tmp_path):
        """SpEL：链式/变量双 TP；Simple 加固、cookie 取值、只解析三 TN"""
        issues = self._scan(tmp_path)
        lines = {
            i["line"] for i in issues
            if "spel-taint" in str(i.get("rule_id"))
        }
        # marker 需含 return 前缀：行 19 注释含同样字样，会抢先命中
        assert self._line_of("return parser.parseExpression(value).getValue()") in lines, (
            "TP1: 链式 parseExpression(value).getValue() 应报出"
        )
        assert self._line_of("expression.getValue(context)") in lines, (
            "TP2: getValue(StandardEvaluationContext) 应报出"
        )
        # spel_sec 与 spel_vuln2 的 getValue 行文本相同，按方法区间区分：
        # sec 的 getValue 行号 > vuln2 的行号且仅差 11 行（方法结构对称）
        vuln2_line = self._line_of("expression.getValue(context)")
        sec_line = next(
            n for n, t in enumerate(_EXPR_JAVA.split("\n"), 1)
            if "expression.getValue(context)" in t and n > vuln2_line
        )
        assert sec_line not in lines, (
            "TN1: getValue(SimpleEvaluationContext) 加固后不应报"
        )
        assert self._line_of("cookie.getValue()") not in lines, (
            "TN2: cookie.getValue() 是 Cookie 取值，不应命中 SpEL sink"
        )
        assert self._line_of("getExpressionString()") not in lines, (
            "TN3: 只解析不求值，无执行点不应报"
        )

    def test_qlexpress_taint_tp_and_tn(self, tmp_path):
        """QLExpress：类型化 execute TP；全局策略豁免 TN"""
        issues = self._scan(tmp_path)
        lines = {
            i["line"] for i in issues
            if "qlexpress-taint" in str(i.get("rule_id"))
        }
        assert self._line_of("runner.execute(input") in lines, (
            "TP3: 污点流入 ExpressRunner.execute 应报出"
        )
        sec_exec = next(
            n for n, t in enumerate(_EXPR_JAVA.split("\n"), 1)
            if "runner.execute(input" in t and n > self._line_of("runner.execute(input")
        )
        assert sec_exec not in lines, (
            "TN4: setForbidInvokeSecurityRiskMethods 加固后不应报"
        )

    def test_script_engine_taint_tp_and_tn(self, tmp_path):
        """脚本引擎：eval/evaluate 双 TP；常量与线程池 TN"""
        issues = self._scan(tmp_path)
        lines = {
            i["line"] for i in issues
            if "script-engine-taint" in str(i.get("rule_id"))
        }
        assert self._line_of("engine.eval(cmd, bindings)") in lines, (
            "TP4: 污点经 String.format 传播流入 eval 应报出"
        )
        assert self._line_of("groovyShell.evaluate(content)") in lines, (
            "TP5: GroovyShell.evaluate 污点应报出"
        )
        assert self._line_of("engine.eval(\"print('hello')\")") not in lines, (
            "TN5: 常量脚本无污点源不应报"
        )
        assert self._line_of("pool.execute(") not in lines, (
            "TN6: ExecutorService.execute 是线程池提交，不应命中"
        )

    def test_sink_exclusion_dsl_blocks_parsed(self):
        """DSL 扩展回归：pattern-sinks-not / pattern-sinks-not-inside 块
        经引擎构建后成为 sink 复合排除（semgrep pattern-not/-not-inside）。
        """
        engine = RuleEngine(
            str(_SPECS_DIR),
            {"specs": [{"path": "expression-injection.md", "enabled": True}]},
        )
        rules = engine._rules_to_semgrep()
        by_id = {r["id"]: r for r in rules["rules"]}

        spel = by_id.get("spel-taint")
        assert spel, "spel-taint 规则未生成"
        nots = [
            p for s in spel["pattern-sinks"] for p in s.get("patterns", [])
            if "pattern-not" in p
        ]
        assert any("SimpleEvaluationContext" in p["pattern-not"] for p in nots), (
            "pattern-sinks-not 应复合为 sink 的 pattern-not 排除"
        )

        ql = by_id.get("qlexpress-taint")
        assert ql, "qlexpress-taint 规则未生成"
        not_insides = [
            p for s in ql["pattern-sinks"] for p in s.get("patterns", [])
            if "pattern-not-inside" in p
        ]
        assert any(
            "setForbidInvokeSecurityRiskMethods" in p["pattern-not-inside"]
            for p in not_insides
        ), "pattern-sinks-not-inside 应复合为 sink 的 pattern-not-inside 豁免"
