import abc
import json
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

class BaseLLMAdapter(abc.ABC):
    @abc.abstractmethod
    async def complete(self, prompt: str, system: Optional[str] = None) -> str:
        """Return free-form text completion."""
        pass

    @abc.abstractmethod
    async def complete_structured(self, prompt: str, schema: Type[T], system: Optional[str] = None) -> T:
        """Return structured response strictly conforming to Pydantic model T."""
        pass
