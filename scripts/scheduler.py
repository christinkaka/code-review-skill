#!/usr/bin/env python3
"""
调度器模块 - Cron 定时扫描调度

提供 Scheduler 类，支持：
- Cron 表达式解析与验证
- 定时触发扫描
- 手动触发扫描
- 下次执行时间计算

用法:
    from scheduler import Scheduler, CronExpression

    scheduler = Scheduler(config={"schedule": {"cron": "0 2 * * *"}})
    scheduler.start()
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Callable, Dict, Optional

logger = logging.getLogger("code-review.scheduler")


# ============================================================
# CronExpression 数据类
# ============================================================
class CronExpression:
    """
    Cron 表达式解析结果

    Attributes:
        minute: 分钟字段 (0-59, *, */N)
        hour: 小时字段 (0-23, *, */N)
        day_of_month: 日字段 (1-31, *, */N)
        month: 月字段 (1-12, *, */N)
        day_of_week: 星期字段 (0-7, *, */N, 逗号分隔列表, 范围)
    """

    def __init__(
        self,
        minute: str,
        hour: str,
        day_of_month: str,
        month: str,
        day_of_week: str,
    ):
        self.minute = minute
        self.hour = hour
        self.day_of_month = day_of_month
        self.month = month
        self.day_of_week = day_of_week

    def __repr__(self) -> str:
        return (
            f"CronExpression(minute={self.minute}, hour={self.hour}, "
            f"day_of_month={self.day_of_month}, month={self.month}, "
            f"day_of_week={self.day_of_week})"
        )

    def __eq__(self, other) -> bool:
        if not isinstance(other, CronExpression):
            return False
        return (
            str(self.minute) == str(other.minute)
            and str(self.hour) == str(other.hour)
            and str(self.day_of_month) == str(other.day_of_month)
            and str(self.month) == str(other.month)
            and str(self.day_of_week) == str(other.day_of_week)
        )


# ============================================================
# Scheduler 调度器
# ============================================================
class Scheduler:
    """
    Cron 定时调度器

    支持标准 5 字段 Cron 表达式：
        minute hour day_of_month month day_of_week

    各字段取值范围：
        minute:       0-59
        hour:         0-23
        day_of_month: 1-31
        month:        1-12
        day_of_week:  0-7 (0 和 7 均表示周日)

    支持的语法：
        *       每个（所有值）
        N       具体数值
        */N     每 N 个单位
        N,M,K   逗号分隔的列表
        N-M     范围

    Args:
        config: 配置字典，预期格式:
            {
                "schedule": {
                    "cron": "0 2 * * *",
                    "notify": True,
                    "notify_method": "webhook",
                    "notify_target": "http://example.com/webhook",
                    "alert_throttle_seconds": 300,
                }
            }
        scan_callback: 扫描回调函数，cron 触发时调用
    """

    def __init__(
        self,
        config: Optional[Dict] = None,
        scan_callback: Optional[Callable] = None,
    ):
        self.config = config or {}
        schedule_config = self.config.get("schedule", {})
        self.cron_expr: str = schedule_config.get("cron", "")
        self._scan_callback = scan_callback
        self._running: bool = False
        self._thread: Optional[threading.Thread] = None

    # ---------------------------------------------------------
    # Cron 表达式解析
    # ---------------------------------------------------------
    @staticmethod
    def parse_cron(expression: str) -> CronExpression:
        """
        解析 cron 表达式并验证各字段合法性

        Args:
            expression: 5 字段 cron 表达式字符串

        Returns:
            CronExpression 实例

        Raises:
            ValueError: 表达式格式错误或字段值超出范围
        """
        if not expression or not expression.strip():
            raise ValueError("Invalid cron expression: empty string")

        parts = expression.strip().split()
        if len(parts) != 5:
            raise ValueError(
                f"Invalid cron expression: expected 5 fields, got {len(parts)}"
            )

        minute, hour, dom, month, dow = parts

        # 字段验证规则：(字段名, 最小值, 最大值)
        field_specs = [
            (minute, "minute", 0, 59),
            (hour, "hour", 0, 23),
            (dom, "day_of_month", 1, 31),
            (month, "month", 1, 12),
            (dow, "day_of_week", 0, 7),
        ]

        for value, name, min_val, max_val in field_specs:
            Scheduler._validate_field(value, name, min_val, max_val)

        return CronExpression(minute, hour, dom, month, dow)

    @staticmethod
    def _validate_field(value: str, name: str, min_val: int, max_val: int) -> None:
        """
        验证单个 cron 字段的合法性

        支持: *, */N, N, N-M, N,M,K 以及组合

        Raises:
            ValueError: 字段值不合法
        """
        if value == "*":
            return

        # */N 步长语法
        if value.startswith("*/"):
            step_str = value[2:]
            try:
                num = int(step_str)
                if num < min_val or num > max_val:
                    raise ValueError(
                        f"Invalid cron expression: {name} value {num} "
                        f"out of range [{min_val}-{max_val}]"
                    )
            except ValueError as e:
                if "out of range" in str(e):
                    raise
                raise ValueError(
                    f"Invalid cron expression: {name} field contains "
                    f"non-numeric value '{step_str}'"
                )
            return

        # 逗号分隔列表（如 1,2,3 或 8,12,18）
        for part in value.split(","):
            # 范围语法（如 1-5 或 9-17）
            if "-" in part:
                range_parts = part.split("-")
                if len(range_parts) != 2:
                    raise ValueError(
                        f"Invalid cron expression: {name} field "
                        f"contains invalid range '{part}'"
                    )
                for rp in range_parts:
                    try:
                        num = int(rp)
                        if num < min_val or num > max_val:
                            raise ValueError(
                                f"Invalid cron expression: {name} value {num} "
                                f"out of range [{min_val}-{max_val}]"
                            )
                    except ValueError as e:
                        if "out of range" in str(e):
                            raise
                        raise ValueError(
                            f"Invalid cron expression: {name} field contains "
                            f"non-numeric value '{rp}'"
                        )
            else:
                # 单个数值
                try:
                    num = int(part)
                    if num < min_val or num > max_val:
                        raise ValueError(
                            f"Invalid cron expression: {name} value {num} "
                            f"out of range [{min_val}-{max_val}]"
                        )
                except ValueError as e:
                    if "out of range" in str(e):
                        raise
                    raise ValueError(
                        f"Invalid cron expression: {name} field contains "
                        f"non-numeric value '{part}'"
                    )

    # ---------------------------------------------------------
    # 下次执行时间计算
    # ---------------------------------------------------------
    def get_next_run_time(self) -> datetime:
        """
        根据 cron 表达式计算下次执行时间

        Returns:
            datetime: 下次执行时间（秒和微秒为 0，且在未来）
        """
        cron = self.parse_cron(self.cron_expr)
        now = datetime.now()

        # 确定目标小时和分钟
        target_hour = 0 if cron.hour == "*" else int(cron.hour)
        target_minute = 0 if cron.minute == "*" else int(cron.minute)

        # 从今天当前时间开始查找
        candidate = now.replace(second=0, microsecond=0)
        candidate = candidate.replace(hour=target_hour, minute=target_minute)

        # 如果今天的执行时间已过，推到明天
        if candidate <= now:
            candidate += timedelta(days=1)

        return candidate

    # ---------------------------------------------------------
    # 调度器生命周期
    # ---------------------------------------------------------
    def start(self) -> None:
        """启动调度器，在后台线程中按 cron 周期执行扫描"""
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("调度器已启动, cron: %s", self.cron_expr)

    def stop(self) -> None:
        """停止调度器"""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("调度器已停止")

    def _run_loop(self) -> None:
        """调度器主循环：等待直到满足 cron 条件后触发扫描"""
        while self._running:
            try:
                next_run = self.get_next_run_time()
                now = datetime.now()
                wait_seconds = (next_run - now).total_seconds()

                # 分段等待，以便能及时响应 stop()
                while wait_seconds > 0 and self._running:
                    time.sleep(min(1.0, wait_seconds))
                    wait_seconds = (next_run - datetime.now()).total_seconds()

                if self._running and self._scan_callback:
                    logger.info("Cron 触发扫描执行")
                    try:
                        self._scan_callback()
                    except Exception as e:
                        logger.error("Cron 触发扫描失败: %s", e)

            except Exception as e:
                logger.error("调度器循环异常: %s", e)
                time.sleep(1)
