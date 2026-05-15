# -*- coding: utf-8 -*-
"""LLM API客户端"""
import time
import requests
from .config import LLMConfig


class LLMClient:
    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg
        self.headers = {
            "Authorization": f"Bearer {cfg.api_key}",
            "Content-Type": "application/json",
        }

    def call(self, system_prompt: str, user_prompt: str) -> tuple[str, dict]:
        """调用LLM API，支持重试"""
        payload = {
            "model": self.cfg.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.cfg.temperature,
            "max_tokens": self.cfg.max_tokens,
        }

        last_error = None
        for attempt in range(self.cfg.max_retries + 1):
            try:
                resp = requests.post(
                    f"{self.cfg.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=self.cfg.timeout,
                )
                resp.raise_for_status()
                result = resp.json()
                content = result["choices"][0]["message"]["content"]
                usage = result.get("usage", {})
                return content, usage
            except Exception as e:
                last_error = e
                if attempt < self.cfg.max_retries:
                    wait = 2 ** attempt
                    print(f"  API 失败 (尝试 {attempt + 1}/{self.cfg.max_retries + 1}): {e}")
                    print(f"  {wait}秒后重试...")
                    time.sleep(wait)
                else:
                    break

        raise last_error
