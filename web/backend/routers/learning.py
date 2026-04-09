"""Learning endpoints: chat, answer, progress."""
from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import LearningProgress, ChatMessage, Answer, User
from auth import get_current_user
from services.llm import stream_chat

router = APIRouter(prefix="/api/learning", tags=["learning"])


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


@router.post("/chat")
async def chat(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """SSE streaming chat with AI tutor."""
    import logging
    from routers.cartridges import CARTRIDGES_DIR

    log = logging.getLogger("starlight.chat")

    # Validate input
    if not req.message or not req.message.strip():
        raise HTTPException(400, "Message cannot be empty")
    if not req.cartridge_id or not req.node_id:
        raise HTTPException(400, "cartridge_id and node_id are required")
    if len(req.message) > 10000:
        raise HTTPException(400, "Message too long (max 10000 characters)")

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
        raise HTTPException(404, f"Node '{req.node_id}' not found in cartridge '{req.cartridge_id}'")

    # Save user message
    user_msg = ChatMessage(
        user_id=user.id,
        cartridge_id=req.cartridge_id,
        node_id=req.node_id,
        role="user",
        content=req.message,
    )
    db.add(user_msg)

    # Update progress to in_progress
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

    # Build messages for LLM
    system_prompt = f"""你是 Starlight 学习系统的 AI 导师。
当前节点：{node_title}

教学内容：
{node_content[:6000]}

教学规则：
1. 友好但专业，不要废话
2. 用苏格拉底式提问引导思考
3. 讲完一个知识点后自动出一道题
4. 题目类型轮换: 单选→判断→多选→填空
5. 答错给提示，连续答错推荐基础
6. 用 Markdown 格式，公式用 $...$

题目输出格式（讲完知识点后，在消息末尾输出）:
<<QUESTION>>
{{"type":"single_choice","question":"...","options":["A","B","C","D"],"answer":1,"explanation":"..."}}
<</QUESTION>>

type 可选: single_choice, multi_choice, fill_blank, judgment
多选题: answers 为数组 [0,2]
判断题: answer 为 true/false
填空题: answer 为关键词字符串

推理步骤输出:
<<REASONING>>
{{"title":"推理过程","steps":[{{"title":"第1步","content":"..."}},{{"title":"第2步","content":"..."}}]}}
<</REASONING>>"""

    messages = [{"role": "system", "content": system_prompt}]
    for msg in req.history[-10:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role not in ("user", "assistant"):
            role = "user"
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
            yield f"data: {json.dumps({'error': True, 'text': '⚠️ AI 导师暂时无法回复，请稍后再试'})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
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
    from sqlalchemy import func, case

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

    # Streak: count distinct days with activity
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
