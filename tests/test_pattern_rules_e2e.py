"""pattern 规则真实 semgrep 端到端集成测试

依赖本机 semgrep（与 TestRealSemgrepSandbox 同级约定）。

背景（2026-08-26）：两条规则因 semgrep rc=2 解析失败静默失效——
- ssrf-deep-detection__python：Java 语法 pattern 无语言标签落入 Python 变体
- xxe-deep-detection__java：缺分号的语句序列 pattern-not 无法解析
（即使可解析，pattern-not 范围语义也永远不命中，正确算子是 pattern-not-inside）
本文件固化复活后的 TP/TN 行为，以及全量规则可解析性回归（rc=2 静默失效防护）。
"""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from rule_engine import RuleEngine

pytestmark = pytest.mark.skipif(
    shutil.which("semgrep") is None, reason="本机未安装 semgrep"
)

_SPECS_DIR = Path(__file__).parent.parent / "references" / "security"


def _scan(tmp_path, filename, source):
    repo = tmp_path / "repo"
    repo.mkdir(exist_ok=True)
    (repo / filename).write_text(source, encoding="utf-8")
    engine = RuleEngine(
        str(_SPECS_DIR), {"specs": [{"path": "deserialization.md", "enabled": True}]}
    )
    return engine.run(str(repo), [{"path": filename}])


def _lines(issues, rule_prefix):
    return {
        i.get("line")
        for i in issues
        if rule_prefix in str(i.get("rule_id"))
    }


_XXE_JAVA = """import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.XMLConstants;

class XxeCases {
    void unhardened(String xml) throws Exception {
        DocumentBuilderFactory f = DocumentBuilderFactory.newInstance();
        f.newDocumentBuilder().parse(xml);
    }

    void hardenedDoctype(String xml) throws Exception {
        DocumentBuilderFactory f = DocumentBuilderFactory.newInstance();
        f.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        f.newDocumentBuilder().parse(xml);
    }

    void hardenedSecureQualified(String xml) throws Exception {
        DocumentBuilderFactory f = DocumentBuilderFactory.newInstance();
        f.setFeature(javax.xml.XMLConstants.FEATURE_SECURE_PROCESSING, true);
        f.newDocumentBuilder().parse(xml);
    }

    void hardenedSecureImported(String xml) throws Exception {
        DocumentBuilderFactory f = DocumentBuilderFactory.newInstance();
        f.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
        f.newDocumentBuilder().parse(xml);
    }
}
"""


class TestXxeDeepDetectionE2E:
    def test_unhardened_flagged_hardened_exempted(self, tmp_path):
        """未加固工厂报出；三种 OWASP 推荐加固写法豁免（pattern-not-inside）"""
        lines = _lines(_scan(tmp_path, "XxeCases.java", _XXE_JAVA), "xxe-deep-detection")
        assert 6 in lines, "未加固的 DocumentBuilderFactory.newInstance() 应报出"
        assert 11 not in lines, "disallow-doctype-decl 加固后不应报"
        assert 16 not in lines, "全限定名 FEATURE_SECURE_PROCESSING 加固后不应报"
        assert 21 not in lines, "import 形式 FEATURE_SECURE_PROCESSING 加固后不应报"


_SSRF_JAVA = """import java.net.HttpURLConnection;
import java.net.URL;

class SsrfCases {
    void vulnerable(String url) throws Exception {
        Object c = new URL(url).openConnection();
    }

    void constant() throws Exception {
        Object c = new URL("https://api.example.com/health").openConnection();
    }
}
"""

_SSRF_PY = """import requests


def fetch_url(url):
    return requests.get(url)


def fetch_const():
    return requests.get("https://api.example.com/health")


def fetch_template(path):
    return requests.get(f"https://api.example.com{path}")
"""


class TestSsrfDeepDetectionE2E:
    def test_java_inline_chain_tp_and_constant_tn(self, tmp_path):
        """Java 内联链式用户 URL 报出；常量 URL 排除（2026-08-26 修正二）"""
        lines = _lines(_scan(tmp_path, "SsrfCases.java", _SSRF_JAVA), "ssrf-deep-detection")
        assert 6 in lines, "用户可控 URL 内联 openConnection 应报出"
        assert 10 not in lines, "常量 URL 直连不应报"

    def test_python_variant_revived_tp_and_constant_tn(self, tmp_path):
        """Python 变体复活：用户 URL 报出、常量排除、f-string 拼接仍报出"""
        lines = _lines(_scan(tmp_path, "ssrf_app.py", _SSRF_PY), "ssrf-deep-detection")
        assert 5 in lines, "requests.get(用户URL) 应报出（此前整条规则解析失效）"
        assert 9 not in lines, "requests.get(常量URL) 不应报（$USER_INPUT 匹配任意表达式）"
        assert 13 in lines, "f-string 拼接 URL 应报出（非字符串字面量）"


class TestAllRulesParseable:
    def test_security_rules_no_semgrep_parse_errors(self, tmp_path):
        """全量 security 规约经引擎生成后必须全部可被 semgrep 解析。

        rc=2 解析失败会导致整条规则静默失效（2026-08-26 曾有 2 条），
        且每次扫描都输出"Semgrep 异常退出"噪声。以真实扫描路径断言
        errors 为空作回归防护。
        """
        engine = RuleEngine(
            str(_SPECS_DIR), {"specs": [{"path": "*.md", "enabled": True}]}
        )
        rules = engine._rules_to_semgrep()
        assert rules["rules"], "规则生成结果为空"

        with tempfile.NamedTemporaryFile(
            "w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            json.dump(rules, f, ensure_ascii=False)
            rules_file = f.name

        fixture = tmp_path / "repo"
        fixture.mkdir()
        (fixture / "Sample.java").write_text(
            "class Sample { int x = 1; }\n", encoding="utf-8"
        )
        try:
            proc = subprocess.run(
                [
                    "semgrep", "--config", rules_file,
                    "--json", str(fixture),
                ],
                capture_output=True, text=True, timeout=300,
            )
        finally:
            Path(rules_file).unlink(missing_ok=True)

        data = json.loads(proc.stdout)
        assert not data.get("errors"), (
            "存在 semgrep 解析失败的规则（将静默失效）: "
            f"{[e.get('message', '')[:150] for e in data['errors']]}"
        )
