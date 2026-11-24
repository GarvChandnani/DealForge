"""
DealForge Agents — LiteLLM Client Abstraction.

Provides a single entry point for all LLM calls in the agents module.
Model selection is fully config-driven — no provider is hardcoded.

Supported model prefixes (via LiteLLM):
  - gpt-4o, gpt-4o-mini       → OpenAI
  - claude-3-5-sonnet-...     → Anthropic
  - gemini/gemini-1.5-pro     → Google
  - ollama/llama3             → Ollama (local)
  - Any other LiteLLM-supported prefix

Usage:
    from agents.llm.litellm_client import LLMClient

    client = LLMClient()
    response = await client.chat([{"role": "user", "content": "Hello"}])
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import litellm
from litellm import acompletion

# Suppress verbose LiteLLM logs in production
litellm.set_verbose = os.getenv("APP_ENV", "development") == "development"


class LLMClient:
    """
    Thin wrapper around LiteLLM's async completion API.

    All API keys are read from environment variables — never stored here.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> None:
        self.model = model or os.getenv("LITELLM_DEFAULT_MODEL", "gpt-4o-mini")
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        """
        Send a chat completion request and return the assistant's message text.

        Args:
            messages: List of {"role": ..., "content": ...} dicts.
            model: Override the default model for this call.
            temperature: Override temperature for this call.
            max_tokens: Override max_tokens for this call.
            **kwargs: Additional kwargs passed through to litellm.acompletion.

        Returns:
            The assistant's response text.
        """
        response = await acompletion(
            model=model or self.model,
            messages=messages,
            temperature=temperature if temperature is not None else self.temperature,
            max_tokens=max_tokens or self.max_tokens,
            **kwargs,
        )
        return response.choices[0].message.content  # type: ignore[index]

    async def embed(self, text: str, model: Optional[str] = None) -> List[float]:
        """
        Generate an embedding for the given text.

        Args:
            text: Text to embed.
            model: Embedding model (defaults to text-embedding-3-small).

        Returns:
            List of floats representing the embedding vector.
        """
        embed_model = model or "text-embedding-3-small"
        response = await litellm.aembedding(model=embed_model, input=[text])
        return response.data[0]["embedding"]  # type: ignore[index]


# Module-level default client — configure per use-case
default_client = LLMClient()
