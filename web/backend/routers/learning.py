"""Learning endpoints: chat, answer, progress — V2 adaptive harness."""
from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, func, case, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import LearningProgress, ChatMessage, Answer, User
from auth import get_current_user
from services.llm import stream_chat

router = APIRouter(prefix="/api/learning", tags=["learning"])
log = logging.getLogger("starlight.learning")


class ChatRequest(BaseModel):
    cartridge_id: str
    node_id: str
    message: str
    history: list[dict] = []


class AnswerRequest(BaseModel):
    cartridge_id: str
    node_id: str
    question_type: str
    user_answer: str
    correct_answer: str
    correct: bool


class CompleteRequest(BaseModel):
    cartridge_id: str
    node_id: str
    score: int = 100


# ─── Adaptive system prompt builder ───

async def _build_learner_context(db: AsyncSession, user: User, cartridge_id: str, node_id: str) -> str:
    """Build a compact learner context string for the system prompt."""
    # Recent answer accuracy (last 20 answers)
    recent_answers = (await db.execute(
        select(Answer)
        .where(Answer.user_id == user.id)
        .order_by(desc(Answer.id))
        .limit(20)
    )).scalars().all()

    if recent_answers:
        correct = sum(1 for a in recent_answers if a.correct)
        total = len(recent_answers)
        accuracy = correct / total
    else:
        accuracy = 0.5
        correct = 0
        total = 0

    # Current cartridge progress
    progress_rows = (await db.execute(
        select(LearningProgress)
        .where(LearningProgress.user_id == user.id, LearningProgress.cartridge_id == cartridge_id)
    )).scalars().all()

    completed_nodes = sum(1 for p in progress_rows if p.status == "completed")
    total_progress = len(progress_rows)

    # Determine learner level
    if accuracy >= 0.8:
        level = "advanced"
        difficulty_hint = "学习者水平较高，可以用更深入的场景和追问。"
    elif accuracy >= 0.5:
        level = "intermediate"
        difficulty_hint = "学习者水平中等，保持当前节奏，注意纠正误解。"
    else:
        level = "beginner"
        difficulty_hint = "学习者基础较弱，用简单场景、多提示、小步引导。"

    # Streak info
    streak_days = len(set(
        p.completed_at.date() for p in progress_rows
        if p.completed_at and p.status == "completed"
    )) if progress_rows else 0

    return (
        f"学习者水平：{level}（近期正确率 {correct}/{total}={accuracy:.0%}）\n"
        f"当前卡带进度：{completed_nodes}/{total_progress} 节已完成\n"
        f"连续学习：{streak_days} 天\n"
        f"难度调整：{difficulty_hint}"
    )


def _build_system_prompt(
    node_title: str,
    node_content: str,
    learner_context: str,
    conversation_turn: int,
) -> str:
    """Build an optimized, adaptive system prompt."""

    # Trim node content to ~4000 chars to save tokens
    if len(node_content) > 4000:
        # Keep first 3000 + last 1000 chars
        trimmed = node_content[:3000] + "\n\n[... 内容已省略 ...]\n\n" + node_content[-1000:]
    else:
        trimmed = node_content

    # Turn-based strategy hints
    if conversation_turn == 0:
        turn_hint = (
            "这是第一轮对话。用一个简短的日常场景引入第一个核心概念（2-3句），"
            "然后立刻出一道选择题。不要一次性讲太多。"
        )
    elif conversation_turn >= 5:
        turn_hint = (
            f"已经是第 {conversation_turn + 1} 轮了。如果学习者已经展现了基本理解，"
            "应该尽快做出总结性判定。[PASS] 或继续最后一轮引导。"
        )
    else:
        turn_hint = (
            f"第 {conversation_turn + 1} 轮。根据学习者回答调整引导方向。"
            "每次只讲一个小知识点，然后提问。"
        )

    return f"""你是 Starlight 的 AI 导师。你的任务是通过苏格拉底式对话帮助学生掌握知识。

## 核心规则（必须严格遵守）
1. **小步互动**：每次只讲一个小点（2-3句话），然后提问。绝对不要长篇大论。
2. **循序渐进**：先用简单场景引入，逐步加深，最后综合应用。
3. **即时反馈**：答对了给肯定并引入新概念；答错了温和纠正并给提示。
4. **覆盖要点**：确保教学内容覆盖下方「知识内容」中的核心要点。
5. **回复长度**：控制在 3-6 行以内（不含题目和代码）。

## 教学策略
- 第 1 轮：用一个贴近生活的场景引入第一个概念，出一道**单选题**
- 第 2 轮+：根据回答深入或纠正，出选择题或开放性问题
- 感觉学生理解了 70%+：出一道综合题（可以是多选），确认理解
- 学生理解到位 → 在回复末尾加上 `[PASS]` 标签
- 多轮后仍不理解核心 → 温和总结并加 `[FAIL]` 标签

## 出题格式（讲完知识点后在消息末尾输出）

单选题（默认）：
```
<<QUESTION>>
{{"type":"single_choice","question":"题目","options":["选项A","选项B","选项C","选项D"],"answer":0,"explanation":"解析"}}
<</QUESTION>>
```

多选题（多个正确答案）：
```
<<QUESTION>>
{{"type":"multi_choice","question":"题目","options":["选项A","选项B","选项C","选项D"],"answer":[0,2],"explanation":"解析"}}
<</QUESTION>>
```

判断题：
```
<<QUESTION>>
{{"type":"judgment","question":"题目","answer":true,"explanation":"解析"}}
<</QUESTION>>
```

填空题：
```
<<QUESTION>>
{{"type":"fill_blank","question":"___是什么？","answer":"关键词","explanation":"解析"}}
<</QUESTION>>
```

出题规则：
- 4 个选项（偶尔 2-3 个也可以）
- 选项简短（15 字以内）
- 有迷惑性但不是陷阱
- 大约 70% 选择题 + 30% 自由问答
- **第一轮必须出选择题**
- **如果没有使用 <<QUESTION>> 格式，系统无法显示答题按钮**

## 推理过程（可选，在题目之前输出）
```
<<REASONING>>
{{"title":"推理过程","steps":[{{"title":"步骤1","content":"..."}}]}}
<</REASONING>>
```

## 当前教学状态
{turn_hint}

## 学习者画像
{learner_context}

## 知识内容
{trimmed}"""


