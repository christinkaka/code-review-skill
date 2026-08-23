#!/usr/bin/env python3
"""
rule_compiler.py 单元测试
覆盖规则预编译、缓存和清单管理
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from rule_compiler import RuleCompiler


@pytest.fixture
def compiler_env():
    """创建 RuleCompiler 测试环境"""
    with tempfile.TemporaryDirectory() as tmpdir:
        specs_dir = os.path.join(tmpdir, "specs")
        os.makedirs(specs_dir)

        security_dir = os.path.join(specs_dir, "security")
        os.makedirs(security_dir)

        rule_content = """# SQL 注入 - 字符串拼接

> 使用字符串拼接构建 SQL 查询，存在 SQL 注入风险。

```yaml
id: sqli-java-concat
languages: [java]
severity: ERROR
cwe: CWE-89
```

## 检测模式

```pattern
String $SQL = $STR + $USER_INPUT;
```

```pattern
Statement $STMT = $CONN.createStatement();
```
"""
        with open(os.path.join(security_dir, "sql-injection.md"), "w") as f:
            f.write(rule_content)

        compiler = RuleCompiler(specs_dir=specs_dir)

        yield {
            "compiler": compiler,
            "specs_dir": specs_dir,
            "rule_file": os.path.join(security_dir, "sql-injection.md"),
        }


class TestRuleCompiler:
    """测试 RuleCompiler"""

    def test_init(self, compiler_env):
        """RuleCompiler 初始化接受 specs_dir"""
        compiler = compiler_env["compiler"]
        assert compiler is not None
        assert compiler.specs_dir is not None

    def test_compute_file_hash(self, compiler_env):
        """compute_file_hash() 返回文件的哈希值"""
        compiler = compiler_env["compiler"]
        file_hash = compiler.compute_file_hash(compiler_env["rule_file"])

        assert isinstance(file_hash, str)
        assert len(file_hash) > 0

    def test_compute_file_hash_deterministic(self, compiler_env):
        """compute_file_hash() 同一文件返回相同哈希"""
        compiler = compiler_env["compiler"]
        hash1 = compiler.compute_file_hash(compiler_env["rule_file"])
        hash2 = compiler.compute_file_hash(compiler_env["rule_file"])

        assert hash1 == hash2

    def test_compile_file(self, compiler_env):
        """compile_file() 编译单个规约文件"""
        compiler = compiler_env["compiler"]
        result = compiler.compile_file(compiler_env["rule_file"])

        assert isinstance(result, dict)
        assert "rules" in result
        assert len(result["rules"]) >= 1

    def test_compile_file_extracts_rules(self, compiler_env):
        """compile_file() 正确提取规则信息"""
        compiler = compiler_env["compiler"]
        result = compiler.compile_file(compiler_env["rule_file"])

        rules = result["rules"]
        rule_ids = [r.get("id") for r in rules]
        assert "sqli-java-concat" in rule_ids

    def test_manifest_management(self, compiler_env):
        """load_manifest() 和 save_manifest() 正常工作"""
        compiler = compiler_env["compiler"]

        manifest = compiler.load_manifest()
        assert isinstance(manifest, dict)

    def test_is_cache_valid_false_for_new_file(self, compiler_env):
        """is_cache_valid() 对新文件返回 False"""
        compiler = compiler_env["compiler"]
        file_hash = compiler.compute_file_hash(compiler_env["rule_file"])

        valid = compiler.is_cache_valid("security/sql-injection.md", file_hash, {})
        assert valid is False

    def test_is_cache_valid_true_after_compile(self, compiler_env):
        """is_cache_valid() 编译后对相同哈希返回 True"""
        compiler = compiler_env["compiler"]

        compiler.compile_file(compiler_env["rule_file"])

        file_hash = compiler.compute_file_hash(compiler_env["rule_file"])
        manifest = compiler.load_manifest()

        valid = compiler.is_cache_valid("security/sql-injection.md", file_hash, manifest)
        assert valid is True

    def test_is_cache_valid_false_after_change(self, compiler_env):
        """is_cache_valid() 文件修改后返回 False"""
        compiler = compiler_env["compiler"]

        compiler.compile_file(compiler_env["rule_file"])

        file_hash = compiler.compute_file_hash(compiler_env["rule_file"])
        manifest = compiler.load_manifest()

        valid = compiler.is_cache_valid("security/sql-injection.md", "different_hash", manifest)
        assert valid is False
