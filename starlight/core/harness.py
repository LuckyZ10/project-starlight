from starlight.adapters.base import HarnessResult


class LearningHarness:
    """Starlight 学习引擎 — 6 阶段生命周期"""

    def __init__(self, cartridge_loader, assessor, progress_mgr, tribute_engine):
        self.cartridges = cartridge_loader
        self.assessor = assessor
        self.progress = progress_mgr
        self.tribute = tribute_engine

    async def process(self, user_id: int, message: str, cartridge_id: str) -> HarnessResult:
        """核心方法：处理一条用户消息，返回学习结果。"""
        progress = await self.progress.get_progress(user_id, cartridge_id)

        if message == "/start":
            return await self._handle_start(user_id, cartridge_id)

        if progress is None or progress.status == "not_started":
            return HarnessResult(text="请先 /start 选择一个卡带", state="idle")

        if progress.status == "completed":
            return HarnessResult(text="你已经通关了！试试 /browse 选新的卡带。", state="completed")

        return await self._handle_assessment(user_id, message, cartridge_id, progress)

    async def _handle_start(self, user_id: int, cartridge_id: str) -> HarnessResult:
        cart = self.cartridges.load(cartridge_id)
        entry = self.cartridges.get_entry_node(cart)
        content = self.cartridges.load_node_content(cartridge_id, entry["file"])
        await self.progress.start_cartridge(user_id, cartridge_id, entry["id"])
        return HarnessResult(
            text=f"📚 {cart['title']}\n\n{content}\n\n准备好接受考核了吗？直接回答即可。",
            state="learning",
        )

    async def _handle_assessment(self, user_id: int, answer: str, cartridge_id: str, progress) -> HarnessResult:
        cart = self.cartridges.load(cartridge_id)
        current_node = self.cartridges.get_node_by_id(cart, progress.current_node)
        content = self.cartridges.load_node_content(cartridge_id, current_node["file"])

        result = await self.assessor.assess(
            node_content=content,
            pass_criteria=current_node["pass_criteria"],
            conversation=[],
            user_answer=answer,
        )

        if result.verdict == "PASS":
            next_nodes = self.cartridges.get_next_nodes(cart, current_node["id"])
            if not next_nodes:
                await self.progress.complete_cartridge(user_id, cartridge_id)
                tribute_text = self.tribute.build_completion_tribute(
                    cartridge_id, cart["title"], cart.get("contributors", [])
                )
                return HarnessResult(
                    text=f"✅ {result.feedback}\n\n{tribute_text}",
                    verdict="PASS",
                    state="completed",
                )
            else:
                await self.progress.advance_node(user_id, cartridge_id, next_nodes[0]["id"])
                next_content = self.cartridges.load_node_content(cartridge_id, next_nodes[0]["file"])
                return HarnessResult(
                    text=f"✅ {result.feedback}\n\n下一章：{next_nodes[0]['title']}\n\n{next_content}",
                    verdict="PASS",
                    state="learning",
                    next_node=next_nodes[0]["id"],
                )
        elif result.verdict == "FAIL":
            return HarnessResult(
                text=f"❌ {result.feedback}\n\n💡 提示：{result.hint}",
                verdict="FAIL",
                state="learning",
            )
        else:
            return HarnessResult(
                text=f"🤔 {result.feedback}",
                verdict="CONTINUE",
                state="learning",
            )
