#!/usr/bin/env python3
"""
diff_analyzer.py 单元测试
覆盖差异分析和全库扫描两种模式
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from diff_analyzer import DiffAnalyzer


@pytest.fixture
def temp_git_repo():
    """创建带有分支和变更的临时 Git 仓库"""
    tmpdir = tempfile.mkdtemp(prefix="test_diff_analyzer_")
    repo_path = Path(tmpdir)

    subprocess.run(["git", "init", "-b", "master"], cwd=str(repo_path), capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(repo_path), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(repo_path), capture_output=True)

    # 创建初始文件
    src_dir = repo_path / "src"
    src_dir.mkdir()
    (src_dir / "Main.java").write_text(
        'public class Main {\n    public void hello() {\n        System.out.println("hello");\n    }\n}\n'
    )
    (src_dir / "Utils.java").write_text(
        'public class Utils {\n    public static String trim(String s) {\n        return s.trim();\n    }\n}\n'
    )
    subprocess.run(["git", "add", "."], cwd=str(repo_path), capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=str(repo_path), capture_output=True)

    # 创建 feature 分支并修改文件
    subprocess.run(["git", "checkout", "-b", "feature"], cwd=str(repo_path), capture_output=True)
    (src_dir / "Main.java").write_text(
        'public class Main {\n    public void hello() {\n        System.out.println("hello world");\n    }\n    public void goodbye() {\n        System.out.println("bye");\n    }\n}\n'
    )
    (src_dir / "New.java").write_text(
        'public class New {\n    public void test() {}\n}\n'
    )
    subprocess.run(["git", "add", "."], cwd=str(repo_path), capture_output=True)
    subprocess.run(["git", "commit", "-m", "Feature changes"], cwd=str(repo_path), capture_output=True)

    yield repo_path

    shutil.rmtree(tmpdir, ignore_errors=True)


class TestDiffAnalyzer:
    """测试 DiffAnalyzer"""

    def test_init(self, temp_git_repo):
        """DiffAnalyzer 初始化接受仓库路径"""
        analyzer = DiffAnalyzer(str(temp_git_repo))
        # 使用 resolve() 处理符号链接
        assert Path(analyzer.repo_path).resolve() == temp_git_repo.resolve()

    def test_analyze_returns_changed_files(self, temp_git_repo):
        """analyze() 返回变更文件列表"""
        analyzer = DiffAnalyzer(str(temp_git_repo))
        result = analyzer.analyze("master", "feature")

        assert "changed_files" in result
        assert isinstance(result["changed_files"], list)
        assert len(result["changed_files"]) >= 1

    def test_analyze_detects_modified_file(self, temp_git_repo):
        """analyze() 检测到修改的文件"""
        analyzer = DiffAnalyzer(str(temp_git_repo))
        result = analyzer.analyze("master", "feature")

        file_paths = [f["path"] for f in result["changed_files"]]
        assert any("Main.java" in p for p in file_paths)

    def test_analyze_detects_added_file(self, temp_git_repo):
        """analyze() 检测到新增的文件"""
        analyzer = DiffAnalyzer(str(temp_git_repo))
        result = analyzer.analyze("master", "feature")

        file_paths = [f["path"] for f in result["changed_files"]]
        assert any("New.java" in p for p in file_paths)

    def test_analyze_returns_changed_methods(self, temp_git_repo):
        """analyze() 返回变更方法列表"""
        analyzer = DiffAnalyzer(str(temp_git_repo))
        result = analyzer.analyze("master", "feature")

        assert "changed_methods" in result
        assert isinstance(result["changed_methods"], list)

    def test_analyze_no_changes(self, temp_git_repo):
        """analyze() 无变更时返回空列表"""
        analyzer = DiffAnalyzer(str(temp_git_repo))
        result = analyzer.analyze("master", "master")

        assert len(result["changed_files"]) == 0

    def test_scan_full_returns_all_files(self, temp_git_repo):
        """scan_full() 返回仓库中所有源文件"""
        analyzer = DiffAnalyzer(str(temp_git_repo))
        result = analyzer.scan_full()

        assert "changed_files" in result
        assert len(result["changed_files"]) >= 2

    def test_scan_full_includes_all_source_files(self, temp_git_repo):
        """scan_full() 包含所有 Java 源文件"""
        analyzer = DiffAnalyzer(str(temp_git_repo))
        result = analyzer.scan_full()

        file_paths = [f["path"] for f in result["changed_files"]]
        assert any("Main.java" in p for p in file_paths)
        assert any("Utils.java" in p for p in file_paths)
