"""自然语言规约 → taint 规则编译链路测试（2026-08-25）

验证"人只写自然语言"前提的完整闭环：
1. 检测方式声明数据流追踪 → 走 taint 编译分支
2. LLM 生成 sources/sinks/sanitizers，golden test 真实 semgrep 验证
3. LLM 不可用/输出垃圾 → 诚实失败（空规则 + validation=failed），不启发式伪装
4. 审批后引擎通过 .md → compiled/*.approved.yaml 回退加载 taint 规则
5. 引擎侧外部 taint YAML → mode: taint 规则重建
"""

import shutil
import textwrap
from pathlib import Path

import pytest
import yaml

from rule_compiler import RuleCompiler
from rule_engine import RuleEngine
from rule_sandbox import RuleSandbox

from test_rule_compiler_llm import FakeLLMClient

REPO_ROOT = Path(__file__).parent.parent
NL_SPEC = REPO_ROOT / "references" / "security" / "path-traversal-natural-language.md"

# 与 PoC 验证过的等价 taint 规则（golden test 依赖真实 semgrep）
_TAINT_YAML_RESPONSE = """```yaml
pattern-sources:
  - pattern: $REQ.getParameter(...)
pattern-sinks:
  - pattern: new File(...)
pattern-sanitizers:
  - pattern: $F.getName()
```"""


def _make_compiler(tmp_path, llm):
    specs = tmp_path / "specs"
    specs.mkdir(parents=True, exist_ok=True)
    return RuleCompiler(str(specs), llm_client=llm)


class TestDetectionTypeInference:
    def test_taint_keywords(self):
        assert RuleCompiler._is_taint_detection("数据流追踪（污点分析）")
        assert RuleCompiler._is_taint_detection("taint mode")
        assert RuleCompiler._is_taint_detection("Data Flow analysis")

    def test_non_taint(self):
        assert not RuleCompiler._is_taint_detection("模式匹配")
        assert not RuleCompiler._is_taint_detection("")


class TestTaintGeneration:
    def test_llm_generates_taint_rule(self, tmp_path):
        llm = FakeLLMClient(responses=[_TAINT_YAML_RESPONSE])
        compiler = _make_compiler(tmp_path, llm)

        rule = compiler._generate_semgrep_rule_with_ai(
            metadata={"title": "Path traversal", "severity": "ERROR",
                      "languages": ["java"]},
            violation_scenario="用户输入流入文件操作",
            safe_approach="basename 净化",
            bad_example="new File(request.getParameter(\"p\"));",
            good_example="new File(new File(p).getName());",
            detection_type="taint",
        )

        assert len(rule["rules"]) == 1
        r = rule["rules"][0]
        assert r["mode"] == "taint"
        assert r["metadata"]["generation_method"] == "ai"
        assert r["metadata"]["detection_type"] == "taint"
        assert r["pattern-sources"] == [{"pattern": "$REQ.getParameter(...)"}]
        assert r["pattern-sanitizers"] == [{"pattern": "$F.getName()"}]
        # prompt 要求生成 taint 三要素
        assert "pattern-sources" in llm.calls[0]["prompt"]

    def test_llm_unavailable_returns_empty(self, tmp_path):
        """taint 无启发式降级：LLM 不可用 → 空规则（调用方拒绝部署）"""
        compiler = _make_compiler(tmp_path, FakeLLMClient(available=False))

        rule = compiler._generate_semgrep_rule_with_ai(
            metadata={"title": "T", "languages": ["java"]},
            violation_scenario="", safe_approach="",
            bad_example="", good_example="",
            detection_type="taint",
        )
        assert rule == {"rules": []}

    def test_llm_garbage_returns_empty(self, tmp_path):
        compiler = _make_compiler(
            tmp_path, FakeLLMClient(responses=["我不明白你的需求"])
        )
        rule = compiler._generate_semgrep_rule_with_ai(
            metadata={"title": "T", "languages": ["java"]},
            violation_scenario="", safe_approach="",
            bad_example="", good_example="",
            detection_type="taint",
        )
        assert rule == {"rules": []}

    def test_parse_taint_response_variants(self):
        parse = RuleCompiler._parse_taint_response
        # 纯字符串条目
        spec = parse("pattern-sources:\n  - $REQ.getParameter(...)\n"
                     "pattern-sinks:\n  - new File(...)")
        assert spec["pattern-sources"] == [{"pattern": "$REQ.getParameter(...)"}]
        assert "pattern-sanitizers" not in spec
        # 缺 sinks → None
        assert parse("pattern-sources:\n  - $X") is None
        assert parse("随便说说") is None
        assert parse("") is None


