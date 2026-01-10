"""AI provider service - supports multiple free AI providers."""

import json
from abc import ABC, abstractmethod
from typing import Optional

import aiohttp

from app.config import settings


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate response from AI."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if provider is properly configured."""
        pass


class GeminiProvider(AIProvider):
    """Google Gemini API provider (free tier: 60 requests/min)."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model = model

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        url = f"{self.BASE_URL}/{self.model}:generateContent?key={self.api_key}"

        # Combine system prompt with user prompt
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        payload = {
            "contents": [
                {
                    "parts": [{"text": full_prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 1000,
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Gemini API error: {error_text}")

                data = await response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]


class OpenRouterProvider(AIProvider):
    """OpenRouter API provider (has free models)."""

    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    # Free models available on OpenRouter
    FREE_MODELS = [
        "mistralai/mistral-7b-instruct:free",
        "huggingfaceh4/zephyr-7b-beta:free",
        "openchat/openchat-7b:free",
        "google/gemma-7b-it:free",
    ]

    def __init__(self, api_key: str, model: Optional[str] = None):
        self.api_key = api_key
        self.model = model or self.FREE_MODELS[0]

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/lead-gen",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 1000,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.BASE_URL,
                headers=headers,
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"OpenRouter API error: {error_text}")

                data = await response.json()
                return data["choices"][0]["message"]["content"]


class OllamaProvider(AIProvider):
    """Ollama provider for local models (completely free)."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2"):
        self.base_url = base_url
        self.model = model

    def is_configured(self) -> bool:
        # Ollama is always "configured" if you have it running locally
        return True

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        url = f"{self.base_url}/api/generate"

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
            }
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=60) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Ollama API error: {error_text}")

                    data = await response.json()
                    return data["response"]
        except aiohttp.ClientError:
            raise Exception("Ollama is not running. Start it with: ollama serve")


class GroqProvider(AIProvider):
    """Groq API provider (very fast, generous free tier)."""

    BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, api_key: str, model: str = "llama-3.1-8b-instant"):
        self.api_key = api_key
        self.model = model

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 1000,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.BASE_URL,
                headers=headers,
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Groq API error: {error_text}")

                data = await response.json()
                return data["choices"][0]["message"]["content"]


class AIService:
    """
    Unified AI service that supports multiple providers.

    Priority order:
    1. Gemini (if configured) - best free option
    2. Groq (if configured) - very fast
    3. OpenRouter (if configured) - many free models
    4. Ollama (if running locally) - completely offline
    5. Rule-based fallback (no AI)
    """

    def __init__(self):
        self.providers: list[AIProvider] = []
        self._init_providers()

    def _init_providers(self):
        """Initialize available providers based on configuration."""
        # Google Gemini (recommended - generous free tier)
        if settings.gemini_api_key:
            self.providers.append(
                GeminiProvider(
                    api_key=settings.gemini_api_key,
                    model=settings.gemini_model,
                )
            )

        # Groq (very fast, good free tier)
        if settings.groq_api_key:
            self.providers.append(
                GroqProvider(
                    api_key=settings.groq_api_key,
                    model=settings.groq_model,
                )
            )

        # OpenRouter (many free models)
        if settings.openrouter_api_key:
            self.providers.append(
                OpenRouterProvider(
                    api_key=settings.openrouter_api_key,
                    model=settings.openrouter_model,
                )
            )

        # Ollama (local, always available if running)
        if settings.ollama_enabled:
            self.providers.append(
                OllamaProvider(
                    base_url=settings.ollama_base_url,
                    model=settings.ollama_model,
                )
            )

    def is_available(self) -> bool:
        """Check if any AI provider is available."""
        return len(self.providers) > 0

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        fallback_value: Optional[str] = None,
    ) -> Optional[str]:
        """
        Generate response using the first available provider.

        Falls back to next provider on error.
        Returns fallback_value if all providers fail.
        """
        for provider in self.providers:
            try:
                if provider.is_configured():
                    return await provider.generate(prompt, system_prompt)
            except Exception as e:
                print(f"Provider {provider.__class__.__name__} failed: {e}")
                continue

        return fallback_value

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        fallback_value: Optional[dict] = None,
    ) -> Optional[dict]:
        """Generate and parse JSON response."""
        # Add JSON instruction to system prompt
        json_system = (system_prompt or "") + "\n\nRespond ONLY with valid JSON, no other text."

        response = await self.generate(prompt, json_system)

        if not response:
            return fallback_value

        try:
            # Try to extract JSON from response
            # Sometimes models wrap JSON in markdown code blocks
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]

            return json.loads(response.strip())
        except json.JSONDecodeError:
            print(f"Failed to parse JSON: {response[:200]}")
            return fallback_value


# Global AI service instance
ai_service = AIService()
