"""Token 统计功能测试"""
import pytest
from unittest.mock import Mock, patch
from ai_reviewer import AIReviewer


class TestTokenStats:
    """测试 token 统计功能"""

    def test_token_stats_initialization(self):
        """测试 token 统计初始化"""
        config = {
            "workflow": "security",
            "llm": {"model": "gpt-4", "url": "http://test.com"},
        }
        reviewer = AIReviewer(config)
        
        stats = reviewer.get_token_stats()
        assert stats["prompt_tokens"] == 0
        assert stats["completion_tokens"] == 0
        assert stats["total_tokens"] == 0
        assert stats["call_count"] == 0
        assert stats["model"] == "gpt-4"

    def test_token_stats_accumulation(self):
        """测试 token 统计累加"""
        config = {
            "workflow": "security",
            "llm": {"model": "gpt-4", "url": "http://test.com"},
        }
        reviewer = AIReviewer(config)
        
        # 模拟多次 LLM 调用
        reviewer.token_stats["prompt_tokens"] += 100
        reviewer.token_stats["completion_tokens"] += 50
        reviewer.token_stats["total_tokens"] += 150
        reviewer.token_stats["call_count"] += 1
        
        reviewer.token_stats["prompt_tokens"] += 200
        reviewer.token_stats["completion_tokens"] += 100
        reviewer.token_stats["total_tokens"] += 300
        reviewer.token_stats["call_count"] += 1
        
        stats = reviewer.get_token_stats()
        assert stats["prompt_tokens"] == 300
        assert stats["completion_tokens"] == 150
        assert stats["total_tokens"] == 450
        assert stats["call_count"] == 2

    @patch("urllib.request.urlopen")
    def test_call_llm_records_tokens(self, mock_urlopen):
        """测试 _call_llm 记录 token 消耗"""
        config = {
            "workflow": "security",
            "llm": {
                "model": "gpt-4",
                "url": "http://test.com/v1/chat/completions",
                "api_key_env": "TEST_API_KEY",
            },
        }
        reviewer = AIReviewer(config)
        
        # Mock LLM 响应
        mock_response = Mock()
        mock_response.read.return_value = b'''{
            "choices": [{"message": {"content": "test response"}}],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            }
        }'''
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        with patch.dict("os.environ", {"TEST_API_KEY": "test-key"}):
            result = reviewer._call_llm("test prompt")
        
        assert result == "test response"
        stats = reviewer.get_token_stats()
        assert stats["prompt_tokens"] == 100
        assert stats["completion_tokens"] == 50
        assert stats["total_tokens"] == 150
        assert stats["call_count"] == 1

    def test_get_token_stats_returns_copy(self):
        """测试 get_token_stats 返回副本"""
        config = {
            "workflow": "security",
            "llm": {"model": "gpt-4", "url": "http://test.com"},
        }
        reviewer = AIReviewer(config)
        
        stats1 = reviewer.get_token_stats()
        stats1["prompt_tokens"] = 999
        
        stats2 = reviewer.get_token_stats()
        assert stats2["prompt_tokens"] == 0  # 原始值未变
