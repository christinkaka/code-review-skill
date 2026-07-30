#!/usr/bin/env python3
"""
通知器模块 - Webhook 通知与告警

提供 Notifier 类，支持：
- Webhook 通知发送（HTTP POST JSON）
- 告警通知发送
- 网络超时与错误处理
- 告警限流

用法:
    from notifier import Notifier

    notifier = Notifier(config={
        "notify_method": "webhook",
        "notify_target": "https://hooks.example.com/services/code-review",
    })
    notifier.send_webhook(scan_result)
"""

import json
import logging
import urllib.error
import urllib.request
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger("code-review.notifier")


class Notifier:
    """
    Webhook 通知器

    通过 HTTP POST 将扫描结果以 JSON 格式发送到指定的 Webhook 端点。

    通知载荷格式:
        {
            "event": "scan.complete",
            "timestamp": "2026-07-28T02:00:00.000000",
            "status": "success",
            "data": { ... scan_result ... }
        }

    Args:
        config: 通知配置字典，预期格式:
            {
                "notify_method": "webhook",
                "notify_target": "https://hooks.example.com/webhook",
                "timeout": 10,
                "retry_count": 3,
            }
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.notify_method: str = self.config.get("notify_method", "none")
        self.notify_target: str = self.config.get("notify_target", "")
        self._timeout: int = self.config.get("timeout", 10)
        self._retry_count: int = self.config.get("retry_count", 1)

    # ---------------------------------------------------------
    # Webhook 发送
    # ---------------------------------------------------------
    def send_webhook(self, scan_result: Dict) -> bool:
        """
        发送 Webhook 通知

        将扫描结果包装为标准载荷格式，通过 HTTP POST 发送到目标 URL。

        Args:
            scan_result: 扫描结果字典

        Returns:
            bool: 发送成功返回 True，失败返回 False
        """
        if not self.notify_target:
            logger.warning("Webhook 目标 URL 为空，跳过发送")
            return False

        payload = {
            "event": "scan.complete",
            "timestamp": self._now_iso(),
            "status": "success",
            "data": scan_result,
        }

        return self._do_send(payload)

    # ---------------------------------------------------------
    # 告警发送
    # ---------------------------------------------------------
    def send_alert(self, alert_data: Dict) -> bool:
        """
        发送告警通知

        告警数据通过 Webhook 通道发送。

        Args:
            alert_data: 告警数据字典，通常包含:
                - event: "scan.failure"
                - timestamp: ISO 8601 时间戳
                - status: "error"
                - error_type: 异常类型名
                - error_message: 异常消息
                - data: 附加诊断信息

        Returns:
            bool: 发送成功返回 True，失败返回 False
        """
        return self.send_webhook(alert_data)

    # ---------------------------------------------------------
    # 内部方法
    # ---------------------------------------------------------
    def _do_send(self, payload: Dict) -> bool:
        """
        执行 HTTP POST 请求发送载荷

        Args:
            payload: 要发送的 JSON 载荷

        Returns:
            bool: 2xx 响应视为成功，其他情况返回 False
        """
        try:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                self.notify_target,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                success = 200 <= resp.status < 300
                if success:
                    logger.info("Webhook 通知发送成功: %s", self.notify_target)
                else:
                    logger.warning(
                        "Webhook 返回非成功状态码: %d", resp.status
                    )
                return success
        except urllib.error.HTTPError as e:
            logger.error("Webhook HTTP 错误: %d %s", e.code, e.reason)
            return False
        except urllib.error.URLError as e:
            logger.error("Webhook URL 错误: %s", e.reason)
            return False
        except (ConnectionError, OSError, TimeoutError) as e:
            logger.error("Webhook 发送失败: %s", e)
            return False
        except Exception as e:
            logger.error("Webhook 发送未知错误: %s", e)
            return False

    @staticmethod
    def _now_iso() -> str:
        """返回当前时间的 ISO 8601 格式字符串"""
        return datetime.now().isoformat()


# ============================================================
# ScanRunner 扫描运行器
# ============================================================
class ScanRunner:
    """
    扫描运行器 - 封装扫描执行与通知/告警逻辑

    职责：
    - 调用 run_scan() 执行扫描
    - 扫描成功时通过 Notifier 发送通知
    - 扫描失败时通过 Notifier 发送告警
    - 支持告警限流（避免连续失败时告警风暴）

    Args:
        config: 配置字典，预期格式:
            {
                "schedule": {
                    "notify": True,
                    "alert_throttle_seconds": 300,
                },
                "repo": "test-repo",
            }
        notifier: Notifier 实例，为 None 时不发送通知
    """

    def __init__(
        self,
        config: Optional[Dict] = None,
        notifier: Optional[Notifier] = None,
    ):
        self.config = config or {}
        self.notifier = notifier
        self._last_alert_time: Optional[float] = None

    def run(self) -> Dict:
        """
        执行扫描并根据结果发送通知或告警

        Returns:
            Dict: 扫描结果

        Raises:
            Exception: 扫描失败时重新抛出原始异常
        """
        try:
            result = self.run_scan()
            # 扫描成功，发送通知
            if self._is_notify_enabled() and self.notifier:
                self.notifier.send_webhook(result)
            return result
        except Exception as e:
            # 扫描失败，发送告警（受限于限流策略）
            if self._is_notify_enabled() and self.notifier:
                throttle_seconds = self.config.get("schedule", {}).get(
                    "alert_throttle_seconds", 0
                )
                if self._should_send_alert(throttle_seconds):
                    alert_data = {
                        "event": "scan.failure",
                        "timestamp": self._now_iso(),
                        "status": "error",
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "data": {
                            "repo": self.config.get("repo", "unknown"),
                        },
                    }
                    self.notifier.send_alert(alert_data)
                    self._last_alert_time = __import__("time").time()
                else:
                    logger.warning("告警限流：跳过本次告警通知")
            raise

    def run_scan(self) -> Dict:
        """
        执行实际扫描（子类或外部可覆写）

        Returns:
            Dict: 扫描结果
        """
        return {"total_issues": 0, "issues": []}

    def _is_notify_enabled(self) -> bool:
        """检查通知是否启用"""
        return self.config.get("schedule", {}).get("notify", False)

    def _should_send_alert(self, throttle_seconds: int) -> bool:
        """
        检查是否应该发送告警（限流逻辑）

        Args:
            throttle_seconds: 限流间隔（秒），0 表示不限流

        Returns:
            bool: 是否应该发送告警
        """
        if throttle_seconds <= 0:
            return True
        if self._last_alert_time is None:
            return True
        elapsed = __import__("time").time() - self._last_alert_time
        return elapsed >= throttle_seconds

    @staticmethod
    def _now_iso() -> str:
        """返回当前时间的 ISO 8601 格式字符串"""
        return datetime.now().isoformat()
