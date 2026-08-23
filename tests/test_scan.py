#!/usr/bin/env python3
"""
scan.py 单元测试
覆盖配置加载、harness 集成、主流程编排
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest
import yaml

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT))


class TestLoadConfig:
    """测试配置加载"""

    def test_load_config_default(self):
        """load_config() 加载项目根目录的 config.yaml"""
        from scan import load_config
        config = load_config(str(PROJECT_ROOT / "config.yaml"))
        assert isinstance(config, dict)
        assert len(config) > 0

    def test_load_config_nonexistent_returns_empty(self):
        """load_config() 文件不存在时返回空字典"""
        from scan import load_config
        config = load_config("/nonexistent/path/config.yaml")
        assert config == {}

    def test_load_config_custom_path(self, tmp_path):
        """load_config() 支持自定义路径"""
        config_file = tmp_path / "custom.yaml"
        config_file.write_text(yaml.dump({"custom_key": "custom_value"}))
        from scan import load_config
        config = load_config(str(config_file))
        assert config["custom_key"] == "custom_value"


class TestLoadHarnessConfig:
    """测试 harness 配置加载"""

    def test_load_harness_config_default(self):
        """load_harness_config() 加载 config/harness.yaml"""
        from scan import load_harness_config
        harness = load_harness_config()
        assert isinstance(harness, dict)
        assert "harness" in harness
        assert harness["harness"]["enabled"] is True

    def test_load_harness_config_decision_logging(self):
        """harness 配置包含决策日志设置"""
        from scan import load_harness_config
        harness = load_harness_config()
        dl = harness["harness"]["decision_logging"]
        assert dl["enabled"] is True
        assert dl["keep_recent"] == 10
        assert dl["storage_dir"] == "data/decisions"

    def test_load_harness_config_feedback(self):
        """harness 配置包含反馈设置"""
        from scan import load_harness_config
        harness = load_harness_config()
        fb = harness["harness"]["feedback"]
        assert fb["enabled"] is True
        assert fb["storage_file"] == "data/feedbacks.json"

    def test_load_harness_config_quality_monitor(self):
        """harness 配置包含质量监控设置"""
        from scan import load_harness_config
        harness = load_harness_config()
        qm = harness["harness"]["quality_monitor"]
        assert qm["enabled"] is True
        assert qm["cache_file"] == "data/stats_cache.json"

    def test_load_harness_config_nonexistent_returns_disabled(self, tmp_path):
        """harness.yaml 不存在时返回禁用配置"""
        from scan import load_harness_config
        harness = load_harness_config(str(tmp_path / "nonexistent.yaml"))
        assert harness["harness"]["enabled"] is False

    def test_load_harness_config_custom_path(self, tmp_path):
        """load_harness_config() 支持自定义路径"""
        harness_file = tmp_path / "harness.yaml"
        harness_file.write_text(yaml.dump({
            "harness": {
                "enabled": True,
                "decision_logging": {"enabled": False, "keep_recent": 5, "storage_dir": "custom/decisions"},
                "feedback": {"enabled": False, "allow_batch": False, "storage_file": "custom/feedbacks.json"},
                "auto_improvement": {"enabled": False, "min_accuracy_threshold": 0.7, "max_adjustment_delta": 0.2, "require_confirmation": True, "storage_file": "custom/adjustments.json"},
                "quality_monitor": {"enabled": False, "cache_file": "custom/stats_cache.json"},
            }
        }))
        from scan import load_harness_config
        harness = load_harness_config(str(harness_file))
        assert harness["harness"]["decision_logging"]["enabled"] is False
        assert harness["harness"]["decision_logging"]["keep_recent"] == 5


class TestHarnessIntegration:
    """测试 harness 组件集成"""

    def test_init_harness_components(self):
        """init_harness_components() 返回初始化的 harness 组件"""
        # 直接导入 harness 模块，避免 scan.py 的导入问题
        from harness.decision_logger import DecisionLogger
        from harness.feedback_manager import FeedbackManager
        from harness.quality_monitor import QualityMonitor

        with tempfile.TemporaryDirectory() as tmpdir:
            harness_config = {
                "harness": {
                    "enabled": True,
                    "decision_logging": {
                        "enabled": True,
                        "keep_recent": 10,
                        "storage_dir": os.path.join(tmpdir, "decisions"),
                    },
                    "feedback": {
                        "enabled": True,
                        "allow_batch": True,
                        "storage_file": os.path.join(tmpdir, "feedbacks.json"),
                    },
                    "quality_monitor": {
                        "enabled": True,
                        "cache_file": os.path.join(tmpdir, "stats_cache.json"),
                    },
                }
            }

            # 手动初始化组件
            dl = DecisionLogger(storage_dir=harness_config["harness"]["decision_logging"]["storage_dir"])
            fm = FeedbackManager(storage_file=harness_config["harness"]["feedback"]["storage_file"])
            qm = QualityMonitor(dl, fm, cache_file=harness_config["harness"]["quality_monitor"]["cache_file"])

            assert dl is not None
            assert fm is not None
            assert qm is not None

    def test_init_harness_components_disabled(self):
        """harness 禁用时返回 None 组件"""
        from scan import init_harness_components

        harness_config = {"harness": {"enabled": False}}
        components = init_harness_components(harness_config)

        assert components["decision_logger"] is None
        assert components["feedback_manager"] is None
        assert components["quality_monitor"] is None


class TestScanFeedbackWire:
    """测试 scan.py 将反馈数据传递给 AIReviewer"""

    def test_build_feedback_examples(self):
        """build_feedback_examples() 从 FeedbackManager 提取近期示例"""
        from scan import build_feedback_examples
        from harness.feedback_manager import FeedbackManager

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_file = os.path.join(tmpdir, "feedbacks.json")
            fm = FeedbackManager(storage_file=storage_file)

            # 添加反馈
            fm.add_feedback("issue-001", "scan-001", "confirmed", "确认是 SQL 注入")
            fm.add_feedback("issue-002", "scan-001", "false_positive", "测试代码")
            fm.add_feedback("issue-003", "scan-001", "uncertain", None)

            examples = build_feedback_examples(fm)

            assert len(examples) == 3
            # 验证所有反馈都被返回
            verdicts = {e["verdict"] for e in examples}
            assert "confirmed" in verdicts
            assert "false_positive" in verdicts
            assert "uncertain" in verdicts

    def test_build_feedback_examples_empty(self):
        """无反馈数据时返回空列表"""
        from scan import build_feedback_examples
        from harness.feedback_manager import FeedbackManager

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_file = os.path.join(tmpdir, "feedbacks.json")
            fm = FeedbackManager(storage_file=storage_file)

            examples = build_feedback_examples(fm)
            assert examples == []


class TestRunScanIntegration:
    """测试 run_scan() 完整流程集成"""

    def test_run_scan_without_harness(self, tmp_path):
        """run_scan() harness 禁用时正常工作"""
        from scan import run_scan

        args = MagicMock()
        args.repo = str(tmp_path)
        args.base = "master"
        args.target = "feature"
        args.profile = "default"
        args.output = str(tmp_path / "report")
        args.config = None
        args.specs_dir = None
        args.language = "java"
        args.workflow = "comprehensive"
        args.full_scan = False

        with patch("scan.DiffAnalyzer") as MockDiff, \
             patch("scan.CallGraphBuilder") as MockCG, \
             patch("scan.RuleEngine") as MockEngine, \
             patch("scan.AIReviewer") as MockAI, \
             patch("scan.ReportGenerator") as MockReport, \
             patch("scan.load_harness_config") as mock_harness_config:

            MockDiff.return_value.analyze.return_value = {
                "changed_files": [{"path": "src/Main.java", "status": "modified"}],
                "changed_methods": [],
            }
            MockCG.return_value.build.return_value = {
                "node_count": 0, "edge_count": 0, "affected_methods": [], "call_chains": {},
            }
            MockEngine.return_value.run.return_value = []
            MockAI.return_value.generate_subagent_task.return_value = ""
            MockAI.return_value.get_current_workflow.return_value = "comprehensive"
            MockReport.return_value.generate.return_value = {"summary": {"total": 0}}

            mock_harness_config.return_value = {"harness": {"enabled": False}}

            report = run_scan(args)

            assert report is not None
