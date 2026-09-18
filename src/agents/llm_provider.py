"""
LLM Provider abstraction layer.
Wraps Ollama (via LangChain) so we can swap to cloud LLMs later.
"""

import json
import logging
from typing import Any

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from src.config import settings

logger = logging.getLogger(__name__)


class LLMProvider:
    """
    Abstraction over LLM providers.
    Currently supports Ollama (local). Designed to be extended for
    OpenAI, Anthropic, Google, etc.
    """

    def __init__(
        self,
        provider: str = "ollama",
        model: str | None = None,
        temperature: float = 0.1,
        base_url: str | None = None,
    ):
        self.provider = provider
        self.model = model or settings.ollama_model
        self.temperature = temperature

        if provider == "ollama":
            self.llm = ChatOllama(
                model=self.model,
                base_url=base_url or settings.ollama_base_url,
                temperature=temperature,
                format="json",  # Request JSON output
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

        logger.info(f"LLM Provider initialized: {provider}/{self.model}")

    def analyze(
        self,
        prompt: str,
        system_prompt: str = "You are a financial analyst AI assistant.",
    ) -> dict[str, Any]:
        """
        Send a prompt to the LLM and get a structured JSON response.

        Args:
            prompt: The user/analysis prompt
            system_prompt: System-level instructions

        Returns:
            Parsed JSON dict from the LLM response
        """
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=prompt),
        ]

        try:
            response = self.llm.invoke(messages)
            content = response.content

            # Parse JSON from response
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON from the response text
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    return json.loads(content[json_start:json_end])
                else:
                    logger.warning(f"LLM response is not valid JSON: {content[:200]}")
                    return {"error": "Invalid JSON response", "raw": content[:500]}

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return {"error": str(e)}

    def analyze_text(
        self,
        prompt: str,
        system_prompt: str = "You are a financial analyst AI assistant.",
    ) -> str:
        """
        Send a prompt and get a plain text response (no JSON parsing).
        """
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=prompt),
        ]
        try:
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return f"Error: {e}"

    def is_available(self) -> bool:
        """Check if the LLM is reachable."""
        try:
            import httpx
            resp = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False
