#!/usr/bin/env python3
"""
共享 LLM 客户端

供 AI 评审器（ai_reviewer.py）与规约预编译器（rule_compiler.py）共用的
OpenAI 兼容协议客户端。

设计要点：
- 可注入：调用方可传入自定义实例（测试用 FakeLLMClient 替换）
- 可用性显式检查：is_available() 明确告知是否具备调用条件
- 失败返回 None 而非抛异常：调用方决定降级策略
"""

import json
import logging
import os
import urllib.request
from typing import Dict, Optional

logger = logging.getLogger("code-review.llm")


class LLMClient:
    """OpenAI 兼容 Chat Completions 客户端"""

    def __init__(self, url: str = "", api_key: str = "", model: str = "",
                 timeout: int = 60):
        """
        Args:
            url: Chat Completions 接口地址（如 https://api.x.com/v1/chat/completions）
            api_key: API 密钥（也可通过 from_config 的环境变量名间接提供）
            model: 模型名
            timeout: 请求超时（秒）
        """
        self.url = url
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    # ------------------------------------------------------------
    # 工厂方法
    # ------------------------------------------------------------

    @classmethod
    def from_config(cls, cfg: Dict) -> "LLMClient":
        """
        从配置构造（ai_review.llm 段的格式）。

        支持格式：
            url / model / api_key_env（环境变量名）/ timeout
        """
        api_key_env = cfg.get("api_key_env", "")
        api_key = os.environ.get(api_key_env, "") if api_key_env else ""
        return cls(
            url=cfg.get("url", ""),
            api_key=api_key,
            model=cfg.get("model", ""),
            timeout=cfg.get("timeout", 60),
        )

    @classmethod
    def autodetect(cls, project_root=None) -> "LLMClient":
        """
        自动探测 LLM 配置，优先级：
        1. 环境变量：CODE_REVIEW_LLM_URL / CODE_REVIEW_LLM_KEY / CODE_REVIEW_LLM_MODEL
        2. 项目 config.yaml 的 ai_review.llm 段
        3. 都没有 -> 返回不可用的空客户端（调用方走降级路径）
        """
        # 1. 环境变量
        url = os.environ.get("CODE_REVIEW_LLM_URL", "")
        if url:
            return cls(
                url=url,
                api_key=os.environ.get("CODE_REVIEW_LLM_KEY", ""),
                model=os.environ.get("CODE_REVIEW_LLM_MODEL", ""),
            )

        # 2. config.yaml
        if project_root:
            config_path = os.path.join(str(project_root), "config.yaml")
            if os.path.exists(config_path):
                try:
                    import yaml
                    with open(config_path, "r", encoding="utf-8") as f:
                        config = yaml.safe_load(f) or {}
                    llm_cfg = config.get("ai_review", {}).get("llm", {})
                    if llm_cfg.get("url"):
                        return cls.from_config(llm_cfg)
                except Exception as e:
                    logger.warning(f"读取 config.yaml 失败: {e}")

        # 3. 不可用
        return cls()

    # ------------------------------------------------------------
    # 可用性与调用
    # ------------------------------------------------------------

    def is_available(self) -> bool:
        """具备调用条件（有 url 即可，key 可选 - 支持本地无鉴权 LLM）"""
        return bool(self.url)

    def chat(self, prompt: str, system: str = None, temperature: float = 0.0,
             max_tokens: int = 1024) -> Optional[str]:
        """
        发送一次对话请求。

        Args:
            prompt: 用户提示词
            system: 系统提示词（可选）
            temperature: 采样温度（规则编译等确定性场景应传 0.0）
            max_tokens: 最大输出 token

        Returns:
            模型回复文本；调用失败返回 None（不抛异常）
        """
        if not self.is_available():
            return None

        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": self.model or "gpt-4",
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            req = urllib.request.Request(
                self.url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result["choices"][0]["message"]["content"]

        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return None
