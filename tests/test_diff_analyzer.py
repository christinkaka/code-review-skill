#!/usr/bin/env python3
"""
DiffAnalyzer 增删行数统计测试

背景：scan.py 完整流程在 Django 真实仓库上跑通后发现报告统计
「新增行数: 0 / 删除行数: 0」，但 git diff --stat 实际是
2401 insertions / 2987 deletions。

根因：GitPython 的 commit.diff(other) 默认不生成 patch 内容，
diff_item.diff 为空 -> 增删计数静默归零（被 except Exception: pass 吞掉）。
需要 create_patch=True 才能拿到 @@ -a,b +c,d @@ 格式的补丁文本。

必须验证：
1. 修改文件：additions/deletions 为真实计数（非 0）
2. 新增文件：additions > 0，deletions == 0
3. 删除文件：additions == 0，deletions > 0
4. 汇总 stats.insertions/deletions 与各文件累加一致
5. 与 git diff --numstat 的官方计数一致（交叉验证）
"""

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from diff_analyzer import DiffAnalyzer


def git_cmd(repo_path, *args):
    return subprocess.run(
        ["git", *args], cwd=str(repo_path),
        capture_output=True, text=True,
    )


def commit_all(repo_path, msg):
    git_cmd(repo_path, "add", ".")
    git_cmd(repo_path, "-c", "user.email=t@t.com", "-c", "user.name=T",
            "commit", "-m", msg)


@pytest.fixture
def two_branch_repo(temp_repo):
    """构造 base/target 两分支仓库：base 有 3 处代码，target 做增删改"""
    repo = temp_repo

    # base 分支：初始代码
    (repo / "app.py").write_text(
        "import os\n"
        "\n"
        "def keep():\n"
        "    return 1\n"
        "\n"
        "def modify_me():\n"
        "    return 2\n"
        "\n"
        "def remove_me():\n"
        "    return 3\n",
        encoding="utf-8",
    )
    commit_all(repo, "base state")

    git_cmd(repo, "checkout", "-b", "feature")

    # target 分支：修改 + 新增 + 删除
    (repo / "app.py").write_text(
        "import os\n"
        "\n"
        "def keep():\n"
        "    return 1\n"
        "\n"
        "def modify_me():\n"
        "    return 99\n"          # 修改 1 行（-1/+1）
        "\n"
        "def new_func():\n"        # 新增 3 行
        "    a = 1\n"
        "    return a\n",
        encoding="utf-8",
    )
    # remove_me 函数被删（-3 行）
    (repo / "new_file.py").write_text("x = 1\ny = 2\n", encoding="utf-8")  # 新文件 +2
    (repo / "gone_file.py").write_text("z = 3\n", encoding="utf-8")
    commit_all(repo, "feature state")
    # 删除文件放在最后一个提交，保证 base 有、target 无
    # 实际上上面 gone_file 在 base 不存在 -> 需要在 base 就创建

    return repo


@pytest.fixture
def full_repo(temp_repo):
    """严格的增删改删文件四场景仓库"""
    repo = temp_repo

    # base：modify.py + delete_me.py
    (repo / "modify.py").write_text("a = 1\nb = 2\nc = 3\n", encoding="utf-8")
    (repo / "delete_me.py").write_text("x = 1\nx = 2\n", encoding="utf-8")
    commit_all(repo, "base")

    git_cmd(repo, "checkout", "-b", "feature")

    # target：改 1 行 + 新文件 + 删文件
    (repo / "modify.py").write_text("a = 1\nb = 99\nc = 3\n", encoding="utf-8")
    (repo / "brand_new.py").write_text("n = 1\n", encoding="utf-8")
    (repo / "delete_me.py").unlink()
    commit_all(repo, "feature")

    return repo


class TestAdditionDeletionCounts:

    def test_modified_file_counts_real_numbers(self, full_repo):
        """修改文件必须统计出真实增删（-1/+1），不能是 0"""
        analyzer = DiffAnalyzer(str(full_repo))
        result = analyzer.analyze("master", "feature")

        modify = next(f for f in result["changed_files"]
                      if f["path"] == "modify.py")
        assert modify["additions"] == 1, (
            f"modify.py 新增行应为 1，实际 {modify['additions']}"
        )
        assert modify["deletions"] == 1, (
            f"modify.py 删除行应为 1，实际 {modify['deletions']}"
        )

    def test_new_file_counts_additions_only(self, full_repo):
        """新增文件：additions=1, deletions=0"""
        analyzer = DiffAnalyzer(str(full_repo))
        result = analyzer.analyze("master", "feature")

        new_file = next(f for f in result["changed_files"]
                        if f["path"] == "brand_new.py")
        assert new_file["additions"] == 1
        assert new_file["deletions"] == 0

    def test_deleted_file_counts_deletions_only(self, full_repo):
        """删除文件：additions=0, deletions=2"""
        analyzer = DiffAnalyzer(str(full_repo))
        result = analyzer.analyze("master", "feature")

        deleted = next(f for f in result["changed_files"]
                       if f["path"] == "delete_me.py")
        assert deleted["additions"] == 0
        assert deleted["deletions"] == 2

    def test_stats_sum_matches_files(self, full_repo):
        """汇总 stats 必须等于各文件累加"""
        analyzer = DiffAnalyzer(str(full_repo))
        result = analyzer.analyze("master", "feature")

        stats = result["stats"]
        assert stats["insertions"] == sum(f["additions"]
                                          for f in result["changed_files"])
        assert stats["deletions"] == sum(f["deletions"]
                                         for f in result["changed_files"])
        # 本仓库：改 1 行 + 新文件 1 行 -> insertions = 2
        # 删 1 行 + 删文件 2 行 -> deletions = 3
        assert stats["insertions"] == 2, f"insertions 应为 2: {stats}"
        assert stats["deletions"] == 3, f"deletions 应为 3: {stats}"

    def test_matches_git_numstat_official_counts(self, full_repo):
        """与 git diff --numstat 官方计数交叉验证"""
        analyzer = DiffAnalyzer(str(full_repo))
        result = analyzer.analyze("master", "feature")

        numstat = git_cmd(full_repo, "diff", "master", "feature", "--numstat")
        official = {}
        for line in numstat.stdout.strip().split("\n"):
            if not line.strip():
                continue
            add, dele, path = line.split("\t")
            official[path] = (int(add), int(dele))

        for f in result["changed_files"]:
            if f["path"] in official:
                exp_add, exp_del = official[f["path"]]
                assert f["additions"] == exp_add, (
                    f"{f['path']} additions {f['additions']} != 官方 {exp_add}"
                )
                assert f["deletions"] == exp_del, (
                    f"{f['path']} deletions {f['deletions']} != 官方 {exp_del}"
                )
