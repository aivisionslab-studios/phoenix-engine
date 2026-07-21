from abc import ABC, abstractmethod
from typing import Any

class IValidationService(ABC):
    @abstractmethod
    async def validate_system(self) -> dict[str, Any]:
        """Validates system integrity and sensor redundancy."""
        pass
