# starlight/core/harness_v2.py
"""V2 Harness — 完整教学循环，融合启智教学策略"""
from __future__ import annotations
from starlight.adapters.base import HarnessResult
from starlight.core.session import Session
from starlight.core.learner import LearnerProfile
from starlight.core.strategies import get_strategy, TeachingStrategy
from starlight.core.assessor_v2 import AssessorV2
from starlight.core.contributor import TributeEngine
from starlight.core.cartridge import CartridgeLoader
from starlight.core.spaced_rep import ReviewCard, calculate_next_review, get_due_cards


class LearningHarnessV2:
    """Starlight V2 学习引擎 — 融合启智 24 个教学 skill"""
    
    def __init__(self, cartridge_loader: CartridgeLoader,
                 assessor: AssessorV2, progress_mgr, tribute_engine: TributeEngine,
                 strategy_name: str = "adaptive"):
        self.cartridges = cartridge_loader
        self.assessor = assessor
        self.progress = progress_mgr
        self.tribute = tribute_engine
        self.strategy_name = strategy_name
        
        # 会话和画像存储（生产环境用 DB，现在用内存）
        self._sessions: dict[tuple[int, str], Session] = {}
        self._learners: dict[int, LearnerProfile] = {}
        self._review_cards: dict[int, list[ReviewCard]] = {}
    
    def get_session(self, user_id: int, cartridge_id: str) -> Session | None:
        return self._sessions.get((user_id, cartridge_id))
    
    def get_learner(self, user_id: int) -> LearnerProfile:
        if user_id not in self._learners:
            self._learners[user_id] = LearnerProfile(user_id=user_id)
        return self._learners[user_id]
    
    def _get_strategy(self) -> TeachingStrategy:
        return get_strategy(self.strategy_name)
    
    async def process(self, user_id: int, message: str, 
                      cartridge_id: str | None = None) -> HarnessResult:
        """核心方法：处理用户消息"""
        learner = self.get_learner(user_id)
        strategy = self._get_strategy()
        self.assessor.strategy = strategy
        
        # === 命令路由 ===
        if message == "/browse":
            return await self._handle_browse()
        if message == "/help":
            return self._handle_help()
        if message == "/progress":
            return await self._handle_progress(user_id, cartridge_id)
        if message == "/review":
            return await self._handle_review_cards(user_id)
        if message == "/stats":
            return self._handle_stats(learner)
        if message == "/start":
            return await self._handle_start(user_id, cartridge_id, learner, strategy)
        
        # === 学习流程 ===
        if not cartridge_id:
            return HarnessResult(text="请先 /start 选择一个卡带", state="idle")
        
        session = self.get_session(user_id, cartridge_id)
        if session is None:
            return HarnessResult(text="请先 /start 选择一个卡带", state="idle")
        
        # /back — 拉回正轨，聚焦核心知识点
        if message == "/back":
            return await self._handle_back(user_id, cartridge_id, session, learner)
        
        # 记录用户回答
        session.add_exchange("user", message)
        
        # 加载当前节点
        cart = self.cartridges.load(cartridge_id)
        node = self.cartridges.get_node_by_id(cart, session.current_node)
        content = self.cartridges.load_node_content(cartridge_id, node["file"])
        
        # 调用 Assessor
        result = await self.assessor.assess(content, node["pass_criteria"], session, learner)
        
        # 记录 AI 回复
        session.add_exchange("assistant", result.feedback, 
                           metadata={"verdict": result.verdict, "score": result.score})
        
        # 更新学习者画像
        learner.update_from_assessment(
            score=result.score, verdict=result.verdict,
            turn_count=session.turn_count, error_type=result.error_type
        )
        
        # 处理结果
        if result.verdict == "PASS":
            return await self._handle_pass(user_id, cartridge_id, cart, node, result, session, learner)
        elif result.verdict == "FAIL":
            return self._handle_fail(result, learner)
        else:
            # CONTINUE — 继续对话
            return HarnessResult(text=f"🤔 {result.feedback}", verdict="CONTINUE", state="learning")
    
    async def _handle_start(self, user_id, cartridge_id, learner, strategy) -> HarnessResult:
        if not cartridge_id:
            return HarnessResult(text="请用 /start <卡带ID> 选择卡带。用 /browse 查看可用卡带。", state="idle")
        
        cart = self.cartridges.load(cartridge_id)
        entry = self.cartridges.get_entry_node(cart)
        content = self.cartridges.load_node_content(cartridge_id, entry["file"])
        
        # 创建会话
        session = Session(user_id=user_id, cartridge_id=cartridge_id, current_node=entry["id"])
        session.max_turns = learner.get_max_turns()
        self._sessions[(user_id, cartridge_id)] = session
        
        # 更新进度
        await self.progress.start_cartridge(user_id, cartridge_id, entry["id"])
        
        # 记录内容到会话（不发给用户，给 LLM 参考）
        session.add_exchange("system", f"知识内容：{content}")
        
        # 让 LLM 生成第一个小问题（不甩教材）
        first_question = await self._generate_first_question(content, entry["pass_criteria"], learner, session)
        session.add_exchange("assistant", first_question)
        
        opening = strategy.get_opening_message(entry["title"], content, learner)
        
        return HarnessResult(
            text=f"{opening}\n\n{first_question}",
            state="learning",
        )
    
    async def _generate_first_question(self, content, pass_criteria, learner, session) -> str:
        """让 LLM 生成第一个引导性小问题（不甩教材）"""
        strategy = self._get_strategy()
        system_prompt = await strategy.build_system_prompt(content, pass_criteria, learner, session)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "我准备好了，开始吧！"},
        ]
        
        try:
            response = await self.assessor._call_llm(messages)
            return response
        except Exception:
            return "我们来聊一个概念：在编程里，`=` 是什么意思？跟数学里的等号一样吗？"
    
    async def _handle_pass(self, user_id, cartridge_id, cart, node, result, session, learner) -> HarnessResult:
        next_nodes = self.cartridges.get_next_nodes(cart, node["id"])
        
        # 记录分数
        session.record_score(node["id"], result.score)
        
        # 创建复习卡片
        self._add_review_card(user_id, node["id"], cartridge_id, node.get("title", ""), result.quality)
        
        if not next_nodes:
            # 通关！
            await self.progress.complete_cartridge(user_id, cartridge_id)
            tribute_text = self.tribute.build_completion_tribute(
                cartridge_id, cart["title"], cart.get("contributors", [])
            )
            return HarnessResult(
                text=f"✅ {result.feedback}\n\n🎉 恭喜通关！\n\n{tribute_text}\n\n⚡ XP +{learner.total_xp}",
                verdict="PASS", state="completed",
            )
        else:
            # 进入下一节点
            next_node = next_nodes[0]
            await self.progress.advance_node(user_id, cartridge_id, next_node["id"])
            session.advance_node(next_node["id"])
            
            # 加载下一节点内容
            next_content = self.cartridges.load_node_content(cartridge_id, next_node["file"])
            
            # 生成下一节开场
            strategy = self._get_strategy()
            opening = strategy.get_opening_message(next_node["title"], next_content, learner)
            session.add_exchange("system", f"知识内容：{next_content}")
            
            first_q = await self._generate_first_question(next_content, next_node["pass_criteria"], learner, session)
            session.add_exchange("assistant", first_q)
            
            return HarnessResult(
                text=f"✅ {result.feedback}\n\n---\n\n{opening}\n\n{first_q}",
                verdict="PASS", state="learning", next_node=next_node["id"],
            )
    
    def _handle_fail(self, result, learner) -> HarnessResult:
        hint_text = f"\n\n💡 提示：{result.hint}" if result.hint else ""
        encouragement = ""
        if learner.confidence < 0.3:
            encouragement = "\n\n💪 别担心，学习中犯错是正常的，我们一起加油！"
        
        return HarnessResult(
            text=f"❌ {result.feedback}{hint_text}{encouragement}",
            verdict="FAIL", state="learning",
        )
    
    def _add_review_card(self, user_id, node_id, cartridge_id, title, quality):
        if user_id not in self._review_cards:
            self._review_cards[user_id] = []
        card = ReviewCard(node_id=node_id, cartridge_id=cartridge_id, title=title)
        calculate_next_review(card, quality)
        self._review_cards[user_id].append(card)
    
    async def _handle_review_cards(self, user_id) -> HarnessResult:
        cards = self._review_cards.get(user_id, [])
        due = get_due_cards(cards)
        if not due:
            return HarnessResult(text="📭 暂无需要复习的内容，继续保持学习！", state="idle")
        lines = ["📋 需要复习的内容：\n"]
        for c in due:
            lines.append(f"• {c.title} ({c.cartridge_id}/{c.node_id})")
        return HarnessResult(text="\n".join(lines), state="idle")
    
    def _handle_stats(self, learner) -> HarnessResult:
        warning = learner.get_warning()
        warning_text = f"\n\n{warning}" if warning else ""
        return HarnessResult(
            text=(
                f"📊 学习统计\n\n"
                f"⚡ XP: {learner.total_xp}\n"
                f"📚 已完成节点: {learner.nodes_completed}\n"
                f"📈 知识水平: {learner.knowledge_level:.0%}\n"
                f"🎯 自信度: {learner.confidence:.0%}\n"
                f"🧠 布鲁姆层次: L{learner.bloom_level}\n"
                f"🔥 连续学习: {learner.streak_days} 天"
                f"{warning_text}"
            ),
            state="idle",
        )
    
    async def _handle_back(self, user_id, cartridge_id, session, learner) -> HarnessResult:
        """拉回正轨 — 重新聚焦到当前节点的核心知识点"""
        if session is None:
            return HarnessResult(text="请先 /start 选择一个卡带", state="idle")
        
        cart = self.cartridges.load(cartridge_id)
        node = self.cartridges.get_node_by_id(cart, session.current_node)
        content = self.cartridges.load_node_content(cartridge_id, node["file"])
        
        # 让 LLM 重新聚焦
        session.add_exchange("user", "/back（请回到当前知识点）")
        
        messages = [
            {"role": "system", "content": f"你是一个教学助手。用户觉得跑偏了，请回到核心知识点。"},
            {"role": "system", "content": f"当前知识点：{node['title']}"},
            {"role": "system", "content": f"知识内容：{content}"},
            {"role": "system", "content": f"通过标准：{node['pass_criteria']}"},
            {"role": "system", "content": "请用2-3句话总结当前知识点的核心，然后问一个紧扣通过标准的问题。"},
        ]
        
        try:
            response = await self.assessor._call_llm(messages)
            session.add_exchange("assistant", response)
            return HarnessResult(
                text=f"🎯 回到正轨！\n\n{response}",
                state="learning",
            )
        except Exception:
            return HarnessResult(
                text=f"🎯 当前知识点：**{node['title']}**\n\n通过标准：{node['pass_criteria']}\n\n准备好了就回答吧！",
                state="learning",
            )
    
    async def _handle_progress(self, user_id: int, cartridge_id: str | None) -> HarnessResult:
        """显示学习进度地图 — 已完成、当前、待学习"""
        if not cartridge_id:
            return HarnessResult(text="请先选择一个卡带。用 /browse 查看可用卡带。", state="idle")
        
        cart = self.cartridges.load(cartridge_id)
        progress = await self.progress.get_progress(user_id, cartridge_id)
        
        if progress is None:
            return HarnessResult(text="你还没开始这个卡带。用 /start 开始吧！", state="idle")
        
        # Build progress map
        completed_nodes = set()
        current_node_id = progress.current_node
        
        # Walk the DAG to find completed nodes (before current)
        dag = cart.get("dag", {})
        edges = dag.get("edges", {})
        entry = dag.get("entry", "")
        
        # Simple BFS to find nodes before current
        visited = set()
        queue = [entry]
        while queue:
            nid = queue.pop(0)
            if nid == current_node_id:
                break
            if nid not in visited:
                visited.add(nid)
                completed_nodes.add(nid)
                queue.extend(edges.get(nid, []))
        
        # Render map
        lines = [f"🗺️ **{cart['title']}** 学习进度\n"]
        for node in cart["nodes"]:
            nid = node["id"]
            if nid in completed_nodes:
                lines.append(f"  ✅ {node['title']}")
            elif nid == current_node_id:
                lines.append(f"  📍 {node['title']} ← 你在这里")
                lines.append(f"     📋 通过标准：{node['pass_criteria']}")
            else:
                lines.append(f"  ⬜ {node['title']}")
        
        total = len(cart["nodes"])
        done = len(completed_nodes)
        pct = int(done / total * 100) if total > 0 else 0
        lines.append(f"\n📊 进度：{done}/{total}（{pct}%）")
        
        status_text = "学习中" if progress.status == "in_progress" else progress.status
        lines.append(f"📌 状态：{status_text}")
        
        return HarnessResult(text="\n".join(lines), state=progress.status)
    
    # 复用 V1 的 browse/help
    async def _handle_browse(self) -> HarnessResult:
        cartridges = self.cartridges.list_cartridges()
        lines = ["📚 可用卡带：\n"]
        for cart_id in cartridges:
            try:
                cart = self.cartridges.load(cart_id)

                lines.append(f"• {cart['title']} ({cart_id}) — {len(cart['nodes'])} 个知识点")
            except Exception:
                lines.append(f"• {cart_id}")
        lines.append("\n用 /start <卡带ID> 开始学习")
        return HarnessResult(text="\n".join(lines), state="idle")
    
    def _handle_help(self) -> HarnessResult:
        return HarnessResult(
            text=(
                "🌟 **星光学习机 V2**\n\n"
                "指令：\n"
                "/browse — 浏览卡带\n"
                "/start <ID> — 开始学习\n"
                "/progress — 学习进度地图\n"
                "/back — 拉回正轨（跑偏时用）\n"
                "/stats — 学习统计\n"
                "/review — 复习到期内容\n"
                "/help — 帮助\n\n"
                "💡 直接输入文字 = 回答问题\n"
                "🎯 LLM 会自由出题，但必须覆盖通过标准才算 PASS"
            ),
            state="idle",
        )
