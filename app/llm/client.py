from typing import Protocol

from fastapi import Depends

from app.core.config import Settings, get_settings


class LLMError(Exception):
    pass


class LLMClient(Protocol):
    def generate(self, prompt: str) -> str:
        raise NotImplementedError


class GeminiLLMClient:
    def __init__(self, api_key: str | None, model_name: str) -> None:
        self.api_key = api_key
        self.model_name = model_name

    def generate(self, prompt: str) -> str:
        if not self.api_key:
            raise LLMError("GEMINI_API_KEY não configurada.")

        try:
            from google import genai

            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
            text = getattr(response, "text", None)
        except Exception as exc:  # pragma: no cover - depends on external API
            raise LLMError("Falha ao gerar resumo na Gemini.") from exc

        if not text or not text.strip():
            raise LLMError("A Gemini retornou uma resposta vazia.")
        return text.strip()


def get_llm_client(settings: Settings = Depends(get_settings)) -> LLMClient:
    return GeminiLLMClient(settings.gemini_api_key, settings.gemini_model)
