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

    def test_build_traces_callers_across_unchanged_files(self, temp_java_repo):
        """全仓索引应追踪未变更文件中的跨文件调用者。"""
        builder = CallGraphBuilder(str(temp_java_repo))
        result = builder.build([
            {"file": "src/Service.java", "name": "validate", "line": 9, "end_line": 12}
        ])

        assert "process" in result["affected_methods"]
        assert "handleRequest" in result["affected_methods"]
        assert any(node["file"] == "src/Controller.java" for node in result["nodes"])

    def test_duplicate_method_names_do_not_create_cross_file_cartesian_edges(self, temp_java_repo):
        """跨文件同名方法不能产生 N*M 组合边。"""
        (temp_java_repo / "src" / "Other.java").write_text("""
public class Other {
    public void process(String input) {
        validate(input);
    }

    private String validate(String input) {
        return input;
    }
}
""")
        builder = CallGraphBuilder(str(temp_java_repo))
        result = builder.build([
            {"file": "src/Service.java", "name": "validate", "line": 9, "end_line": 12},
            {"file": "src/Other.java", "name": "validate", "line": 7, "end_line": 9},
        ])

        edge_pairs = {(edge["from"], edge["to"]) for edge in result["edges"]}
        assert len(edge_pairs) == result["edge_count"]
        assert all(
            source.split(":", 1)[0] == target.split(":", 1)[0]
            for source, target in edge_pairs
        )

    def test_build_ignores_paths_outside_repository(self, temp_java_repo):
        """变更文件路径不能越过仓库边界。"""
        builder = CallGraphBuilder(str(temp_java_repo))
        result = builder.build([
            {"file": "../outside.java", "name": "outside", "line": 1, "end_line": 2}
        ])

        assert result["node_count"] == 0
        assert result["edge_count"] == 0

    def test_build_handles_78_files_and_533_changed_methods_without_unrelated_nodes(self, tmp_path):
        """回归实际规模：全仓扫描后不把无关方法加入影响图。"""
        src_dir = tmp_path / "src"
        unrelated_dir = tmp_path / "unrelated"
        src_dir.mkdir()
        unrelated_dir.mkdir()
        changed_methods = []

        for file_index in range(78):
            method_count = 7 if file_index < 65 else 6
            methods = []
            for method_index in range(method_count):
                name = f"changed_{file_index}_{method_index}"
                methods.append(f"    public void {name}() {{}}")
                changed_methods.append({
                    "file": f"src/Changed{file_index}.java",
                    "name": name,
                    "line": method_index + 2,
                    "end_line": method_index + 2,
                })
            (src_dir / f"Changed{file_index}.java").write_text(
                "public class Changed%d {\n%s\n}\n" % (file_index, "\n".join(methods))
            )

        assert len(changed_methods) == 533
        for file_index in range(200):
            (unrelated_dir / f"Unrelated{file_index}.java").write_text(
                f"public class Unrelated{file_index} {{ public void unrelated_{file_index}() {{}} }}\n"
            )

        result = CallGraphBuilder(str(tmp_path)).build(changed_methods)

        assert result["node_count"] == 533
        assert len(result["affected_methods"]) == 533
        assert all(node["file"].startswith("src/") for node in result["nodes"])
