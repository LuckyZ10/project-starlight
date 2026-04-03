from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from starlight.models import UserProgress


class ProgressManager:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_progress(self, user_id: int, cartridge_id: str) -> UserProgress | None:
        """获取用户在某个卡带中的进度。"""
        stmt = select(UserProgress).where(
            UserProgress.user_id == user_id,
            UserProgress.cartridge_id == cartridge_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def start_cartridge(self, user_id: int, cartridge_id: str, entry_node: str = "N01") -> UserProgress:
        """开始学习一个卡带。"""
        progress = UserProgress(
            user_id=user_id,
            cartridge_id=cartridge_id,
            current_node=entry_node,
            status="in_progress",
        )
        self.session.add(progress)
        await self.session.commit()
        return progress

    async def advance_node(self, user_id: int, cartridge_id: str, next_node: str) -> UserProgress:
        """通过当前节点，前进到下一个节点。"""
        progress = await self.get_progress(user_id, cartridge_id)
        if progress is None:
            raise ValueError(f"No progress found for user {user_id} in {cartridge_id}")
        progress.current_node = next_node
        await self.session.commit()
        return progress

    async def complete_cartridge(self, user_id: int, cartridge_id: str) -> UserProgress:
        """完成整个卡带。"""
        progress = await self.get_progress(user_id, cartridge_id)
        if progress is None:
            raise ValueError(f"No progress found for user {user_id} in {cartridge_id}")
        progress.status = "completed"
        progress.completed_at = datetime.utcnow()
        await self.session.commit()
        return progress
