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
        
        # 用策略生成开场白（不直接甩教材）
        opening = strategy.get_opening_message(entry["title"], content, learner)
        
        # 记录开场白
        session.add_exchange("system", f"知识内容：{content}")
        
        # 触发第一个问题：让 LLM 基于内容生成一个引导性问题
        first_question = await self._generate_first_question(content, entry["pass_criteria"], learner, session)
        session.add_exchange("assistant", first_question)
        
        return HarnessResult(
            text=f"{opening}\n\n{first_question}",
            state="learning",
        )
    
    async def _generate_first_question(self, content, pass_criteria, learner, session) -> str:
        """让 LLM 生成第一个引导性问题"""
        strategy = self._get_strategy()
        system_prompt = await strategy.build_system_prompt(content, pass_criteria, learner, session)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "我准备好了，请出一个场景题来考考我。"}
        ]
        
        try:
            response = await self.assessor._call_llm(messages)
            return response
        except Exception:
            return f"来看这个场景：\n\n{content}\n\n你能用自己的话解释一下这里的核心概念吗？"
    
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
                "🌟 星光学习机 V2\n\n"
                "指令：\n"
                "/browse — 浏览卡带\n"
                "/start <ID> — 开始学习\n"
                "/stats — 学习统计\n"
                "/review — 复习到期内容\n"
                "/help — 帮助\n\n"
                "💡 直接输入文字 = 回答考核问题\n"
                "系统会根据你的水平自动调整教学策略"
            ),
            state="idle",
        )
