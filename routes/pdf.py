# routes/pdf.py
import asyncio
import os
from fastapi import APIRouter, HTTPException, UploadFile, File, Request

from rag import init_rag
from db.chat import create_session

router = APIRouter()

UPLOAD_DIR = "uploaded_pdfs"


@router.post("/upload_pdf")
async def upload_pdf(request: Request, file: UploadFile = File(...)):
    """
    Upload a PDF file, initialize RAG pipeline
    and automatically start a new session.
    """

    # 1. validate file type
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # 2. save to disk
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    print(f" PDF saved: {file_path}")

    # 3. init RAG pipeline
    loop = asyncio.get_event_loop()
    vectorstore, qa_chain = await loop.run_in_executor(
        None, init_rag, file_path
    )

    # 4. store in app state
    request.app.state.vectorstore = vectorstore
    request.app.state.qa_chain = qa_chain
    print(f" RAG pipeline ready for: {file.filename}")

    # 5. create session using filename as history name
    session_id = await create_session(
        request.app.state.pool,
        history_name=file.filename
    )
    request.app.state.current_session_id = session_id
    print(f" Session auto-created: {session_id}")

    return {
        "message": f"'{file.filename}' uploaded and processed successfully",
        "filename": file.filename,
        "session_id": session_id,    # ← THIS LINE was missing
        "status": "ready"
    }