class TestRuleIdGeneration:
    def test_english_title(self):
        assert RuleCompiler._make_rule_id("Path Traversal Rules") == "path-traversal-rules"

    def test_chinese_title_falls_back_to_hash(self):
        rule_id = RuleCompiler._make_rule_id("用户输入流入文件路径操作")
        assert rule_id.startswith("rule-")
        assert len(rule_id) == len("rule-") + 8


class TestSeverityAlignment:
    """VALID_SEVERITIES 与 scan.py 分层评审口径对齐"""

    @pytest.mark.parametrize("severity", ["CRITICAL", "HIGH", "ERROR", "WARNING", "INFO"])
    def test_standard_severities_accepted(self, severity):
        rule = {"id": "r", "languages": ["java"], "severity": severity,
                "pattern": "eval($X)"}
        valid, reason = RuleSandbox.validate_structure(rule)
        assert valid, reason

    def test_bogus_severity_rejected(self):
        rule = {"id": "r", "languages": ["java"], "severity": "BOGUS",
                "pattern": "eval($X)"}
        valid, _ = RuleSandbox.validate_structure(rule)
        assert not valid


class TestEngineExternalTaintYaml:
    def _taint_yaml(self, tmp_path):
        f = tmp_path / "taint.yaml"
        f.write_text(yaml.dump({
            "rules": [{
                "id": "ext-taint", "mode": "taint", "severity": "CRITICAL",
                "languages": ["java"], "message": "ext",
                "pattern-sources": [{"pattern": "$REQ.getParameter(...)"}],
                "pattern-sinks": [{"pattern": "new File(...)"},
                                  {"pattern": "Paths.get(...)"}],
                "pattern-sanitizers": [{"pattern": "$F.getName()"}],
            }]
        }), encoding="utf-8")
        return f

    def test_load_yaml_rules_builds_taint_structure(self, tmp_path):
        engine = RuleEngine.__new__(RuleEngine)
        engine.rules = engine._load_yaml_rules(str(self._taint_yaml(tmp_path)))

        assert len(engine.rules) == 1
        r = engine.rules[0]
        assert r["taint"]["sources"] == [{"content": "$REQ.getParameter(...)"}]
        assert len(r["taint"]["sinks"]) == 2
        assert r["taint"]["sanitizers"] == [{"content": "$F.getName()"}]

        built = engine._rules_to_semgrep()
        assert built["rules"][0]["mode"] == "taint"
        assert built["rules"][0]["pattern-sinks"][1] == {"pattern": "Paths.get(...)"}

    def test_incomplete_taint_yaml_rejected(self, tmp_path):
        """只有 sources 没有 sinks 的 taint 规则不进引擎"""
        f = tmp_path / "broken.yaml"
        f.write_text(yaml.dump({
            "rules": [{
                "id": "broken", "mode": "taint", "languages": ["java"],
                "pattern-sources": [{"pattern": "$X"}],
            }]
        }), encoding="utf-8")
        engine = RuleEngine.__new__(RuleEngine)
        rules = engine._load_yaml_rules(str(f))
        assert rules == [] or "taint" not in rules[0]


