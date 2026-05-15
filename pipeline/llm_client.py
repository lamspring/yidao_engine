# -*- coding: utf-8 -*-
"""LLM API客户端"""
import time
import requests
from requests import HTTPError
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
            except HTTPError as e:
                status = e.response.status_code if e.response else 0
                msg = str(e)
                if status == 401:
                    msg = (
                        "HTTP 401 Unauthorized: API Key 无效或未设置。\n"
                        "  可能原因：\n"
                        "  1. 环境变量未设置（如 DEEPSEEK_API_KEY / OPENAI_API_KEY）\n"
                        "  2. API Key 已过期或被撤销\n"
                        "  3. 使用了错误的 provider（如默认 deepseek，但你只有 openai 的 key）\n"
                        "  解决：设置正确的环境变量，或使用 --provider 切换到你有 key 的提供商。"
                    )
                elif status == 403:
                    msg = "HTTP 403 Forbidden: API Key 无权限访问此模型，或账户余额不足。"
                elif status == 429:
                    msg = "HTTP 429 Too Many Requests: 请求过于频繁，请稍后再试。"
                elif status >= 500:
                    msg = f"HTTP {status} Server Error: 服务商端错误，请稍后重试。"
                last_error = Exception(msg)
                if attempt < self.cfg.max_retries:
                    wait = 2 ** attempt
                    print(f"  API 失败 (尝试 {attempt + 1}/{self.cfg.max_retries + 1}): {msg}")
                    print(f"  {wait}秒后重试...")
                    time.sleep(wait)
                else:
                    break
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
