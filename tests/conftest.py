#!/usr/bin/env python3
"""
测试辅助模块 - pytest fixtures 和工具函数
提供 mock_semgrep、mock_llm_api、mock_webhook 等 fixture，
以及测试数据加载器和辅助构造函数。
"""

import json
import os
import re
import shutil
import tempfile
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest
import yaml

# ============================================================
# 路径常量
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
REFERENCES_DIR = PROJECT_ROOT / "references"
TEST_CASES_DIR = REFERENCES_DIR / "test-cases"

# 将 scripts 目录加入 Python 路径
import sys
sys.path.insert(0, str(SCRIPTS_DIR))


# ============================================================
# 测试数据加载器
# ============================================================
class TestDataLoader:
    """测试数据加载器，从 references 目录加载规约和测试案例"""

    def __init__(self, references_dir: str = None):
        self.references_dir = Path(references_dir or REFERENCES_DIR)
        self.test_cases_dir = self.references_dir / "test-cases"

    def load_profile(self, profile_name: str = "default") -> Dict:
        """加载指定的 profile 配置"""
        profile_path = self.references_dir / "profiles" / f"{profile_name}.yaml"
        with open(profile_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def load_spec_file(self, relative_path: str) -> str:
        """加载规约文件内容"""
        file_path = self.references_dir / relative_path
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def load_test_case(self, category: str, filename: str) -> str:
        """加载测试案例文件内容"""
        file_path = self.test_cases_dir / category / filename
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def extract_code_blocks(self, md_content: str, language: str = None) -> List[Dict]:
        """
        从 Markdown 内容中提取代码块

        Returns:
            [{"language": str, "code": str, "section": str}]
        """
        blocks = []
        # 匹配代码块
        pattern = r"```(\w[\w-]*)\n(.*?)```"
        for match in re.finditer(pattern, md_content, re.DOTALL):
            lang = match.group(1).strip().lower()
            code = match.group(2).strip()
            if language is None or lang == language:
                blocks.append({"language": lang, "code": code})
        return blocks

    def extract_test_cases_from_md(self, md_content: str) -> List[Dict]:
        """
        从测试案例 Markdown 中提取违规/正确代码及其预期命中规则

        Returns:
            [{"type": "violation"|"correct", "code": str, "language": str,
              "expected_rule": str|None}]
        """
        cases = []
        sections = re.split(r"\n---\n", md_content)

        for section in sections:
            section = section.strip()
            if not section:
                continue

            # 判断是违规还是正确代码
            is_violation = "违规代码" in section or "违规" in section.split("\n")[0]
            is_correct = "正确代码" in section or "正确" in section.split("\n")[0]

            if not is_violation and not is_correct:
                continue

            # 提取代码块（跳过 yaml/pattern/pattern-not 块）
            code_blocks = re.findall(
                r"```(\w[\w-]*)\n(.*?)```", section, re.DOTALL
            )
            source_blocks = [
                (lang, code.strip())
                for lang, code in code_blocks
                if lang.lower() not in ("yaml", "pattern", "pattern-not")
            ]

            # 提取预期命中规则
            expected_rule = None
            rule_match = re.search(r"预期命中[：:]\s*`?(\S+?)`?\s*$", section, re.MULTILINE)
            if rule_match:
                expected_rule = rule_match.group(1)
                if expected_rule == "无":
                    expected_rule = None

            for lang, code in source_blocks:
                cases.append({
                    "type": "violation" if is_violation else "correct",
                    "code": code,
                    "language": lang,
                    "expected_rule": expected_rule,
                })

        return cases

    def list_test_case_files(self, category: str = "security") -> List[Path]:
        """列出指定类别下的所有测试案例文件"""
        tc_dir = self.test_cases_dir / category
        if not tc_dir.exists():
            return []
        return sorted(tc_dir.glob("*-test.md"))


# ============================================================
# 测试数据构造辅助函数
# ============================================================
def build_test_issues(count: int = 10, real_count: int = 5) -> List[Dict]:
    """
    构造模拟扫描问题列表

    Args:
        count: 总问题数
        real_count: 真实问题数（前 real_count 个为真实问题）

    Returns:
        问题列表
    """
    rule_ids = [
        "xxe-java-document-builder",
        "xxe-java-sax-parser",
        "priv-python-eval",
        "priv-python-os-system",
        "xss-js-innerhtml",
        "path-python-open",
        "ssrf-python-requests",
        "sig-java-weak-algorithm",
        "sqli-java-concat",
        "auth-java-missing-check",
    ]
    severities = ["ERROR", "WARNING", "ERROR", "ERROR", "WARNING",
                  "WARNING", "ERROR", "ERROR", "ERROR", "WARNING"]
    categories = ["security"] * 10
    files = [
        "src/Parser.java", "src/SaxHandler.java", "scripts/eval.py",
        "scripts/cmd.py", "web/component.js", "utils/file.py",
        "net/client.py", "crypto/Signer.java", "db/Query.java",
        "auth/Filter.java",
    ]

    issues = []
    for i in range(count):
        idx = i % len(rule_ids)
        issues.append({
            "rule_id": rule_ids[idx],
            "category": categories[idx],
            "severity": severities[idx],
            "file": files[idx],
            "line": (i + 1) * 10,
            "end_line": (i + 1) * 10 + 5,
            "message": f"Test issue #{i + 1}: {rule_ids[idx]}",
            "code_snippet": f"// sample code for {rule_ids[idx]} line {(i + 1) * 10}",
            "fix": "",
        })

    return issues


def build_mock_ai_response(
    issues: List[Dict],
    real_indices: List[int] = None,
    confidence_map: Dict[int, float] = None,
) -> str:
    """
    构造 Mock LLM AI 评审响应 JSON

    Args:
        issues: 问题列表
        real_indices: 真实问题的索引列表（其余为误报）
        confidence_map: 指定某些索引的置信度

    Returns:
        JSON 字符串
    """
    if real_indices is None:
        real_indices = list(range(len(issues) // 2))

    results = []
    for i, issue in enumerate(issues):
        is_real = i in real_indices
        confidence = 0.9 if is_real else 0.2

        if confidence_map and i in confidence_map:
            confidence = confidence_map[i]
            is_real = confidence >= 0.7

        results.append({
            "rule_id": issue["rule_id"],
            "is_valid": is_real,
            "confidence": confidence,
            "enhanced_fix": (
                f"// Fixed code for {issue['rule_id']}\n"
                f"safeAlternative(originalInput);\n"
                if is_real else ""
            ),
        })

    return json.dumps(results, ensure_ascii=False)


def build_mock_diff_result(
    changed_files: List[str] = None,
    changed_methods: List[Dict] = None,
) -> Dict:
    """构造模拟的 diff 分析结果"""
    if changed_files is None:
        changed_files = ["src/Parser.java", "src/Handler.java"]
    if changed_methods is None:
        changed_methods = [
            {"file": "src/Parser.java", "name": "parse", "line": 10, "end_line": 30}
        ]

    return {
        "changed_files": [{"path": f, "status": "modified", "additions": 10, "deletions": 5}
                          for f in changed_files],
        "changed_methods": changed_methods,
        "diff_text": "--- a/src/Parser.java\n+++ b/src/Parser.java\n@@ -10,5 +10,5 @@",
        "stats": {
            "files_changed": len(changed_files),
            "insertions": 10 * len(changed_files),
            "deletions": 5 * len(changed_files),
        },
    }


def build_mock_call_graph() -> Dict:
    """构造模拟的调用图数据"""
    return {
        "node_count": 15,
        "edge_count": 20,
        "affected_methods": ["parse", "validate", "transform"],
        "call_chains": {
            "src/Parser.java:10": ["main", "process", "parse"],
        },
    }


# ============================================================
# Mock Webhook 服务器
# ============================================================
class MockWebhookHandler(BaseHTTPRequestHandler):
    """Mock Webhook HTTP 请求处理器"""

    received_requests = []

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        content_type = self.headers.get("Content-Type", "")

        try:
            body_json = json.loads(body.decode("utf-8")) if body else {}
        except json.JSONDecodeError:
            body_json = {"raw": body.decode("utf-8", errors="replace")}

        self.received_requests.append({
            "method": "POST",
            "path": self.path,
            "content_type": content_type,
            "headers": dict(self.headers),
            "body": body_json,
        })

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))

    def log_message(self, format, *args):
        """抑制默认日志输出"""
        pass


class MockWebhookServer:
    """Mock Webhook 服务器包装器"""

    def __init__(self, port: int = 0):
        self.server = HTTPServer(("127.0.0.1", port), MockWebhookHandler)
        self.port = self.server.server_address[1]
        self.handler = MockWebhookHandler
        self.handler.received_requests = []
        self._thread = None

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/webhook"

    @property
    def received_requests(self) -> List[Dict]:
        return self.handler.received_requests

    def start(self):
        """启动服务器（后台线程）"""
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self._thread.start()
        time.sleep(0.1)  # 等待服务器启动

    def stop(self):
        """停止服务器"""
        self.server.shutdown()
        if self._thread:
            self._thread.join(timeout=5)

    def clear(self):
        """清空已接收的请求"""
        self.handler.received_requests = []


# ============================================================
# Scheduler / Notifier / ScanRunner
# 实际模块已实现，从 scripts/ 目录导入
# ============================================================
from scheduler import Scheduler, CronExpression  # noqa: F401
from notifier import Notifier, ScanRunner  # noqa: F401


# ============================================================
# Pytest Fixtures
# ============================================================
@pytest.fixture
def test_data_loader():
    """提供测试数据加载器"""
    return TestDataLoader()


@pytest.fixture
def default_profile():
    """加载 default profile"""
    loader = TestDataLoader()
    return loader.load_profile("default")


@pytest.fixture
def mock_semgrep():
    """
    Mock Semgrep 调用 - 模拟 semgrep 命令的输出
    用于测试可离线运行，无需真实安装 Semgrep
    """
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps({"results": [], "errors": []})
    mock_result.stderr = ""

    with patch("subprocess.run") as mock_run:
        def side_effect(cmd, **kwargs):
            if isinstance(cmd, list) and cmd[0] == "semgrep":
                if "--version" in cmd:
                    result = MagicMock()
                    result.returncode = 0
                    result.stdout = "0.100.0"
                    result.stderr = ""
                    return result
                return mock_result
            # 非 semgrep 命令走真实调用
            import subprocess as real_subprocess
            return real_subprocess.run(cmd, **kwargs)

        mock_run.side_effect = side_effect
        yield mock_run, mock_result


@pytest.fixture
def mock_semgrep_with_findings():
    """
    Mock Semgrep 调用 - 返回预设的扫描结果
    """
    findings = [
        {
            "check_id": "xxe-java-document-builder",
            "path": "src/Parser.java",
            "start": {"line": 33, "col": 9},
            "end": {"line": 35, "col": 40},
            "extra": {
                "severity": "ERROR",
                "message": "DocumentBuilderFactory 未禁用外部实体",
                "lines": "DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();\nDocumentBuilder builder = factory.newDocumentBuilder();\nreturn builder.parse(inputStream);",
            },
        },
        {
            "check_id": "xxe-java-document-builder",
            "path": "src/NodeParser.java",
            "start": {"line": 33, "col": 9},
            "end": {"line": 35, "col": 40},
            "extra": {
                "severity": "ERROR",
                "message": "DocumentBuilderFactory 未禁用外部实体",
                "lines": "DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();\nDocumentBuilder builder = dbf.newDocumentBuilder();\nreturn builder.parse(input);",
            },
        },
        {
            "check_id": "xxe-java-sax-parser",
            "path": "src/SaxHandler.java",
            "start": {"line": 15, "col": 9},
            "end": {"line": 17, "col": 35},
            "extra": {
                "severity": "ERROR",
                "message": "SAXParser 未禁用外部实体",
                "lines": "SAXParserFactory factory = SAXParserFactory.newInstance();\nSAXParser parser = factory.newSAXParser();\nparser.parse(input, handler);",
            },
        },
    ]

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps({"results": findings, "errors": []})
    mock_result.stderr = ""

    with patch("subprocess.run") as mock_run:
        def side_effect(cmd, **kwargs):
            if isinstance(cmd, list) and cmd[0] == "semgrep":
                if "--version" in cmd:
                    result = MagicMock()
                    result.returncode = 0
                    result.stdout = "0.100.0"
                    result.stderr = ""
                    return result
                return mock_result
            import subprocess as real_subprocess
            return real_subprocess.run(cmd, **kwargs)

        mock_run.side_effect = side_effect
        yield mock_run, findings


@pytest.fixture
def mock_llm_api():
    """
    Mock LLM API 调用 - 返回预定义的 AI 评审结果
    用于测试可离线运行，无需真实 LLM API
    """
    def _factory(response_json: str = None, side_effect=None, latency: float = 0):
        """
        创建 Mock LLM

        Args:
            response_json: 固定的 JSON 响应字符串
            side_effect: 可调用的副作用函数(prompt) -> str
            latency: 模拟网络延迟（秒）
        """
        def mock_call_llm(self_reviewer, prompt):
            if latency > 0:
                time.sleep(latency)
            if side_effect:
                return side_effect(prompt)
            return response_json

        return mock_call_llm

    return _factory


@pytest.fixture
def mock_webhook():
    """
    Mock Webhook 服务器 - 接收并记录 Webhook 请求
    """
    server = MockWebhookServer(port=0)  # 随机端口
    server.start()
    yield server
    server.stop()


@pytest.fixture
def temp_repo():
    """
    创建临时 Git 仓库用于测试
    """
    tmpdir = tempfile.mkdtemp(prefix="test_repo_")
    repo_path = Path(tmpdir)

    # 初始化 Git 仓库（指定 master 为初始分支，兼容新旧版 Git）
    import subprocess
    subprocess.run(["git", "init", "-b", "master"], cwd=str(repo_path), capture_output=True)
    # 如果 -b 参数不被支持（老版 Git），尝试重命名分支
    subprocess.run(["git", "branch", "-M", "master"],
                    cwd=str(repo_path), capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"],
                    cwd=str(repo_path), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"],
                    cwd=str(repo_path), capture_output=True)

    # 创建初始提交
    (repo_path / "README.md").write_text("# Test Repo\n")
    subprocess.run(["git", "add", "."], cwd=str(repo_path), capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"],
                    cwd=str(repo_path), capture_output=True)

    yield repo_path

    # 清理
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def temp_dir():
    """创建临时目录，测试结束后自动清理"""
    tmpdir = tempfile.mkdtemp(prefix="test_")
    yield Path(tmpdir)
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def sample_issues():
    """提供一组标准的测试问题"""
    return build_test_issues(count=10, real_count=5)


@pytest.fixture
def sample_diff_result():
    """提供标准的 diff 结果"""
    return build_mock_diff_result()


@pytest.fixture
def sample_call_graph():
    """提供标准的调用图数据"""
    return build_mock_call_graph()


# ============================================================
# Markdown 规约文件 fixtures (UTDD)
# ============================================================

@pytest.fixture
def sample_markdown_file(tmp_path):
    """创建一个包含完整 yaml/pattern/pattern-not 代码块的 Markdown 规约文件"""
    import textwrap
    content = textwrap.dedent("""\
        # XXE - DocumentBuilderFactory 未禁用外部实体

        > XML 解析器未禁用外部实体，攻击者可通过构造恶意 XML 读取服务器文件。

        ```yaml
        id: xxe-java-document-builder
        languages: [java]
        severity: ERROR
        cwe: CWE-611
        owasp: A05:2021
        ```

        ## 检测模式

        ```pattern
        DocumentBuilderFactory $factory = DocumentBuilderFactory.newInstance();
        ...
        $factory.parse(...);
        ```

        ```pattern-not
        DocumentBuilderFactory $factory = DocumentBuilderFactory.newInstance();
        ...
        $factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        ...
        $factory.parse(...);
        ```

        ---

        # XXE - SAXParser 未禁用外部实体

        > SAXParser 未禁用外部实体，存在 XXE 风险。

        ```yaml
        id: xxe-java-sax-parser
        languages: [java]
        severity: ERROR
        cwe: CWE-611
        ```

        ## 检测模式

        ```pattern
        SAXParserFactory $factory = SAXParserFactory.newInstance();
        ...
        $factory.newSAXParser().parse(...);
        ```
    """)
    md_file = tmp_path / "xxe.md"
    md_file.write_text(content, encoding="utf-8")
    return str(md_file)


@pytest.fixture
def markdown_no_yaml_block(tmp_path):
    """创建一个缺少 yaml 代码块的 Markdown 文件"""
    import textwrap
    content = textwrap.dedent("""\
        # 某规则

        > 这是一个没有 yaml 元数据的规则。

        ```pattern
        some_code($X);
        ```
    """)
    md_file = tmp_path / "no_yaml.md"
    md_file.write_text(content, encoding="utf-8")
    return str(md_file)


@pytest.fixture
def markdown_no_pattern_block(tmp_path):
    """创建一个缺少 pattern 代码块的 Markdown 文件"""
    import textwrap
    content = textwrap.dedent("""\
        # 某规则

        > 这是一个没有 pattern 的规则。

        ```yaml
        id: no-pattern-rule
        languages: [java]
        severity: WARNING
        ```
    """)
    md_file = tmp_path / "no_pattern.md"
    md_file.write_text(content, encoding="utf-8")
    return str(md_file)


@pytest.fixture
def markdown_multiple_patterns(tmp_path):
    """创建一个包含多个 pattern 代码块的 Markdown 文件"""
    import textwrap
    content = textwrap.dedent("""\
        # 多模式规则

        > 包含多个检测模式。

        ```yaml
        id: multi-pattern-rule
        languages: [python]
        severity: WARNING
        ```

        ```pattern
        eval($X)
        ```

        ```pattern
        exec($X)
        ```

        ```pattern-not
        eval("safe_literal")
        ```
    """)
    md_file = tmp_path / "multi_pattern.md"
    md_file.write_text(content, encoding="utf-8")
    return str(md_file)


@pytest.fixture
def markdown_empty_file(tmp_path):
    """创建一个空的 Markdown 文件"""
    md_file = tmp_path / "empty.md"
    md_file.write_text("", encoding="utf-8")
    return str(md_file)


@pytest.fixture
def markdown_malformed(tmp_path):
    """创建一个格式错误的 Markdown 文件"""
    import textwrap
    content = textwrap.dedent("""\
        # 格式错误的规则

        ```yaml
        id: malformed-rule
        languages: [java
        severity: ERROR
        ```

        ```pattern
        unclosed_pattern($X
        ```

        ```
        not a valid code block type
        ```
    """)
    md_file = tmp_path / "malformed.md"
    md_file.write_text(content, encoding="utf-8")
    return str(md_file)


# ============================================================
# Semgrep 输出 fixtures (UTDD)
# ============================================================

@pytest.fixture
def sample_semgrep_json():
    """模拟 Semgrep JSON 输出"""
    return {
        "results": [
            {
                "check_id": "xxe-java-document-builder",
                "path": "src/main/java/com/example/Parser.java",
                "start": {"line": 42, "col": 9},
                "end": {"line": 45, "col": 40},
                "extra": {
                    "message": "XXE vulnerability: DocumentBuilderFactory not secured",
                    "severity": "ERROR",
                    "lines": "DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();\n",
                    "metadata": {"cwe": "CWE-611"},
                },
            },
            {
                "check_id": "xxe-java-sax-parser",
                "path": "src/main/java/com/example/XmlHandler.java",
                "start": {"line": 18, "col": 5},
                "end": {"line": 20, "col": 45},
                "extra": {
                    "message": "XXE vulnerability: SAXParser not secured",
                    "severity": "ERROR",
                    "lines": "SAXParserFactory factory = SAXParserFactory.newInstance();\n",
                    "metadata": {"cwe": "CWE-611"},
                },
            },
        ],
        "errors": [],
    }


@pytest.fixture
def sample_ai_response():
    """模拟 AI 评审 JSON 响应"""
    return json.dumps([
        {
            "rule_id": "xxe-java-document-builder",
            "is_valid": True,
            "confidence": 0.95,
            "enhanced_fix": "在创建 DocumentBuilder 前调用 factory.setFeature 禁用 DTD",
        },
        {
            "rule_id": "naming-convention",
            "is_valid": False,
            "confidence": 0.3,
            "enhanced_fix": "",
        },
    ], ensure_ascii=False)
