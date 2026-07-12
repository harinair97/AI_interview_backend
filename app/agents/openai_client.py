from typing import Protocol, TypeVar

from openai import OpenAI
from pydantic import BaseModel

from app.config import Settings, get_settings

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class StructuredOutputClient(Protocol):
    def parse(
        self,
        *,
        model: str,
        instructions: str,
        input_text: str,
        response_model: type[SchemaT],
    ) -> SchemaT: ...


class OpenAIStructuredOutputClient:
    """Thin adapter around Responses API structured Pydantic parsing."""

    def __init__(self, settings: Settings) -> None:
        self.client = OpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.openai_timeout_seconds,
            max_retries=settings.openai_max_retries,
        )

    def parse(
        self,
        *,
        model: str,
        instructions: str,
        input_text: str,
        response_model: type[SchemaT],
    ) -> SchemaT:
        response = self.client.responses.parse(
            model=model,
            instructions=instructions,
            input=input_text,
            text_format=response_model,
        )
        if response.output_parsed is None:
            raise ValueError("OpenAI returned no parsed structured output.")
        return response.output_parsed


def create_openai_client(
    settings: Settings | None = None,
) -> StructuredOutputClient | None:
    resolved_settings = settings or get_settings()
    if not resolved_settings.openai_api_key:
        return None
    return OpenAIStructuredOutputClient(resolved_settings)