# ─── Endpoints ───

@router.post("/chat")
async def chat(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """SSE streaming chat with adaptive AI tutor."""
    from routers.cartridges import CARTRIDGES_DIR

    # Validate
    if not req.message or not req.message.strip():
        raise HTTPException(400, "Message cannot be empty")
    if not req.cartridge_id or not req.node_id:
        raise HTTPException(400, "cartridge_id and node_id are required")
    if len(req.message) > 10000:
        raise HTTPException(400, "Message too long")

    # Read node content
    nodes_dir = CARTRIDGES_DIR / req.cartridge_id / "nodes"
    if not nodes_dir.exists():
        raise HTTPException(404, f"Cartridge '{req.cartridge_id}' not found")

    node_content = ""
    node_title = req.node_id
    for f in nodes_dir.iterdir():
        if f.name.startswith(req.node_id) and f.suffix == ".md":
            node_content = f.read_text(encoding="utf-8")
            node_title = f.stem.split("-", 1)[-1] if "-" in f.stem else f.stem
            break

    if not node_content:
        raise HTTPException(404, f"Node '{req.node_id}' not found")

    # Save user message
    user_msg = ChatMessage(
        user_id=user.id,
        cartridge_id=req.cartridge_id,
        node_id=req.node_id,
        role="user",
        content=req.message,
    )
    db.add(user_msg)

    # Update progress
    stmt = select(LearningProgress).where(
        LearningProgress.user_id == user.id,
        LearningProgress.cartridge_id == req.cartridge_id,
        LearningProgress.node_id == req.node_id,
    )
    result = await db.execute(stmt)
    progress = result.scalar_one_or_none()
    if not progress:
        from datetime import datetime, timezone
        progress = LearningProgress(
            user_id=user.id,
            cartridge_id=req.cartridge_id,
            node_id=req.node_id,
            status="in_progress",
            started_at=datetime.now(timezone.utc),
        )
        db.add(progress)
    elif progress.status == "not_started":
        from datetime import datetime, timezone
        progress.status = "in_progress"
        progress.started_at = datetime.now(timezone.utc)
    await db.commit()

    # Build adaptive context
    learner_context = await _build_learner_context(db, user, req.cartridge_id, req.node_id)
    conversation_turn = len(req.history) // 2  # Rough estimate of turns

    system_prompt = _build_system_prompt(
        node_title=node_title,
        node_content=node_content,
        learner_context=learner_context,
        conversation_turn=conversation_turn,
    )

    # Build messages with smart context window
    messages = [{"role": "system", "content": system_prompt}]

    # Add conversation history (last 16 messages max)
    history = req.history[-16:]
    for msg in history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role not in ("user", "assistant"):
            role = "user"
        # Trim very long messages to save tokens
        if len(content) > 1000:
            content = content[:800] + "...[已省略]"
        messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": req.message})

    async def event_stream():
        full_response = ""
        try:
            async for chunk in stream_chat(messages):
                full_response += chunk
                yield f"data: {json.dumps({'text': chunk})}\n\n"
        except Exception as e:
            log.error("LLM streaming error: %s", e)
            yield f"data: {json.dumps({'error': True, 'text': 'AI 导师暂时无法回复，请稍后再试'})}\n\n"

        # Save assistant response
        if full_response:
            assistant_msg = ChatMessage(
                user_id=user.id,
                cartridge_id=req.cartridge_id,
                node_id=req.node_id,
                role="assistant",
                content=full_response[:8000],
            )
            db.add(assistant_msg)
            try:
                await db.commit()
            except Exception:
                await db.rollback()

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/answer")
async def submit_answer(
    req: AnswerRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Record an answer and return feedback."""
    answer = Answer(
        user_id=user.id,
        cartridge_id=req.cartridge_id,
        node_id=req.node_id,
        question_type=req.question_type,
        correct=req.correct,
    )
    db.add(answer)
    await db.commit()

    return {
        "correct": req.correct,
        "feedback": "✅ 正确！" if req.correct else "❌ 不太对，再想想？",
    }


@router.get("/progress/{cartridge_id}")
async def get_progress(
    cartridge_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get learning progress for all nodes in a cartridge."""
    stmt = select(LearningProgress).where(
        LearningProgress.user_id == user.id,
        LearningProgress.cartridge_id == cartridge_id,
    )
    result = await db.execute(stmt)
    progresses = result.scalars().all()

    return {
        p.node_id: {
            "status": p.status,
            "score": p.score,
            "started_at": p.started_at.isoformat() if p.started_at else None,
            "completed_at": p.completed_at.isoformat() if p.completed_at else None,
        }
        for p in progresses
    }


@router.post("/complete")
async def complete_node(
    req: CompleteRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Mark a node as completed."""
    from datetime import datetime, timezone

    stmt = select(LearningProgress).where(
        LearningProgress.user_id == user.id,
        LearningProgress.cartridge_id == req.cartridge_id,
        LearningProgress.node_id == req.node_id,
    )
    result = await db.execute(stmt)
    progress = result.scalar_one_or_none()

    if not progress:
        progress = LearningProgress(
            user_id=user.id,
            cartridge_id=req.cartridge_id,
            node_id=req.node_id,
            started_at=datetime.now(timezone.utc),
        )
        db.add(progress)

    progress.status = "completed"
    progress.score = req.score
    progress.completed_at = datetime.now(timezone.utc)
    await db.commit()

    return {"status": "completed", "score": req.score}


@router.get("/stats")
async def get_learning_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get overall learning statistics for the current user."""
    # Total nodes attempted / completed
    progress_stmt = select(
        func.count(LearningProgress.id).label("total_nodes"),
        func.sum(case((LearningProgress.status == "completed", 1), else_=0)).label("completed_nodes"),
        func.sum(case((LearningProgress.status == "in_progress", 1), else_=0)).label("in_progress_nodes"),
        func.avg(case((LearningProgress.status == "completed", LearningProgress.score), else_=None)).label("avg_score"),
    ).where(LearningProgress.user_id == user.id)
    result = await db.execute(progress_stmt)
    row = result.one()

    # Answer stats
    answer_stmt = select(
        func.count(Answer.id).label("total_answers"),
        func.sum(case((Answer.correct == True, 1), else_=0)).label("correct_answers"),
    ).where(Answer.user_id == user.id)
    answer_result = await db.execute(answer_stmt)
    answer_row = answer_result.one()

    # Per-cartridge progress
    cart_stmt = select(
        LearningProgress.cartridge_id,
        func.count(LearningProgress.id).label("total"),
        func.sum(case((LearningProgress.status == "completed", 1), else_=0)).label("completed"),
    ).where(LearningProgress.user_id == user.id).group_by(LearningProgress.cartridge_id)
    cart_result = await db.execute(cart_stmt)
    cartridges = [
        {"cartridge_id": r.cartridge_id, "total": r.total, "completed": r.completed}
        for r in cart_result.all()
    ]

    # Chat messages count
    msg_stmt = select(func.count(ChatMessage.id)).where(ChatMessage.user_id == user.id)
    msg_result = await db.execute(msg_stmt)
    total_messages = msg_result.scalar() or 0

    # Active days
    streak_stmt = select(func.count(func.distinct(func.date(ChatMessage.created_at)))).where(
        ChatMessage.user_id == user.id
    )
    streak_result = await db.execute(streak_stmt)
    active_days = streak_result.scalar() or 0

    return {
        "total_nodes": row.total_nodes or 0,
        "completed_nodes": row.completed_nodes or 0,
        "in_progress_nodes": row.in_progress_nodes or 0,
        "avg_score": round(row.avg_score, 1) if row.avg_score else 0,
        "total_answers": answer_row.total_answers or 0,
        "correct_answers": answer_row.correct_answers or 0,
        "accuracy": round((answer_row.correct_answers or 0) / max(answer_row.total_answers or 1, 1) * 100, 1),
        "total_messages": total_messages,
        "active_days": active_days,
        "cartridges": cartridges,
    }
