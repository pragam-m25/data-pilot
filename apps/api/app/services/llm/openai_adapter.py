import json
from typing import Optional, Type, TypeVar
import httpx
from pydantic import BaseModel
from app.services.llm.base import BaseLLMAdapter

T = TypeVar("T", bound=BaseModel)

class OpenAIAdapter(BaseLLMAdapter):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    async def complete(self, prompt: str, system: Optional[str] = None) -> str:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not configured.")

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json={"model": self.model, "messages": messages}
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def complete_structured(self, prompt: str, schema: Type[T], system: Optional[str] = None) -> T:
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        system_instruction = (
            (system or "") +
            f"\n\nYou are a precise JSON generator. Return strictly valid JSON conforming to this schema:\n{schema_json}"
        )
        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ]

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json={
                    "model": self.model,
                    "messages": messages,
                    "response_format": {"type": "json_object"}
                }
            )
            resp.raise_for_status()
            data = resp.json()
            raw_content = data["choices"][0]["message"]["content"]
            parsed = json.loads(raw_content)
            return schema.model_validate(parsed)