_NL_MD = NL_SPEC.read_text(encoding="utf-8")


class TestNaturalLanguageCompileToDeploy:
    """全链路：自然语言 md → FakeLLM 编译 → golden test → 审批 → 引擎消费

    golden test 与引擎扫描依赖真实 semgrep。
    """

    @pytest.fixture
    def specs_dir(self, tmp_path):
        (tmp_path / "path-traversal-natural-language.md").write_text(
            _NL_MD, encoding="utf-8"
        )
        return tmp_path

    @pytest.mark.skipif(shutil.which("semgrep") is None, reason="未安装 semgrep")
    def test_compile_approve_and_engine_consume(self, specs_dir):
        # 1. 编译（FakeLLM 提供已知有效的 taint 规则）
        compiler = RuleCompiler(
            str(specs_dir), llm_client=FakeLLMClient(responses=[_TAINT_YAML_RESPONSE])
        )
        result = compiler.compile_rule(
            specs_dir / "path-traversal-natural-language.md", force=True
        )
        assert result["status"] == "compiled"
        assert result["validation"]["status"] == "passed", result["validation"]

        compiled = specs_dir / "compiled" / "path-traversal-natural-language.yaml"
        rule = yaml.safe_load(compiled.read_text(encoding="utf-8"))["rules"][0]
        assert rule["mode"] == "taint"
        assert rule["metadata"]["generation_method"] == "ai"

        # 2. 审批部署（auto_approve 仅测试用；人工闸门见 approve 流程）
        deploy = compiler.approve_and_deploy(compiled, auto_approve=True)
        assert deploy["status"] == "approved"
        approved = specs_dir / "compiled" / "path-traversal-natural-language.approved.yaml"
        assert approved.exists()

        # 3. 引擎通过 .md → approved 回退加载 taint 规则
        engine = RuleEngine(
            str(specs_dir),
            {"specs": [{"path": "path-traversal-natural-language.md", "enabled": True}]},
        )
        taint_rules = [r for r in engine.rules if r.get("taint")]
        assert len(taint_rules) == 1, "自然语言规约的编译产物应被引擎加载"

        # 4. 真实扫描：真阳性报出、常量拼接不误报
        repo = specs_dir / "repo"
        repo.mkdir()
        (repo / "Upload.java").write_text(textwrap.dedent("""\
            import java.io.File;
            import java.nio.file.Files;
            import javax.servlet.http.HttpServletRequest;

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
            }
        """), encoding="utf-8")

        issues = engine.run(str(repo), [{"path": "Upload.java"}])
        hits = {
            i.get("line") for i in issues
            if i.get("file") == "Upload.java" and "rule-" in str(i.get("rule_id", ""))
        }
        # readUserFile 内（7-9 行附近）报出，readConstFile（13-15 行）不报
        assert any(7 <= l <= 10 for l in hits), f"真阳性未报出: {hits}"
        assert not any(12 <= l <= 16 for l in hits), f"常量拼接误报: {hits}"

    @pytest.mark.skipif(shutil.which("semgrep") is None, reason="未安装 semgrep")
    def test_llm_unavailable_taint_not_deployable(self, specs_dir):
        """LLM 不可用：taint 规则编译失败，审批被闸门拒绝"""
        compiler = RuleCompiler(
            str(specs_dir), llm_client=FakeLLMClient(available=False)
        )
        result = compiler.compile_rule(
            specs_dir / "path-traversal-natural-language.md", force=True
        )
        assert result["status"] == "compiled"
        assert result["validation"]["status"] == "failed"
        assert result["validation"]["reason"] == "rule_generation_failed"
        assert result["validation"]["pass_rate"] == 0.0

        compiled = specs_dir / "compiled" / "path-traversal-natural-language.yaml"
        deploy = compiler.approve_and_deploy(compiled, auto_approve=True)
        assert deploy["status"] == "refused"
