import json
from typing import Optional, Type, TypeVar
import httpx
from pydantic import BaseModel
from app.services.llm.base import BaseLLMAdapter

T = TypeVar("T", bound=BaseModel)

class AnthropicAdapter(BaseLLMAdapter):
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.anthropic.com/v1/messages"

    async def complete(self, prompt: str, system: Optional[str] = None) -> str:
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is not configured.")

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}]
        }
        if system:
            payload["system"] = system

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(self.base_url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["content"][0]["text"]

    async def complete_structured(self, prompt: str, schema: Type[T], system: Optional[str] = None) -> T:
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        system_instruction = (
            (system or "") +
            f"\n\nYou MUST return raw, strictly valid JSON conforming to the schema below without any markdown fences, comments, or preamble.\nSCHEMA:\n{schema_json}"
        )
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "system": system_instruction,
            "messages": [{"role": "user", "content": prompt}]
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(self.base_url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["content"][0]["text"].strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            parsed = json.loads(raw_text.strip())
            return schema.model_validate(parsed)
