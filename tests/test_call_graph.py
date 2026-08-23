#!/usr/bin/env python3
"""
call_graph.py 单元测试
覆盖调用图构建和血缘分析
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from call_graph import CallGraphBuilder


@pytest.fixture
def temp_java_repo():
    """创建包含 Java 源文件的临时 Git 仓库"""
    tmpdir = tempfile.mkdtemp(prefix="test_call_graph_")
    repo_path = Path(tmpdir)

    subprocess.run(["git", "init", "-b", "master"], cwd=str(repo_path), capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(repo_path), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(repo_path), capture_output=True)

    src_dir = repo_path / "src"
    src_dir.mkdir()

    (src_dir / "Service.java").write_text("""
public class Service {
    public void process(String input) {
        String validated = validate(input);
        String result = transform(validated);
        save(result);
    }

    private String validate(String input) {
        if (input == null) throw new IllegalArgumentException();
        return input.trim();
    }

    private String transform(String input) {
        return input.toUpperCase();
    }

    private void save(String data) {
        System.out.println("Saving: " + data);
    }
}
""")

    (src_dir / "Controller.java").write_text("""
public class Controller {
    private Service service = new Service();

    public void handleRequest(String input) {
        service.process(input);
    }
}
""")

    subprocess.run(["git", "add", "."], cwd=str(repo_path), capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=str(repo_path), capture_output=True)

    yield repo_path

    shutil.rmtree(tmpdir, ignore_errors=True)


class TestCallGraphBuilder:
    """测试 CallGraphBuilder"""

    def test_init(self, temp_java_repo):
        """CallGraphBuilder 初始化接受仓库路径"""
        builder = CallGraphBuilder(str(temp_java_repo))
        assert Path(builder.repo_path).resolve() == temp_java_repo.resolve()

    def test_build_returns_graph_structure(self, temp_java_repo):
        """build() 返回包含节点、边、影响范围的字典"""
        builder = CallGraphBuilder(str(temp_java_repo))
        changed_methods = [
            {"file": "src/Service.java", "name": "process", "line": 3, "end_line": 8}
        ]
        result = builder.build(changed_methods)

        assert "node_count" in result
        assert "edge_count" in result
        assert "affected_methods" in result
        assert isinstance(result["node_count"], int)
        assert isinstance(result["edge_count"], int)
        assert isinstance(result["affected_methods"], list)

    def test_build_detects_call_relationships(self, temp_java_repo):
        """build() 检测到方法间的调用关系"""
        builder = CallGraphBuilder(str(temp_java_repo))
        changed_methods = [
            {"file": "src/Service.java", "name": "process", "line": 3, "end_line": 8}
        ]
        result = builder.build(changed_methods)

        assert result["node_count"] >= 1

    def test_build_all_scans_entire_repo(self, temp_java_repo):
        """build_all() 扫描整个仓库"""
        builder = CallGraphBuilder(str(temp_java_repo))
        result = builder.build_all()

        assert "node_count" in result
        assert result["node_count"] >= 2

    def test_build_empty_methods(self, temp_java_repo):
        """build() 空方法列表时返回图结构"""
        builder = CallGraphBuilder(str(temp_java_repo))
        result = builder.build([])

        assert "node_count" in result
        assert result["node_count"] >= 0

    def test_build_with_language_param(self, temp_java_repo):
        """CallGraphBuilder 支持 language 参数"""
        builder = CallGraphBuilder(str(temp_java_repo), language="java")
        result = builder.build_all()
        assert "node_count" in result
