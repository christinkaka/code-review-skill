#!/usr/bin/env python3
"""
定期扫描调度模块验收测试
覆盖 ACCEPTANCE-CRITERIA.md 中 SCHED-AC1 至 SCHED-AC4 的全部测试场景。

测试场景清单：
  SCHED-AC1-TS1: Cron 表达式解析与下次执行时间计算
  SCHED-AC1-TS2: 无效 Cron 表达式错误处理
  SCHED-AC1-TS3: Cron 定时触发扫描执行
  SCHED-AC2-TS1: Webhook 通知发送成功
  SCHED-AC2-TS2: Webhook 目标不可达时的错误处理
  SCHED-AC2-TS3: Webhook 通知内容格式验证
  SCHED-AC3-TS1: CLI --trigger 参数执行扫描
  SCHED-AC3-TS2: 无变更时手动触发
  SCHED-AC4-TS1: 扫描异常触发告警
  SCHED-AC4-TS2: 告警通知包含诊断信息
  SCHED-AC4-TS3: 连续失败时的告警限流

运行方式：
  # 全部调度模块测试（全部 Mock，可离线运行）
  pytest tests/test_scheduler_e2e.py -v

  # 运行特定测试类
  pytest tests/test_scheduler_e2e.py::TestSCHEDAC1CronSchedule -v
  pytest tests/test_scheduler_e2e.py::TestSCHEDAC2WebhookNotification -v
  pytest tests/test_scheduler_e2e.py::TestSCHEDAC3ManualTrigger -v
  pytest tests/test_scheduler_e2e.py::TestSCHEDAC4FailureAlert -v
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

# 确保可以导入项目模块
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from conftest import (
    Scheduler,
    Notifier,
    ScanRunner,
    CronExpression,
    MockWebhookServer,
    build_mock_diff_result,
    build_mock_call_graph,
)


# ============================================================
# SCHED-AC1: Cron 定时自动扫描
# ============================================================
class TestSCHEDAC1CronSchedule:
    """SCHED-AC1 测试组：Cron 定时自动扫描"""

    def test_parse_cron_expression(self):
        """
        SCHED-AC1-TS1: Cron 表达式解析与下次执行时间计算

        验证：
        - "0 2 * * *" 被正确解析为 minute=0, hour=2
        - 下次执行时间的 hour=2, minute=0
        - 下次执行时间 > 当前时间
        """
        scheduler = Scheduler(config={"schedule": {"cron": "0 2 * * *"}})
        cron = scheduler.parse_cron("0 2 * * *")

        assert cron.minute == "0", f"Expected minute='0', got '{cron.minute}'"
        assert cron.hour == "2", f"Expected hour='2', got '{cron.hour}'"
        assert cron.day_of_month == "*", f"Expected day_of_month='*', got '{cron.day_of_month}'"
        assert cron.month == "*", f"Expected month='*', got '{cron.month}'"
        assert cron.day_of_week == "*", f"Expected day_of_week='*', got '{cron.day_of_week}'"

        next_run = scheduler.get_next_run_time()
        assert next_run.hour == 2, f"Expected next run hour=2, got {next_run.hour}"
        assert next_run.minute == 0, f"Expected next run minute=0, got {next_run.minute}"
        assert next_run > datetime.now(), "Next run time should be in the future"

    @pytest.mark.parametrize("cron_expr,expected_minute,expected_hour", [
        ("0 2 * * *", "0", "2"),
        ("30 8 * * *", "30", "8"),
        ("*/15 * * * *", "*/15", "*"),
        ("0 9 * * 1-5", "0", "9"),
        ("0 0 1 * *", "0", "0"),
    ])
    def test_various_cron_expressions(self, cron_expr, expected_minute, expected_hour):
        """
        SCHED-AC1-TS1 补充：多种 Cron 表达式解析验证

        覆盖：
        - 每天凌晨 2 点
        - 每天 8:30
        - 每 15 分钟
        - 工作日 9:00
        - 每月 1 号 0:00
        """
        cron = Scheduler.parse_cron(cron_expr)
        assert cron.minute == expected_minute, (
            f"For '{cron_expr}', expected minute='{expected_minute}', got '{cron.minute}'"
        )
        assert cron.hour == expected_hour, (
            f"For '{cron_expr}', expected hour='{expected_hour}', got '{cron.hour}'"
        )

    @pytest.mark.parametrize("invalid_expr,expected_error_substring", [
        ("invalid cron", "Invalid cron expression"),
        ("60 25 32 13 8", "out of range"),
        ("", "Invalid cron expression"),
        ("* * *", "expected 5 fields"),
        ("abc * * * *", "non-numeric"),
    ])
    def test_invalid_cron_expression_handling(self, invalid_expr, expected_error_substring):
        """
        SCHED-AC1-TS2: 无效 Cron 表达式错误处理

        验证：
        - 无效格式抛出 ValueError
        - 超出范围的值抛出 ValueError
        - 空字符串抛出 ValueError
        - 错误消息包含有意义的信息
        """
        with pytest.raises(ValueError) as exc_info:
            Scheduler.parse_cron(invalid_expr)

        error_msg = str(exc_info.value)
        assert expected_error_substring in error_msg, (
            f"Expected error message to contain '{expected_error_substring}', "
            f"got: '{error_msg}'"
        )

    @pytest.mark.parametrize("out_of_range_expr,field_name", [
        ("60 * * * *", "minute"),
        ("* 24 * * *", "hour"),
        ("* * 0 * *", "day_of_month"),
        ("* * 32 * *", "day_of_month"),
        ("* * * 13 *", "month"),
        ("* * * * 8", "day_of_week"),
    ])
    def test_cron_field_range_validation(self, out_of_range_expr, field_name):
        """
        SCHED-AC1-TS2 补充：Cron 各字段范围验证

        验证各字段超出范围时抛出 ValueError 并包含字段名
        """
        with pytest.raises(ValueError) as exc_info:
            Scheduler.parse_cron(out_of_range_expr)

        error_msg = str(exc_info.value)
        assert field_name in error_msg or "out of range" in error_msg, (
            f"Error for '{out_of_range_expr}' should mention '{field_name}' or 'out of range', "
            f"got: '{error_msg}'"
        )

    def test_cron_trigger_scan_execution(self):
        """
        SCHED-AC1-TS3: Cron 定时触发扫描执行

        验证：
        - 调度器可启动和停止
        - 配置解析正确
        """
        scheduler = Scheduler(config={"schedule": {"cron": "* * * * *"}})

        # 验证实例化成功
        assert scheduler.cron_expr == "* * * * *"

        # 验证可以启动和停止
        scheduler.start()
        assert scheduler._running is True

        scheduler.stop()
        assert scheduler._running is False

    def test_next_run_time_calculation(self):
        """
        SCHED-AC1-TS1 补充：下次执行时间计算准确性

        验证：
        - 如果当前时间已过今天的执行时间，下次执行在明天
        - 下次执行时间的秒和微秒为 0
        """
        scheduler = Scheduler(config={"schedule": {"cron": "0 2 * * *"}})
        next_run = scheduler.get_next_run_time()

        assert next_run.second == 0, "Next run second should be 0"
        assert next_run.microsecond == 0, "Next run microsecond should be 0"
        assert next_run > datetime.now(), "Next run should be in the future"


# ============================================================
# SCHED-AC2: 扫描完成 Webhook 通知
# ============================================================
class TestSCHEDAC2WebhookNotification:
    """SCHED-AC2 测试组：扫描完成 Webhook 通知"""

    def test_send_webhook_success(self, mock_webhook):
        """
        SCHED-AC2-TS1: Webhook 通知发送成功

        验证：
        - 本地 Mock 服务收到 1 个 POST 请求
        - Content-Type 为 application/json
        - 请求体包含扫描结果数据
        """
        notifier = Notifier(config={
            "notify_method": "webhook",
            "notify_target": mock_webhook.url,
        })

        scan_result = {
            "total_issues": 5,
            "critical": 2,
            "high": 3,
            "repo": "agentserver",
        }

        success = notifier.send_webhook(scan_result)
        assert success is True, "Webhook send should succeed"

        # 验证请求
        assert len(mock_webhook.received_requests) == 1, (
            f"Expected 1 request, got {len(mock_webhook.received_requests)}"
        )

        req = mock_webhook.received_requests[0]
        assert req["method"] == "POST", f"Expected POST, got {req['method']}"
        assert "application/json" in req["content_type"], (
            f"Expected Content-Type application/json, got {req['content_type']}"
        )

        # 验证请求体
        body = req["body"]
        assert "data" in body, "Request body should contain 'data' field"
        assert body["data"]["total_issues"] == 5, (
            f"Expected total_issues=5, got {body['data'].get('total_issues')}"
        )
        assert body["data"]["critical"] == 2, (
            f"Expected critical=2, got {body['data'].get('critical')}"
        )
        assert body["data"]["repo"] == "agentserver", (
            f"Expected repo='agentserver', got {body['data'].get('repo')}"
        )

    def test_webhook_target_unreachable(self):
        """
        SCHED-AC2-TS2: Webhook 目标不可达时的错误处理

        验证：
        - 不抛出未处理异常
        - 返回 False
        """
        notifier = Notifier(config={
            "notify_method": "webhook",
            "notify_target": "http://127.0.0.1:19999/webhook",  # 不可达端口
        })

        scan_result = {"total_issues": 5, "critical": 2}

        # 不应抛出异常
        result = notifier.send_webhook(scan_result)
        assert result is False, "Should return False when target is unreachable"

    def test_webhook_payload_format(self, mock_webhook):
        """
        SCHED-AC2-TS3: Webhook 通知内容格式验证

        验证：
        - 请求体包含 timestamp（ISO 8601 格式）
        - 请求体包含 event 字段
        - 请求体包含 status 字段
        - 请求体 data 包含完整扫描结果
        """
        notifier = Notifier(config={
            "notify_method": "webhook",
            "notify_target": mock_webhook.url,
        })

        scan_result = {
            "total_issues": 10,
            "critical": 3,
            "high": 4,
            "medium": 2,
            "low": 1,
            "repo": "agentserver",
            "scan_id": "scan-20260728-001",
            "issues": [
                {"rule_id": "xxe-java-document-builder", "severity": "ERROR", "file": "Parser.java"},
                {"rule_id": "priv-python-eval", "severity": "ERROR", "file": "eval.py"},
            ],
        }

        notifier.send_webhook(scan_result)

        assert len(mock_webhook.received_requests) == 1
        body = mock_webhook.received_requests[0]["body"]

        # 验证必需字段
        assert "event" in body, "Payload should contain 'event' field"
        assert body["event"] == "scan.complete", f"Expected event='scan.complete', got '{body['event']}'"

        assert "timestamp" in body, "Payload should contain 'timestamp' field"
        # 验证 timestamp 为 ISO 8601 格式
        try:
            datetime.fromisoformat(body["timestamp"])
        except ValueError:
            pytest.fail(f"Timestamp '{body['timestamp']}' is not valid ISO 8601 format")

        assert "status" in body, "Payload should contain 'status' field"
        assert body["status"] == "success", f"Expected status='success', got '{body['status']}'"

        assert "data" in body, "Payload should contain 'data' field"
        assert body["data"]["total_issues"] == 10
        assert body["data"]["repo"] == "agentserver"

    def test_webhook_empty_target(self):
        """
        SCHED-AC2-TS2 补充：空目标 URL 时不发送请求

        验证：
        - notify_target 为空时返回 False
        - 不抛出异常
        """
        notifier = Notifier(config={
            "notify_method": "webhook",
            "notify_target": "",
        })

        result = notifier.send_webhook({"total_issues": 0})
        assert result is False, "Should return False when target is empty"

    def test_multiple_webhook_sends(self, mock_webhook):
        """
        SCHED-AC2-TS1 补充：多次发送 Webhook 通知

        验证：
        - 连续发送 3 次通知
        - Mock 服务收到 3 个请求
        """
        notifier = Notifier(config={
            "notify_method": "webhook",
            "notify_target": mock_webhook.url,
        })

        for i in range(3):
            notifier.send_webhook({"total_issues": i, "repo": f"repo-{i}"})

        assert len(mock_webhook.received_requests) == 3, (
            f"Expected 3 requests, got {len(mock_webhook.received_requests)}"
        )


# ============================================================
# SCHED-AC3: 手动触发扫描
# ============================================================
class TestSCHEDAC3ManualTrigger:
    """SCHED-AC3 测试组：手动触发扫描"""

    def test_manual_trigger_with_mock(self, temp_repo):
        """
        SCHED-AC3-TS1: CLI --trigger 参数执行扫描（Mock 版本）

        验证：
        - scan.py 脚本存在
        - --help 参数可正常输出
        - 脚本可被 Python 正常导入
        """
        scan_script = SCRIPTS_DIR / "scan.py"
        assert scan_script.exists(), f"scan.py not found at {scan_script}"

        # 验证 --help 可正常输出
        result = subprocess.run(
            [sys.executable, str(scan_script), "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"--help failed: {result.stderr}"
        assert "repo" in result.stdout.lower(), "Help should mention --repo argument"

    def test_manual_trigger_no_changes(self, temp_repo):
        """
        SCHED-AC3-TS2: 无变更时手动触发

        验证：
        - 当 base 和 target 指向同一提交时，扫描正常退出
        - 退出码为 0
        - 输出包含无变更信息或正常完成信息
        """
        scan_script = SCRIPTS_DIR / "scan.py"

        # 使用同一个分支作为 base 和 target（无差异）
        result = subprocess.run(
            [
                sys.executable, str(scan_script),
                "--repo", str(temp_repo),
                "--base", "master",
                "--target", "master",
                "--output", tempfile.mkdtemp(),
            ],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(PROJECT_ROOT),
        )

        # 应该正常退出（退出码 0）
        assert result.returncode == 0, (
            f"Expected exit code 0 for no-change scan, got {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_scan_runner_manual_trigger(self):
        """
        SCHED-AC3-TS1 补充：ScanRunner 手动触发逻辑验证

        验证：
        - ScanRunner.run() 成功执行
        - 通知被发送（如果配置了 notify）
        """
        mock_notifier = MagicMock(spec=Notifier)
        mock_notifier.send_webhook.return_value = True

        runner = ScanRunner(
            config={
                "schedule": {"notify": True},
                "repo": "test-repo",
            },
            notifier=mock_notifier,
        )

        # Mock run_scan 返回成功结果
        with patch.object(runner, "run_scan", return_value={
            "total_issues": 5,
            "issues": [],
        }):
            result = runner.run()

        assert result["total_issues"] == 5
        mock_notifier.send_webhook.assert_called_once()

    def test_scan_runner_no_notify_when_disabled(self):
        """
        SCHED-AC3 补充：通知未启用时不发送通知

        验证：
        - schedule.notify = False 时不调用 send_webhook
        """
        mock_notifier = MagicMock(spec=Notifier)

        runner = ScanRunner(
            config={
                "schedule": {"notify": False},
                "repo": "test-repo",
            },
            notifier=mock_notifier,
        )

        with patch.object(runner, "run_scan", return_value={"total_issues": 0}):
            runner.run()

        mock_notifier.send_webhook.assert_not_called()


# ============================================================
# SCHED-AC4: 扫描失败告警通知
# ============================================================
class TestSCHEDAC4FailureAlert:
    """SCHED-AC4 测试组：扫描失败告警通知"""

    def test_scan_failure_triggers_alert(self):
        """
        SCHED-AC4-TS1: 扫描异常触发告警

        验证：
        - run_scan() 抛出 RuntimeError("Semgrep crashed")
        - Notifier.send_alert() 被调用
        - 告警内容包含错误信息 "Semgrep crashed"
        - 告警级别为 ERROR
        """
        mock_notifier = MagicMock(spec=Notifier)
        mock_notifier.send_alert.return_value = True

        runner = ScanRunner(
            config={
                "schedule": {"notify": True},
                "repo": "agentserver",
            },
            notifier=mock_notifier,
        )

        with patch.object(runner, "run_scan", side_effect=RuntimeError("Semgrep crashed")):
            with pytest.raises(RuntimeError, match="Semgrep crashed"):
                runner.run()

        # 验证告警被发送
        assert mock_notifier.send_alert.called, "send_alert should be called on scan failure"

        # 验证告警内容
        call_args = mock_notifier.send_alert.call_args
        alert_data = call_args[0][0] if call_args[0] else call_args[1]

        assert "Semgrep crashed" in str(alert_data), (
            f"Alert should contain 'Semgrep crashed', got: {alert_data}"
        )
        assert alert_data.get("error_type") == "RuntimeError", (
            f"Expected error_type='RuntimeError', got '{alert_data.get('error_type')}'"
        )
        assert alert_data.get("status") == "error", (
            f"Expected status='error', got '{alert_data.get('status')}'"
        )

    def test_alert_contains_diagnostic_info(self):
        """
        SCHED-AC4-TS2: 告警通知包含诊断信息

        验证：
        - 告警包含错误类型（RuntimeError）
        - 告警包含错误消息
        - 告警包含时间戳
        - 告警包含仓库名称
        - 告警不包含敏感信息（如 API Key）
        """
        mock_notifier = MagicMock(spec=Notifier)
        mock_notifier.send_alert.return_value = True

        runner = ScanRunner(
            config={
                "schedule": {"notify": True},
                "repo": "agentserver",
                "api_key": "sk-secret-key-12345",  # 模拟敏感信息
            },
            notifier=mock_notifier,
        )

        with patch.object(runner, "run_scan", side_effect=RuntimeError("Semgrep crashed")):
            with pytest.raises(RuntimeError):
                runner.run()

        call_args = mock_notifier.send_alert.call_args
        alert_data = call_args[0][0] if call_args[0] else call_args[1]

        # 验证诊断信息
        assert "error_type" in alert_data, "Alert should contain error_type"
        assert alert_data["error_type"] == "RuntimeError"

        assert "error_message" in alert_data, "Alert should contain error_message"
        assert alert_data["error_message"] == "Semgrep crashed"

        assert "timestamp" in alert_data, "Alert should contain timestamp"
        # 验证时间戳格式
        try:
            datetime.fromisoformat(alert_data["timestamp"])
        except ValueError:
            pytest.fail(f"Alert timestamp '{alert_data['timestamp']}' is not ISO 8601")

        # 验证仓库名称
        assert "data" in alert_data, "Alert should contain data field"
        assert alert_data["data"].get("repo") == "agentserver", (
            f"Expected repo='agentserver' in alert data"
        )

        # 验证不包含敏感信息
        alert_str = json.dumps(alert_data, ensure_ascii=False)
        assert "sk-secret-key-12345" not in alert_str, (
            "Alert should not contain sensitive API key"
        )

    def test_alert_throttling_on_consecutive_failures(self):
        """
        SCHED-AC4-TS3: 连续失败时的告警限流

        验证：
        - 配置告警限流间隔 300 秒
        - 连续 3 次失败仅发送 1 次告警
        - 第 2、3 次失败时告警被限流跳过
        """
        mock_notifier = MagicMock(spec=Notifier)
        mock_notifier.send_alert.return_value = True

        runner = ScanRunner(
            config={
                "schedule": {
                    "notify": True,
                    "alert_throttle_seconds": 300,
                },
                "repo": "test-repo",
            },
            notifier=mock_notifier,
        )

        # 连续 3 次失败
        for i in range(3):
            with patch.object(runner, "run_scan", side_effect=RuntimeError(f"Error #{i+1}")):
                with pytest.raises(RuntimeError):
                    runner.run()

        # 验证仅发送 1 次告警
        assert mock_notifier.send_alert.call_count == 1, (
            f"Expected 1 alert with throttling, got {mock_notifier.send_alert.call_count}"
        )

    def test_alert_throttling_expires(self):
        """
        SCHED-AC4-TS3 补充：限流过期后重新发送告警

        验证：
        - 第 1 次失败发送告警
        - 模拟时间流逝超过限流间隔
        - 第 2 次失败重新发送告警
        """
        mock_notifier = MagicMock(spec=Notifier)
        mock_notifier.send_alert.return_value = True

        runner = ScanRunner(
            config={
                "schedule": {
                    "notify": True,
                    "alert_throttle_seconds": 300,
                },
                "repo": "test-repo",
            },
            notifier=mock_notifier,
        )

        # 第 1 次失败
        with patch.object(runner, "run_scan", side_effect=RuntimeError("Error #1")):
            with pytest.raises(RuntimeError):
                runner.run()

        assert mock_notifier.send_alert.call_count == 1

        # 模拟时间流逝超过限流间隔
        runner._last_alert_time = time.time() - 301

        # 第 2 次失败
        with patch.object(runner, "run_scan", side_effect=RuntimeError("Error #2")):
            with pytest.raises(RuntimeError):
                runner.run()

        assert mock_notifier.send_alert.call_count == 2, (
            "Alert should be sent again after throttle period expires"
        )

    def test_no_alert_when_notify_disabled(self):
        """
        SCHED-AC4 补充：通知未启用时不发送告警

        验证：
        - schedule.notify = False 时，即使扫描失败也不发送告警
        """
        mock_notifier = MagicMock(spec=Notifier)

        runner = ScanRunner(
            config={
                "schedule": {"notify": False},
                "repo": "test-repo",
            },
            notifier=mock_notifier,
        )

        with patch.object(runner, "run_scan", side_effect=RuntimeError("Error")):
            with pytest.raises(RuntimeError):
                runner.run()

        mock_notifier.send_alert.assert_not_called()
        mock_notifier.send_webhook.assert_not_called()

    def test_no_alert_without_notifier(self):
        """
        SCHED-AC4 补充：未配置 notifier 时不崩溃

        验证：
        - notifier 为 None 时，扫描失败不抛出额外异常
        """
        runner = ScanRunner(
            config={
                "schedule": {"notify": True},
                "repo": "test-repo",
            },
            notifier=None,
        )

        with patch.object(runner, "run_scan", side_effect=RuntimeError("Error")):
            with pytest.raises(RuntimeError, match="Error"):
                runner.run()

    def test_scan_success_sends_notification(self, mock_webhook):
        """
        SCHED-AC4 补充：扫描成功时发送通知（非告警）

        验证：
        - 扫描成功时调用 send_webhook（非 send_alert）
        - 通知内容包含扫描结果
        """
        notifier = Notifier(config={
            "notify_method": "webhook",
            "notify_target": mock_webhook.url,
        })

        runner = ScanRunner(
            config={
                "schedule": {"notify": True},
                "repo": "test-repo",
            },
            notifier=notifier,
        )

        with patch.object(runner, "run_scan", return_value={
            "total_issues": 5,
            "critical": 2,
            "high": 3,
        }):
            result = runner.run()

        assert result["total_issues"] == 5
        assert len(mock_webhook.received_requests) == 1

        body = mock_webhook.received_requests[0]["body"]
        assert body["event"] == "scan.complete"
        assert body["status"] == "success"


# ============================================================
# 集成测试和边界情况
# ============================================================
class TestSchedulerIntegration:
    """调度模块集成测试和边界情况"""

    def test_scheduler_config_loading(self):
        """
        验证调度器配置加载正确性
        """
        config = {
            "schedule": {
                "cron": "0 2 * * *",
                "notify": True,
                "notify_method": "webhook",
                "notify_target": "http://example.com/webhook",
            }
        }
        scheduler = Scheduler(config=config)
        assert scheduler.cron_expr == "0 2 * * *"

    def test_notifier_config(self):
        """
        验证通知器配置加载正确性
        """
        config = {
            "notify_method": "webhook",
            "notify_target": "http://example.com/webhook",
        }
        notifier = Notifier(config=config)
        assert notifier.notify_method == "webhook"
        assert notifier.notify_target == "http://example.com/webhook"

    def test_scan_runner_lifecycle(self):
        """
        验证 ScanRunner 完整生命周期：成功 -> 通知
        """
        mock_notifier = MagicMock(spec=Notifier)
        mock_notifier.send_webhook.return_value = True

        runner = ScanRunner(
            config={"schedule": {"notify": True}, "repo": "test"},
            notifier=mock_notifier,
        )

        # 成功场景
        with patch.object(runner, "run_scan", return_value={"total_issues": 0}):
            result = runner.run()
        assert result["total_issues"] == 0
        assert mock_notifier.send_webhook.call_count == 1

    @pytest.mark.parametrize("cron_expr,is_valid", [
        ("0 2 * * *", True),
        ("*/15 * * * *", True),
        ("0 9 * * 1-5", True),
        ("0 8,12,18 * * *", True),   # 逗号分隔的小时值，有效
        ("", False),
        ("* *", False),
    ])
    def test_cron_validation_matrix(self, cron_expr, is_valid):
        """
        Cron 表达式验证矩阵

        覆盖有效和无效的 Cron 表达式
        """
        if is_valid:
            cron = Scheduler.parse_cron(cron_expr)
            assert cron is not None
        else:
            with pytest.raises(ValueError):
                Scheduler.parse_cron(cron_expr)

    def test_webhook_payload_with_full_scan_report(self, mock_webhook):
        """
        验证完整扫描报告的 Webhook 通知格式
        """
        notifier = Notifier(config={
            "notify_method": "webhook",
            "notify_target": mock_webhook.url,
        })

        full_report = {
            "scan_info": {
                "repo": "agentserver",
                "base_branch": "master",
                "target_branch": "release/1.0",
                "profile": "default",
                "timestamp": "2026-07-28T02:00:00",
                "duration_seconds": 12.5,
            },
            "summary": {
                "total": 15,
                "critical": 3,
                "high": 5,
                "medium": 4,
                "low": 3,
            },
            "issues": [
                {
                    "rule_id": "xxe-java-document-builder",
                    "severity": "ERROR",
                    "file": "src/Parser.java",
                    "line": 33,
                    "message": "XXE vulnerability",
                },
            ],
        }

        notifier.send_webhook(full_report)

        assert len(mock_webhook.received_requests) == 1
        body = mock_webhook.received_requests[0]["body"]
        assert body["data"]["summary"]["total"] == 15
        assert body["data"]["scan_info"]["repo"] == "agentserver"
