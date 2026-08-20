#!/usr/bin/env python3
"""
调度器单元测试 (UT1) - 预留

覆盖 Scheduler.parse_cron() 的 cron 表达式解析：
- 有效 cron 表达式
- 无效 cron 表达式
- 边界情况

注意：调度器模块 (scripts/scheduler.py) 尚未实现，
本测试使用 conftest.py 中的 Scheduler 桩实现，
遵循 TDD 红-绿-重构流程。当实际模块实现后，应替换为真实实现。
"""

import pytest

# 从 conftest.py 中的桩实现导入 Scheduler
# 当 scripts/scheduler.py 实现后，改为: from scheduler import Scheduler
from conftest import Scheduler, CronExpression


# ===================================================================
# UT1: parse_cron() 正确解析 cron 表达式
# ===================================================================

class TestParseCronExpression:
    """测试有效 cron 表达式的解析"""

    @pytest.mark.parametrize("expression,expected", [
        # (cron 表达式, 预期解析结果属性字典)
        ("0 2 * * *", {
            "minute": "0",
            "hour": "2",
            "day_of_month": "*",
            "month": "*",
            "day_of_week": "*",
        }),
        ("30 8 * * 1,2,3,4,5", {
            "minute": "30",
            "hour": "8",
            "day_of_month": "*",
            "month": "*",
            "day_of_week": "1,2,3,4,5",
        }),
        ("0 0 1 * *", {
            "minute": "0",
            "hour": "0",
            "day_of_month": "1",
            "month": "*",
            "day_of_week": "*",
        }),
        ("*/15 * * * *", {
            "minute": "*/15",
            "hour": "*",
            "day_of_month": "*",
            "month": "*",
            "day_of_week": "*",
        }),
        ("0 0 * * 0", {
            "minute": "0",
            "hour": "0",
            "day_of_month": "*",
            "month": "*",
            "day_of_week": "0",
        }),
        ("5 4 * * *", {
            "minute": "5",
            "hour": "4",
            "day_of_month": "*",
            "month": "*",
            "day_of_week": "*",
        }),
    ])
    def test_parse_cron_expression(self, expression, expected):
        """UT1: 正确解析各种有效 cron 表达式"""
        result = Scheduler.parse_cron(expression)

        assert isinstance(result, CronExpression)
        for key, value in expected.items():
            actual = getattr(result, key)
            assert str(actual) == str(value), f"字段 {key} 预期 {value}，实际 {actual}"

    def test_parse_cron_returns_all_five_fields(self):
        """UT1: 解析结果包含完整的 5 个字段"""
        result = Scheduler.parse_cron("0 0 * * *")

        expected_attrs = {"minute", "hour", "day_of_month", "month", "day_of_week"}
        actual_attrs = {attr for attr in dir(result) if not attr.startswith("_")}
        assert expected_attrs.issubset(actual_attrs)

    @pytest.mark.parametrize("expression", [
        "0 2 * * *",       # 每天凌晨 2 点
        "*/5 * * * *",     # 每 5 分钟
        "0 0 1 1 *",       # 每年 1 月 1 日
        "0 0 * * 1,2,3,4,5",  # 工作日（逗号分隔）
        "30 2 * * 6,0",    # 周末凌晨 2:30
    ])
    def test_parse_cron_common_expressions(self, expression):
        """UT1: 常见 cron 表达式都能正确解析"""
        result = Scheduler.parse_cron(expression)
        assert isinstance(result, CronExpression)


# ===================================================================
# 无效 cron 表达式
# ===================================================================

class TestParseInvalidCron:
    """测试无效 cron 表达式的错误处理"""

    @pytest.mark.parametrize("expression", [
        "",                  # 空字符串
        "0 2",              # 字段不足
        "0 2 *",            # 字段不足
        "0 2 * *",          # 字段不足
        "0 2 * * * *",      # 字段过多（6 个字段）
    ])
    def test_parse_invalid_cron(self, expression):
        """UT1: 无效 cron 表达式抛出 ValueError"""
        with pytest.raises(ValueError):
            Scheduler.parse_cron(expression)

    @pytest.mark.parametrize("expression", [
        "abc * * * *",      # 非数字字段
        "60 * * * *",       # 分钟超出范围
        "* 25 * * *",       # 小时超出范围
        "* * 32 * *",       # 日超出范围
        "* * * 13 *",       # 月超出范围
        "* * * * 8",        # 星期超出范围
        "-1 * * * *",       # 负数
    ])
    def test_parse_invalid_cron_values(self, expression):
        """UT1: 超出范围的值抛出 ValueError"""
        with pytest.raises(ValueError):
            Scheduler.parse_cron(expression)

    def test_parse_invalid_cron_error_message(self):
        """UT1: 错误信息包含有用的上下文"""
        with pytest.raises(ValueError) as exc_info:
            Scheduler.parse_cron("invalid")

        # 错误信息应包含某种有意义的描述
        assert str(exc_info.value)


# ===================================================================
# 边界情况
# ===================================================================

class TestParseCronEdgeCases:
    """测试 cron 解析的边界情况"""

    @pytest.mark.parametrize("expression", [
        "0 0 * * *",        # 最小有效值
        "59 23 * * *",      # 最大有效值
        "0 0 1 1 0",        # 各字段最小值
        "59 23 31 12 7",    # 各字段最大值
    ])
    def test_parse_cron_boundary_values(self, expression):
        """UT1: 边界值的 cron 表达式能正确解析"""
        result = Scheduler.parse_cron(expression)
        assert isinstance(result, CronExpression)

    def test_parse_cron_with_spaces(self):
        """UT1: 多余空格被正确处理"""
        result = Scheduler.parse_cron("  0   2   *   *   *  ")
        assert isinstance(result, CronExpression)
        assert str(result.minute) == "0"
        assert str(result.hour) == "2"

    def test_parse_cron_step_values(self):
        """UT1: 步长值正确解析"""
        result = Scheduler.parse_cron("*/10 */2 * * *")
        assert str(result.minute) == "*/10"
        assert str(result.hour) == "*/2"

    def test_parse_cron_range_values(self):
        """UT1: 范围值（如 9-17）正确解析"""
        # 实际 scheduler.py 已实现，支持范围语法
        result = Scheduler.parse_cron("0 9-17 * * 1,2,3,4,5")
        assert isinstance(result, CronExpression)
        assert str(result.minute) == "0"
        assert str(result.hour) == "9-17"
        assert str(result.day_of_week) == "1,2,3,4,5"

    def test_parse_cron_list_values(self):
        """UT1: 列表值正确解析"""
        result = Scheduler.parse_cron("0 0 * * 1,3,5")
        assert isinstance(result, CronExpression)
