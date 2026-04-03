from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class HarnessResult:
    text: str
    verdict: str | None = None  # PASS/FAIL/CONTINUE
    state: str | None = None  # idle/learning/assessing/completed
    next_node: str | None = None


class BaseAdapter(ABC):
    @abstractmethod
    async def send_message(self, user_id: str, text: str) -> None:
        """Send a message to the user."""
        pass
