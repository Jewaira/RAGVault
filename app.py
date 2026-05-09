# app.py
import asyncio
import os
from fastapi import FastAPI
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from db.config import DBConfig
from db.init import get_pool, init_db, create_database_if_not_exists
from routes.chat import router as chat_router
from routes.pdf import router as pdf_router

load_dotenv()

UPLOAD_DIR = "uploaded_pdfs"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    load_dotenv()
    config = DBConfig()

    await create_database_if_not_exists(config)
    app.state.pool = await get_pool(config)
    await init_db(app.state.pool)
    print(" DB pool ready")

    app.state.vectorstore = None
    app.state.qa_chain = None
    print("  No PDF loaded yet — upload via POST /upload_pdf")

    yield

    # SHUTDOWN
    await app.state.pool.close()
    print(" DB pool closed")


# create app
app = FastAPI(lifespan=lifespan)

# register routers
app.include_router(pdf_router)
app.include_router(chat_router)