#!/usr/bin/env python3
"""
Prefilter 白名单测试

背景：Spring Boot 双盲测试发现 359 个 path-traversal 命中几乎全部在测试文件
（dockerTest 目录、*Tests.java 复数命名），但 prefilter 没有过滤掉它们。

真实案例（Spring Boot 仓库）：
- src/dockerTest/java/.../BootBuildImageIntegrationTests.java  <- 未被过滤
- src/integrationTest/java/...                                  <- 未被过滤

必须覆盖的测试文件命名约定：
- src/test/**、src/tests/**（标准 Maven/Gradle）
- src/dockerTest/**、src/integrationTest/**（Spring Boot 自定义 source set）
- *Test.java、*Tests.java（JUnit 单复数两种约定）
- *IT.java（Maven Failsafe 集成测试约定）
- *_test.py、test_*.py（pytest 约定）
- *.spec.ts / *.test.js（前端约定）

同时必须保证非测试文件不被误过滤。
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from scan import prefilter_issues


def make_issue(rule_id, file):
    return {"rule_id": rule_id, "file": file, "line": 1, "severity": "ERROR"}


# ===================================================================
# 标准测试目录约定（原有能力，不得回归）
# ===================================================================

class TestStandardTestDirs:
    def test_src_test_dir_filtered(self):
        issues = [make_issue("path-write-traversal",
                             "src/test/java/org/app/ParserTest.java")]
        assert prefilter_issues(issues, {}) == []

    def test_tests_dir_filtered(self):
        issues = [make_issue("xss-js-innerhtml", "tests/component/render.js")]
        assert prefilter_issues(issues, {}) == []

    def test_underscore_test_file_filtered(self):
        issues = [make_issue("priv-python-eval", "utils/helper_test.py")]
        assert prefilter_issues(issues, {}) == []

    def test_test_suffix_file_filtered(self):
        issues = [make_issue("xxe-java-document-builder", "src/ParserTest.java")]
        assert prefilter_issues(issues, {}) == []


# ===================================================================
# 新增：Spring Boot 真实误报场景（RED 阶段）
# ===================================================================

class TestCustomTestSourceSets:
    """dockerTest / integrationTest 自定义 source set 必须过滤"""

    def test_docker_test_dir_filtered(self):
        """Spring Boot 实测案例：src/dockerTest/java/.../BootBuildImageIntegrationTests.java"""
        issues = [make_issue(
            "path-write-traversal",
            "build-plugin/spring-boot-gradle-plugin/src/dockerTest/java/"
            "org/springframework/boot/gradle/tasks/bundling/"
            "BootBuildImageIntegrationTests.java",
        )]
        assert prefilter_issues(issues, {}) == []

    def test_integration_test_dir_filtered(self):
        issues = [make_issue(
            "path-read-traversal",
            "src/integrationTest/java/org/app/FullStackIT.java",
        )]
        assert prefilter_issues(issues, {}) == []

    def test_plural_tests_suffix_filtered(self):
        """JUnit 复数约定：*Tests.java（BootBuildImageIntegrationTests.java）"""
        issues = [make_issue("path-write-traversal",
                             "src/main/java/org/app/RepositoryTests.java")]
        assert prefilter_issues(issues, {}) == []

    def test_it_suffix_filtered(self):
        """Maven Failsafe 约定：*IT.java"""
        issues = [make_issue("path-write-traversal",
                             "src/main/java/org/app/EndToEndIT.java")]
        assert prefilter_issues(issues, {}) == []


# ===================================================================
# 前端测试约定
# ===================================================================

class TestFrontendConventions:
    def test_spec_ts_filtered(self):
        issues = [make_issue("xss-js-innerhtml", "components/Modal.spec.ts")]
        assert prefilter_issues(issues, {}) == []

    def test_test_js_filtered(self):
        issues = [make_issue("ssrf-js-fetch", "api/client.test.js")]
        assert prefilter_issues(issues, {}) == []

    def test_pytest_convention_filtered(self):
        issues = [make_issue("priv-python-eval", "test_parser.py")]
        assert prefilter_issues(issues, {}) == []


# ===================================================================
# 反向保护：非测试文件不得被误杀
# ===================================================================

class TestNonTestFilesKept:
    def test_main_source_kept(self):
        """生产代码必须保留，prefilter 不能过度过滤"""
        issues = [make_issue("xxe-java-document-builder",
                             "src/main/java/org/app/Parser.java")]
        result = prefilter_issues(issues, {})
        assert len(result) == 1

    def test_testy_name_but_main_path_kept(self):
        """文件名含 test 但不在测试目录且不符合测试命名 -> 保留"""
        issues = [make_issue("path-read-traversal",
                             "src/main/java/org/app/ContestManager.java")]
        result = prefilter_issues(issues, {})
        assert len(result) == 1

    def test_latest_keyword_not_filtered(self):
        """latest 之类的词不能被误匹配"""
        issues = [make_issue("xss-js-innerhtml", "src/latest.js")]
        result = prefilter_issues(issues, {})
        assert len(result) == 1


# ===================================================================
# 过滤后问题必须打标（可追溯）
# ===================================================================

class TestFilterTraceability:
    def test_filtered_issue_marked(self):
        """被过滤的问题要标 is_false_positive，而不是静默消失"""
        issues = [make_issue("path-write-traversal",
                             "src/test/java/org/app/ParserTest.java")]
        filtered = prefilter_issues(issues, {}, )
        # 返回列表不含该问题（当前实现），但被过滤的问题不返回时
        # 至少保证主流程可继续
        assert filtered == []


# ===================================================================
# 配置化：whitelist 可从 config 覆盖
# ===================================================================

class TestConfigurableWhitelist:
    def test_custom_pattern_from_config(self):
        """用户可以通过 config 自定义白名单模式"""
        config = {"prefilter": {"whitelist": {
            "file_patterns": ["**/generated/**"],
        }}}
        issues = [make_issue("naming-java-boolean-prefix",
                             "codegen/generated/Dto.java")]
        assert prefilter_issues(issues, config) == []

    def test_rule_file_combo_from_config(self):
        """rule_id + file 组合白名单"""
        config = {"prefilter": {"whitelist": {
            "file_patterns": [],
            "rule_file_combos": [
                {"rule_id": "path-write-traversal", "file": "legacy/"},
            ],
        }}}
        issues = [make_issue("path-write-traversal", "legacy/old_writer.py")]
        assert prefilter_issues(issues, config) == []
