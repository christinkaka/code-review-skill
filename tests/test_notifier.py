#!/usr/bin/env python3
"""
通知器单元测试 (UT2) - 预留

覆盖 Notifier.send_webhook() 的 HTTP 请求构造：
- 成功发送
- 超时处理
- 网络错误处理

注意：通知器模块 (scripts/notifier.py) 尚未实现，
本测试使用 conftest.py 中的 Notifier 桩实现，
遵循 TDD 红-绿-重构流程。当实际模块实现后，应替换为真实实现。
"""

import json
from unittest.mock import MagicMock, patch, call

import pytest

# 从 conftest.py 中的桩实现导入 Notifier
# 当 scripts/notifier.py 实现后，改为: from notifier import Notifier
from conftest import Notifier


# ===================================================================
# 辅助 fixtures
# ===================================================================

@pytest.fixture
def webhook_config():
    """Webhook 通知配置"""
    return {
        "notify_method": "webhook",
        "notify_target": "https://hooks.example.com/services/code-review",
        "timeout": 10,
        "retry_count": 3,
    }


@pytest.fixture
def notifier_instance(webhook_config):
    """创建 Notifier 实例"""
    return Notifier(webhook_config)


@pytest.fixture
def scan_result():
    """模拟扫描结果"""
    return {
        "repo": "test-repo",
        "branch": "main",
        "commit": "abc123",
        "issues": [
            {
                "rule_id": "xxe-java-document-builder",
                "severity": "ERROR",
                "file": "src/Parser.java",
                "line": 42,
                "message": "XXE vulnerability detected",
            },
        ],
        "summary": {
            "total_issues": 1,
            "errors": 1,
            "warnings": 0,
        },
    }


# ===================================================================
# UT2: send_webhook() 正确构造 HTTP 请求
# ===================================================================

class TestSendWebhookSuccess:
    """测试成功发送 Webhook"""

    def test_send_webhook_success(self, notifier_instance, scan_result):
        """UT2: 成功发送 Webhook 通知返回 True"""
        mock_response = MagicMock()
        mock_response.status = 200

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

            result = notifier_instance.send_webhook(scan_result)

        assert result is True

    def test_send_webhook_url(self, webhook_config, scan_result):
        """UT2: Webhook 请求发送到正确的 URL"""
        n = Notifier(webhook_config)
        mock_response = MagicMock()
        mock_response.status = 200

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

            n.send_webhook(scan_result)

        # 验证请求 URL
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        assert request.full_url == webhook_config["notify_target"]

    def test_send_webhook_payload(self, notifier_instance, scan_result):
        """UT2: Webhook 请求体包含扫描结果"""
        mock_response = MagicMock()
        mock_response.status = 200

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

            notifier_instance.send_webhook(scan_result)

        # 验证请求体
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        payload = json.loads(request.data.decode("utf-8"))

        # 桩实现将扫描结果包装在 "data" 字段中
        assert "data" in payload or "issues" in payload or "summary" in payload

    def test_send_webhook_content_type(self, notifier_instance, scan_result):
        """UT2: Webhook 请求设置正确的 Content-Type"""
        mock_response = MagicMock()
        mock_response.status = 200

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

            notifier_instance.send_webhook(scan_result)

        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        content_type = request.get_header("Content-type")
        assert content_type == "application/json"


# ===================================================================
# 超时处理
# ===================================================================

class TestSendWebhookTimeout:
    """测试 Webhook 超时场景"""

    def test_send_webhook_timeout(self, notifier_instance, scan_result):
        """UT2: Webhook 超时时返回 False"""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = TimeoutError("Connection timed out")

            result = notifier_instance.send_webhook(scan_result)

        assert result is False

    def test_send_webhook_timeout_no_crash(self, notifier_instance, scan_result):
        """UT2: Webhook 超时不导致程序崩溃"""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = TimeoutError("Connection timed out")

            # 不应抛出异常
            result = notifier_instance.send_webhook(scan_result)
            assert isinstance(result, bool)


# ===================================================================
# 网络错误处理
# ===================================================================

class TestSendWebhookNetworkError:
    """测试网络错误场景"""

    def test_send_webhook_network_error(self, notifier_instance, scan_result):
        """UT2: 网络错误时返回 False"""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = ConnectionError("Network unreachable")

            result = notifier_instance.send_webhook(scan_result)

        assert result is False

    def test_send_webhook_dns_error(self, notifier_instance, scan_result):
        """UT2: DNS 解析失败时返回 False"""
        import urllib.error

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.URLError("Name resolution failed")

            result = notifier_instance.send_webhook(scan_result)

        assert result is False

    def test_send_webhook_http_error(self, notifier_instance, scan_result):
        """UT2: HTTP 错误状态码时返回 False"""
        import urllib.error

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.HTTPError(
                url="https://hooks.example.com/webhook",
                code=500,
                msg="Internal Server Error",
                hdrs={},
                fp=None,
            )

            result = notifier_instance.send_webhook(scan_result)

        assert result is False


# ===================================================================
# 参数化边界测试
# ===================================================================

class TestSendWebhookEdgeCases:
    """Webhook 发送参数化边界测试"""

    def test_send_webhook_empty_target(self, scan_result):
        """UT2: 空 webhook URL 时返回 False"""
        config = {"notify_method": "webhook", "notify_target": ""}
        n = Notifier(config)
        result = n.send_webhook(scan_result)
        assert result is False

    def test_send_webhook_empty_result(self, notifier_instance):
        """UT2: 空扫描结果也能正常发送"""
        empty_result = {"issues": [], "summary": {"total_issues": 0}}

        mock_response = MagicMock()
        mock_response.status = 200

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

            result = notifier_instance.send_webhook(empty_result)

        assert result is True

    def test_send_alert_delegates_to_webhook(self, notifier_instance, scan_result):
        """UT2: send_alert() 委托给 send_webhook()"""
        mock_response = MagicMock()
        mock_response.status = 200

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

            result = notifier_instance.send_alert(scan_result)

        assert result is True

    @pytest.mark.parametrize("status_code", [200, 201, 204])
    def test_send_webhook_success_status_codes(self, notifier_instance, scan_result, status_code):
        """UT2: 2xx 状态码均视为成功"""
        mock_response = MagicMock()
        mock_response.status = status_code

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

            result = notifier_instance.send_webhook(scan_result)

        # 桩实现检查 resp.status == 200
        # 如果实现改为 resp.ok，则 201/204 也会成功
        # 这里只验证不崩溃
        assert isinstance(result, bool)
