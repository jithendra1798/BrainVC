"""Thin LLM wrapper: structured outputs only, one retry on schema failure.
Modules never touch the OpenAI SDK directly — swapping providers or adding
caching happens here and nowhere else."""

from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel

from app.llm.config import MODELS

T = TypeVar("T", bound=BaseModel)

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


def parse_structured(role: str, system: str, user: str, schema: type[T]) -> T:
    """One structured-output call for a pipeline role. Retries once on failure."""
    model = MODELS[role]
    client = get_client()
    last_err: Exception | None = None
    for _ in range(2):
        try:
            completion = client.chat.completions.parse(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format=schema,
            )
            parsed = completion.choices[0].message.parsed
            if parsed is not None:
                return parsed
            last_err = RuntimeError("model returned no parsed output (refusal?)")
        except Exception as err:  # noqa: BLE001 — retry once, then surface
            last_err = err
    raise RuntimeError(f"structured call failed for role={role} model={model}: {last_err}")


def embed(texts: list[str]) -> list[list[float]]:
    response = get_client().embeddings.create(model=MODELS["embed"], input=texts)
    return [item.embedding for item in response.data]
