from typing import Any


class BillingGateway:
    def __init__(self):
        self._usage: dict[str, dict[str, Any]] = {}

    def set_usage(self, user_id: str, plan: str, daily_count: int, daily_limit: int, has_own_key: bool = False):
        self._usage[user_id] = {
            "plan": plan,
            "daily_count": daily_count,
            "daily_limit": daily_limit,
            "has_own_key": has_own_key,
        }

    def can_assess(self, user_id: str) -> bool:
        usage = self._usage.get(user_id, {})
        if not usage:
            return False
        if usage.get("has_own_key"):
            return True
        plan = usage.get("plan", "free")
        if plan in ("monthly", "token_pack"):
            return True
        count = usage.get("daily_count", 0)
        limit = usage.get("daily_limit", 3)
        return count < limit

    def record(self, user_id: str, tokens: int = 0, model: str = ""):
        if user_id not in self._usage:
            self._usage[user_id] = {"plan": "free", "daily_count": 0, "daily_limit": 3, "has_own_key": False}
        self._usage[user_id]["daily_count"] = self._usage[user_id].get("daily_count", 0) + 1

    def get_daily_count(self, user_id: str) -> int:
        return self._usage.get(user_id, {}).get("daily_count", 0)
