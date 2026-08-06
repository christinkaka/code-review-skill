#!/usr/bin/env python3
"""
AI 评审器单元测试

覆盖 AIReviewer 的核心方法：
- 工作流配置和切换
- 任务生成（generate_subagent_task）
- 反馈注入
- 文件保存
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from ai_reviewer import AIReviewer


# ===================================================================
# 辅助 fixtures
# ===================================================================

@pytest.fixture
def reviewer():
    """创建默认配置的 AIReviewer 实例"""
    config = {"workflow": "comprehensive"}
    return AIReviewer(config)


@pytest.fixture
def reviewer_with_feedback():
    """创建带反馈数据的 AIReviewer 实例"""
    config = {
        "workflow": "comprehensive",
        "feedback_summary": {
            "total": 50,
            "confirmed": 30,
            "false_positive": 15,
            "uncertain": 5,
        },
        "feedback_examples": [
            {
                "rule_id": "xxe-java-document-builder",
                "verdict": "confirmed",
                "comment": "确认是真实问题",
            },
            {
                "rule_id": "naming-convention",
                "verdict": "false_positive",
                "comment": "这是测试代码",
            },
        ],
    }
    return AIReviewer(config)


@pytest.fixture
def sample_issues():
    """示例问题列表"""
    return [
        {
            "rule_id": "sqli-java-concat",
            "file": "src/UserDAO.java",
            "line": 42,
            "severity": "ERROR",
            "message": "SQL 注入 - 字符串拼接",
        },
        {
            "rule_id": "xss-js-innerhtml",
            "file": "web/app.js",
            "line": 88,
            "severity": "WARNING",
            "message": "XSS - innerHTML 赋值",
        },
    ]


@pytest.fixture
def sample_diff_result():
    """示例差异分析结果"""
    return {
        "changed_files": [
            {"path": "src/UserDAO.java", "status": "modified"},
            {"path": "web/app.js", "status": "modified"},
        ],
        "changed_methods": [
            {"file": "src/UserDAO.java", "name": "queryUser", "line": 40},
        ],
    }


@pytest.fixture
def sample_call_graph():
    """示例调用图"""
    return {
        "node_count": 15,
        "edge_count": 20,
        "affected_methods": ["handleRequest", "queryUser"],
        "call_chains": {},
    }


# ===================================================================
# 测试工作流配置
# ===================================================================

class TestWorkflowConfig:
    """测试工作流配置和切换"""

    def test_init_default_workflow(self):
        """默认工作流为 comprehensive"""
        reviewer = AIReviewer({})
        assert reviewer.workflow == "comprehensive"

    def test_init_custom_workflow(self):
        """支持自定义工作流"""
        reviewer = AIReviewer({"workflow": "security"})
        assert reviewer.workflow == "security"

    def test_get_current_workflow(self, reviewer):
        """get_current_workflow() 返回当前工作流"""
        assert reviewer.get_current_workflow() == "comprehensive"

    def test_get_available_workflows(self, reviewer):
        """get_available_workflows() 返回所有可用工作流"""
        workflows = reviewer.get_available_workflows()
        assert "security" in workflows
        assert "quality" in workflows
        assert "comprehensive" in workflows
        assert len(workflows) == 5

    def test_set_workflow_success(self, reviewer):
        """set_workflow() 成功切换工作流"""
        result = reviewer.set_workflow("security")
        assert result is True
        assert reviewer.workflow == "security"

    def test_set_workflow_invalid(self, reviewer):
        """set_workflow() 无效工作流返回 False"""
        result = reviewer.set_workflow("invalid_workflow")
        assert result is False
        assert reviewer.workflow == "comprehensive"


# ===================================================================
# 测试任务生成
# ===================================================================

class TestGenerateTask:
    """测试任务生成"""

    def test_generate_task_returns_string(self, reviewer, sample_issues, 
                                          sample_diff_result, sample_call_graph):
        """generate_subagent_task() 返回字符串"""
        task = reviewer.generate_subagent_task(
            sample_issues, sample_diff_result, sample_call_graph
        )
        assert isinstance(task, str)
        assert len(task) > 0

    def test_generate_task_contains_workflow(self, reviewer, sample_issues,
                                              sample_diff_result, sample_call_graph):
        """任务描述包含工作流信息"""
        task = reviewer.generate_subagent_task(
            sample_issues, sample_diff_result, sample_call_graph
        )
        assert "综合评审工作流" in task or "工作流" in task

    def test_generate_task_contains_temperature(self, reviewer, sample_issues,
                                                 sample_diff_result, sample_call_graph):
        """任务描述包含温度参数"""
        task = reviewer.generate_subagent_task(
            sample_issues, sample_diff_result, sample_call_graph
        )
        assert "temperature" in task

    def test_generate_task_contains_issues(self, reviewer, sample_issues,
                                            sample_diff_result, sample_call_graph):
        """任务描述包含问题列表"""
        task = reviewer.generate_subagent_task(
            sample_issues, sample_diff_result, sample_call_graph
        )
        assert "sqli-java-concat" in task
        assert "xss-js-innerhtml" in task

    def test_generate_task_contains_changed_files(self, reviewer, sample_issues,
                                                   sample_diff_result, sample_call_graph):
        """任务描述包含变更文件"""
        task = reviewer.generate_subagent_task(
            sample_issues, sample_diff_result, sample_call_graph
        )
        assert "UserDAO.java" in task or "app.js" in task

    def test_generate_task_empty_issues(self, reviewer, sample_diff_result, sample_call_graph):
        """空问题列表返回空字符串"""
        task = reviewer.generate_subagent_task(
            [], sample_diff_result, sample_call_graph
        )
        assert task == ""

    def test_generate_task_contains_output_format(self, reviewer, sample_issues,
                                                   sample_diff_result, sample_call_graph):
        """任务描述包含输出格式要求"""
        task = reviewer.generate_subagent_task(
            sample_issues, sample_diff_result, sample_call_graph
        )
        assert "rule_id" in task
        assert "is_valid" in task
        assert "confidence" in task
        assert "enhanced_fix" in task


# ===================================================================
# 测试反馈注入
# ===================================================================

class TestFeedbackInjection:
    """测试历史反馈注入"""

    def test_reviewer_accepts_feedback_summary(self):
        """AIReviewer 接受 feedback_summary 配置"""
        config = {
            "workflow": "comprehensive",
            "feedback_summary": {
                "total": 50,
                "confirmed": 30,
                "false_positive": 15,
                "uncertain": 5,
            },
        }
        reviewer = AIReviewer(config)
        assert reviewer.feedback_summary is not None
        assert reviewer.feedback_summary["total"] == 50

    def test_reviewer_accepts_feedback_examples(self):
        """AIReviewer 接受 feedback_examples 配置"""
        config = {
            "workflow": "comprehensive",
            "feedback_examples": [
                {
                    "rule_id": "xxe-java-document-builder",
                    "verdict": "confirmed",
                    "comment": "确认是真实问题",
                },
            ],
        }
        reviewer = AIReviewer(config)
        assert len(reviewer.feedback_examples) == 1

    def test_generate_task_includes_feedback_section(self, reviewer_with_feedback,
                                                      sample_issues, sample_diff_result,
                                                      sample_call_graph):
        """生成的任务描述包含历史反馈部分"""
        task = reviewer_with_feedback.generate_subagent_task(
            sample_issues, sample_diff_result, sample_call_graph
        )
        assert "历史反馈" in task or "反馈统计" in task

    def test_generate_task_no_feedback_section_when_empty(self, reviewer, sample_issues,
                                                           sample_diff_result, sample_call_graph):
        """无反馈数据时不包含历史反馈部分"""
        task = reviewer.generate_subagent_task(
            sample_issues, sample_diff_result, sample_call_graph
        )
        assert "历史反馈" not in task


# ===================================================================
# 测试文件保存
# ===================================================================

class TestSaveTask:
    """测试任务文件保存"""

    def test_save_task_to_file(self, reviewer, sample_issues, sample_diff_result,
                                sample_call_graph, tmp_path):
        """save_task_to_file() 正确保存任务到文件"""
        task = reviewer.generate_subagent_task(
            sample_issues, sample_diff_result, sample_call_graph
        )
        output_file = tmp_path / "task.md"
        
        reviewer.save_task_to_file(task, str(output_file))
        
        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")
        assert content == task

    def test_save_task_creates_parent_dirs(self, reviewer, sample_issues,
                                            sample_diff_result, sample_call_graph, tmp_path):
        """save_task_to_file() 创建父目录"""
        task = "test task"
        output_file = tmp_path / "subdir" / "task.md"
        
        reviewer.save_task_to_file(task, str(output_file))
        
        assert output_file.exists()
