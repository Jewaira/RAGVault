# routes/chat.py
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from rag import query_rag
from db.chat import create_session, store_chat_history, get_chat_history

router = APIRouter()


class ChatRequest(BaseModel):
    question: str
    session_id: str           # ← required, copy from /upload_pdf response
    new_session: bool = False  # ← True = start fresh session


@router.post("/chat")
async def api_chat(request: Request, body: ChatRequest):
    pool = request.app.state.pool

    # 1. check PDF uploaded
    if request.app.state.qa_chain is None:
        raise HTTPException(
            status_code=400,
            detail="No PDF uploaded yet. Please upload via POST /upload_pdf first."
        )

    # 2. handle session
    if body.new_session:
        session_id = await create_session(pool, history_name=body.question[:50])
        print(f"New session created: {session_id}")
    else:
        session_id = body.session_id
        print(f" Using session: {session_id}")

    # 3. get answer from RAG
    answer = await query_rag(body.question, request.app.state.qa_chain)

    # 4. store in PostgreSQL
    message_id = await store_chat_history(
        pool,
        session_id=session_id,
        question=body.question,
        answer=answer,
    )

    return {
        "session_id": session_id,
        "message_id": message_id,
        "question": body.question,
        "answer": answer,
    }


@router.get("/get_session")
async def api_get_session(request: Request, session_id: str = Query(...)):
    """Retrieve full chat history for a session."""
    history = await get_chat_history(request.app.state.pool, session_id)
    if not history:
        raise HTTPException(status_code=404, detail="No session found")
    return {"session_id": session_id, "history": history}