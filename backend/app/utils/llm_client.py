"""
LLM客户端封装
统一使用OpenAI格式调用
"""

import json
import re
import time
from typing import Optional, Dict, Any, List
from openai import OpenAI

from ..config import Config

import logging
_log = logging.getLogger("airwave.llm")


class LLMClient:
    """LLM客户端"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model = model or Config.LLM_MODEL_NAME
        
        if not self.api_key:
            raise ValueError("LLM_API_KEY 未配置")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None,
        extra_body: Optional[Dict] = None,
    ) -> str:
        """
        发送聊天请求
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            response_format: 响应格式（如JSON模式）
            
        Returns:
            模型响应文本
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format:
            kwargs["response_format"] = response_format

        if extra_body:
            kwargs["extra_body"] = extra_body

        # Retry on rate-limit (429) with exponential back-off
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                response = self.client.chat.completions.create(**kwargs)
                break
            except Exception as exc:
                err_str = str(exc).lower()
                if any(k in err_str for k in ("429", "rate limit", "quota", "resource_exhausted")):
                    wait = 8 * (2 ** attempt)   # 8s → 16s → 32s
                    _log.warning(f"Rate limited (attempt {attempt+1}/3) — waiting {wait}s: {exc}")
                    time.sleep(wait)
                    last_exc = exc
                    continue
                raise
        else:
            raise RuntimeError(f"LLM call failed after 3 retries: {last_exc}")
        msg = response.choices[0].message
        content = msg.content

        # Gemini 2.5 Flash (thinking model) sometimes returns content=None via
        # the OpenAI-compat layer when no response_format is specified.
        # Retry once with JSON mode to coerce a real response, then unwrap it.
        if content is None and response_format is None:
            kwargs["response_format"] = {"type": "json_object"}
            # Append instruction so the model wraps output in {"text": "..."}
            patched = list(messages)
            patched[-1] = {
                "role": patched[-1]["role"],
                "content": patched[-1]["content"] + '\n\nRespond with JSON: {"text": "<your full response here>"}',
            }
            kwargs["messages"] = patched
            retry = self.client.chat.completions.create(**kwargs)
            retry_content = retry.choices[0].message.content or ""
            try:
                parsed = json.loads(retry_content)
                content = parsed.get("text") or retry_content
            except Exception:
                content = retry_content

        if content is None:
            content = ""
        if not isinstance(content, str):
            content = str(content)

        # Strip inline <think>…</think> blocks exposed by some models
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        return content
    
    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        extra_body: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        发送聊天请求并返回JSON

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            extra_body: Extra parameters forwarded to the API (e.g. thinking_config)

        Returns:
            解析后的JSON对象
        """
        response = self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            extra_body=extra_body,
        )
        # Try to parse JSON from the response, handling common model quirks:
        # 1. Response wrapped in ```json ... ``` code block
        # 2. Preamble prose before the JSON ("Here is the JSON requested:")
        # 3. Mix of both

        # First, try direct parse of the stripped response
        cleaned = response.strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Extract JSON from a ```json...``` code block (anywhere in the string)
        cb_match = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', cleaned, re.IGNORECASE)
        if cb_match:
            try:
                return json.loads(cb_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Extract the first complete {...} object from anywhere in the response
        brace_match = re.search(r'\{[\s\S]*\}', cleaned)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        # Partial-JSON recovery: model hit token limit mid-object.
        # Try to salvage whatever key:value pairs are present before truncation.
        partial = re.search(r'\{([\s\S]+)', cleaned)
        if partial:
            fragment = partial.group(1)
            # Extract individual "key": value pairs via regex
            recovered: dict = {}
            for m in re.finditer(r'"(\w+)"\s*:\s*("(?:[^"\\]|\\.)*"|[-\d.]+|true|false|null)', fragment):
                key, raw = m.group(1), m.group(2)
                try:
                    recovered[key] = json.loads(raw)
                except Exception:
                    pass
            if recovered:
                _log.warning(f"chat_json: partial JSON recovered ({list(recovered.keys())}); original was truncated")
                return recovered

        raise ValueError(f"LLM返回的JSON格式无效: {cleaned}")

