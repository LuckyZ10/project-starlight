from starlight.adapters.base import HarnessResult


class LearningHarness:
    """Starlight 学习引擎 — 6 阶段生命周期"""

    def __init__(self, cartridge_loader, assessor, progress_mgr, tribute_engine):
        self.cartridges = cartridge_loader
        self.assessor = assessor
        self.progress = progress_mgr
        self.tribute = tribute_engine

    async def process(self, user_id: int, message: str, cartridge_id: str | None = None) -> HarnessResult:
        """核心方法：处理一条用户消息，返回学习结果。"""
        # ── Command routing ──
        if message == "/browse":
            return await self._handle_browse()
        if message == "/help":
            return self._handle_help()
        if message == "/progress":
            return await self._handle_progress(user_id, cartridge_id)
        if message == "/start":
            return await self._handle_start(user_id, cartridge_id)
        if message == "/review":
            return await self._handle_review(user_id, cartridge_id)

        # ── Assessment flow ──
        if not cartridge_id:
            return HarnessResult(text="请先 /start 选择一个卡带", state="idle")

        progress = await self.progress.get_progress(user_id, cartridge_id)

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

    # ── Command handlers ──

    async def _handle_browse(self) -> HarnessResult:
        cartridges = self.cartridges.list_cartridges()
        lines = ["📚 可用卡带：\n"]
        for cart_id in cartridges:
            try:
                cart = self.cartridges.load(cart_id)
                lines.append(f"• **{cart['title']}** (`{cart_id}`) — {len(cart['nodes'])} 个知识点")
            except Exception:
                lines.append(f"• `{cart_id}`")
        lines.append("\n用 `/start <卡带ID>` 开始学习")
        return HarnessResult(text="\n".join(lines), state="idle")

    async def _handle_progress(self, user_id: int, cartridge_id: str | None) -> HarnessResult:
        if not cartridge_id:
            return HarnessResult(text="请先选择一个卡带。用 /browse 查看可用卡带。", state="idle")
        progress = await self.progress.get_progress(user_id, cartridge_id)
        if progress is None:
            return HarnessResult(text="你尚未开始这个卡带。用 /start 开始吧！", state="idle")
        cart = self.cartridges.load(cartridge_id)
        total = len(cart["nodes"])
        return HarnessResult(
            text=f"📊 **{cart['title']}** 进度\n\n当前：{progress.current_node}\n状态：{progress.status}\n总节点：{total}",
            state=progress.status,
        )

    def _handle_help(self) -> HarnessResult:
        return HarnessResult(
            text=(
                "🌟 **星光学习机**\n\n"
                "指令列表：\n"
                "/browse — 浏览可用卡带\n"
                "/start <ID> — 开始学习\n"
                "/progress — 查看进度\n"
                "/review — 复习已学知识\n"
                "/help — 显示帮助\n\n"
                "直接输入文字 = 回答考核问题"
            ),
            state="idle",
        )

    async def _handle_review(self, user_id: int, cartridge_id: str | None) -> HarnessResult:
        if not cartridge_id:
            return HarnessResult(text="请先选择一个卡带。", state="idle")
        progress = await self.progress.get_progress(user_id, cartridge_id)
        if progress is None:
            return HarnessResult(text="你还没开始学习哦。用 /start 开始！", state="idle")
        cart = self.cartridges.load(cartridge_id)
        if progress.current_node:
            node = self.cartridges.get_node_by_id(cart, progress.current_node)
            content = self.cartridges.load_node_content(cartridge_id, node["file"])
            return HarnessResult(text=f"📖 复习：{node['title']}\n\n{content}", state="learning")
        return HarnessResult(text="暂无可复习内容。", state="idle")
