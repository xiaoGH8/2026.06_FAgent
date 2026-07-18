from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from typing import Any

from backend.config.settings import load_agent_config


@dataclass
class ModelStatus:
    mode: str
    provider: str
    model: str
    configured: bool
    reason: str


class ModelFactory:
    """OpenAI-compatible LLM facade for one explicitly configured service."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or load_agent_config()
        self._last_call_time = 0.0
        self._qps_lock = threading.Lock()
        self._min_interval = 1.0 / 5

    @property
    def config_name(self) -> str:
        return str(self.config.get("config_name") or "LLM")

    def status(self) -> ModelStatus:
        api_key = str(self.config.get("llm_api_key") or "")
        configured = bool(api_key and api_key.isascii())
        provider = str(self.config.get("llm_provider") or "rule")
        model = str(self.config.get("llm_model") or "rule-agent")
        return ModelStatus(
            mode="llm" if configured else "rule",
            provider=provider,
            model=model,
            configured=configured,
            reason=(
                f"{self.config_name} key configured"
                if configured
                else f"{self.config_name}_API_KEY is empty or invalid"
            ),
        )

    def chat_with_metadata(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        timeout: int = 90,
    ) -> dict[str, Any]:
        with self._qps_lock:
            now = time.time()
            wait_time = self._last_call_time + self._min_interval - now
            if wait_time > 0:
                time.sleep(wait_time)
            self._last_call_time = time.time()

        status = self.status()
        if not status.configured:
            raise RuntimeError(f"{self.config_name}_API_KEY is empty")
        base_url = str(self.config.get("llm_base_url") or "").rstrip("/")
        if not base_url:
            raise RuntimeError(f"{self.config_name}_BASE_URL is empty")

        payload: dict[str, Any] = {"model": status.model, "messages": messages}
        if temperature is not None:
            payload["temperature"] = temperature
        if status.model.startswith("deepseek-v4"):
            payload["reasoning_effort"] = self.config.get("reasoning_effort", "high")

        request_id = uuid.uuid4().hex
        started = time.time()
        request = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config['llm_api_key']}",
                "Content-Type": "application/json",
                "X-Client-Request-Id": request_id,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
                response_request_id = response.headers.get("x-request-id") or response.headers.get("request-id")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")[:500]
            raise RuntimeError(f"{self.config_name} HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError, UnicodeEncodeError) as exc:
            raise RuntimeError(f"{self.config_name} connection failed: {exc}") from exc

        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError(f"{self.config_name} response has no choices")
        message = choices[0].get("message") or {}
        content = message.get("content") or choices[0].get("text")
        if not content:
            raise RuntimeError(f"{self.config_name} response has no content")
        return {
            "content": str(content).strip(),
            "provider": status.provider,
            "model": status.model,
            "request_id": response_request_id or request_id,
            "duration_ms": int((time.time() - started) * 1000),
            "usage": data.get("usage") or {},
        }

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        timeout: int = 90,
    ) -> str:
        return str(self.chat_with_metadata(messages, temperature=temperature, timeout=timeout)["content"])