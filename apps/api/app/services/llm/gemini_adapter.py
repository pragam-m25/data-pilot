import json
from typing import Optional, Type, TypeVar
import httpx
from pydantic import BaseModel
from app.services.llm.base import BaseLLMAdapter

T = TypeVar("T", bound=BaseModel)

class GeminiAdapter(BaseLLMAdapter):
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model = model
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    async def complete(self, prompt: str, system: Optional[str] = None) -> str:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")

        contents = []
        if system:
            contents.append({"role": "user", "parts": [{"text": f"System Instructions: {system}\n\nUser: {prompt}"}]})
        else:
            contents.append({"role": "user", "parts": [{"text": prompt}]})

        url = f"{self.base_url}?key={self.api_key}"
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json={"contents": contents})
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise RuntimeError("No response candidate returned from Gemini")
            return candidates[0]["content"]["parts"][0]["text"]

    async def complete_structured(self, prompt: str, schema: Type[T], system: Optional[str] = None) -> T:
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        system_instruction = (
            (system or "") +
            f"\n\nYou must return strictly valid JSON matching this JSON schema:\n{schema_json}\n"
            "Do not include markdown codeblocks or extra text. Return only raw JSON."
        )

        contents = [{"role": "user", "parts": [{"text": f"{system_instruction}\n\nTask: {prompt}"}]}]
        url = f"{self.base_url}?key={self.api_key}"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json={
                "contents": contents,
                "generationConfig": {
                    "responseMimeType": "application/json"
                }
            })
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            # Parse JSON and validate against schema
            parsed = json.loads(raw_text)
            return schema.model_validate(parsed)
