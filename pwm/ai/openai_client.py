
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple
import os
import sys
import httpx

DEFAULT_OPENAI_API = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_MAX_TOKENS = 500
DEFAULT_TEMPERATURE = 0.7

@dataclass
class OpenAIClient:
    base_url: str
    api_key: str
    model: str
    max_tokens: int
    temperature: float

    def _debug(self, message: str) -> None:
        """Emit debug diagnostics when PWM_DEBUG is enabled."""
        if os.getenv("PWM_DEBUG") == "1":
            print(f"[DEBUG] OpenAIClient: {message}", file=sys.stderr)

    @classmethod
    def from_config(cls, cfg: dict) -> Optional['OpenAIClient']:
        """
        Create OpenAI client from config.

        Returns None if API key is not configured (graceful degradation).
        """
        openai = cfg.get("openai", {})
        api_key = openai.get("api_key")
        if not api_key:
            return None

        return cls(
            base_url=openai.get("base_url", DEFAULT_OPENAI_API).rstrip("/"),
            api_key=api_key,
            model=openai.get("model", DEFAULT_MODEL),
            max_tokens=openai.get("max_tokens", DEFAULT_MAX_TOKENS),
            temperature=openai.get("temperature", DEFAULT_TEMPERATURE)
        )

    def _headers(self) -> dict:
        """Generate request headers with authorization."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def ping(self) -> Tuple[bool, str]:
        """
        Test API connectivity.

        Returns:
            Tuple of (success: bool, message: str)
        """
        url = f"{self.base_url}/models"
        try:
            with httpx.Client(timeout=10.0) as c:
                r = c.get(url, headers=self._headers())
        except Exception as e:
            self._debug(f"ping network error: {type(e).__name__}")
            return False, f"network error: {e}"

        if r.status_code == 200:
            return True, "ok"
        elif r.status_code == 401:
            self._debug("ping unauthorized (401)")
            return False, "unauthorized (bad API key)"
        else:
            self._debug(f"ping returned HTTP {r.status_code}")
            return False, f"HTTP {r.status_code}"

    def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> Optional[str]:
        """
        Generate a completion using OpenAI Chat Completions API.

        Args:
            prompt: The user prompt/question
            system: Optional system message to set context
            max_tokens: Override default max_tokens for this request
            temperature: Override default temperature for this request

        Returns:
            Generated text or None on failure
        """
        url = f"{self.base_url}/chat/completions"

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
            "temperature": temperature if temperature is not None else self.temperature
        }

        try:
            with httpx.Client(timeout=30.0) as c:  # Longer timeout for AI
                r = c.post(url, headers=self._headers(), json=payload)

                if r.status_code == 200:
                    data = r.json()
                    choices = data.get("choices", [])
                    if choices and len(choices) > 0:
                        message = choices[0].get("message", {})
                        content = message.get("content", "")
                        return content.strip() if content else None
                self._debug(f"complete returned HTTP {r.status_code}")
        except Exception:
            self._debug("complete request raised exception")

        return None
