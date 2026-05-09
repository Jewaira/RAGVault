# RAGVault

A production-ready Retrieval Augmented Generation (RAG) application that lets you chat with your PDF documents, powered by AWS Bedrock (Claude), ChromaDB, and PostgreSQL for persistent session-based chat history.

---

## Features

- **PDF Upload** — Upload any PDF dynamically via API
- **RAG Pipeline** — Retrieves relevant context before answering
- **AWS Bedrock (Claude)** — State-of-the-art LLM for accurate answers
- **PostgreSQL** — Persistent storage for chat sessions and history
- **Session-based Chat** — Continue conversations across requests
- **FastAPI** — High-performance async REST API
- **ChromaDB** — Vector store for semantic document search

---

## Project Structure

```
RAGVault/
├── main.py              ← entry point, only starts the server
├── app.py               ← app creation, lifespan, router registration
├── rag.py               ← RAG pipeline, PDF loading, LLM chain
├── .env                 ← credentials (never commit)
├── .gitignore
├── requirements.txt
├── uploaded_pdfs/       ← uploaded PDFs stored here (auto-created)
├── chroma_db/           ← ChromaDB vector store (auto-created)
├── routes/
│   ├── __init__.py      ← empty, marks routes/ as a package
│   ├── chat.py          ← /chat and /get_session endpoints
│   └── pdf.py           ← /upload_pdf endpoint
└── db/
    ├── __init__.py      ← empty, marks db/ as a package
    ├── config.py        ← reads DB credentials from .env
    ├── init.py          ← creates database and tables on startup
    └── chat.py          ← session and message DB operations
```

---

## Database Schema

```
chat_sessions                        chat_messages
─────────────────────────────        ──────────────────────────────────
session_id  (PK) UUID    ◄────────── session_id  (FK) UUID
history_name     TEXT                message_id  (PK) UUID
created_at       TIMESTAMPTZ         question         TEXT
                                     answer           TEXT
                                     timestamp        TIMESTAMPTZ
```

- One session → many messages (linked by `session_id`)
- `ON DELETE CASCADE` — deleting a session auto-deletes all its messages

---

## Application Flow

```
python main.py
      ↓
uvicorn.run("app:app")           looks for app object in app.py
      ↓
app.py → lifespan() starts
      ↓
create_database_if_not_exists()  creates 'chatdb' if missing
      ↓
get_pool()                       opens connection pool to PostgreSQL
      ↓
init_db()                        creates chat_sessions + chat_messages tables
      ↓
app.include_router()             registers routes from routes/
      ↓
App ready at http://127.0.0.1:8000
      ↓
POST /upload_pdf                 upload your PDF → RAG pipeline initialized
      ↓
POST /chat                       ask questions → answers stored in PostgreSQL
      ↓
GET  /get_session                retrieve full chat history
```

---

## Setup & Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/RAGVault.git
cd RAGVault
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install and start PostgreSQL

- Download from: https://www.postgresql.org/download/windows/
- Recommended version: 16.x
- During installation, set a password for the `postgres` user

### 5. Create the `.env` file

```ini
DB_HOST=localhost
DB_PORT=5432
DB_NAME=chatdb
DB_USER=postgres
DB_PASSWORD=your_postgres_password
```

### 6. Configure AWS Bedrock

```bash
aws configure
```

Or set directly in `.env`:

```ini
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=deafut-region
```

### 7. Run the application

```bash
python main.py
```

You should see:

```
Database 'chatdb' already exists.
Database tables initialized.
DB pool ready
No PDF loaded yet — upload via POST /upload_pdf
INFO: Uvicorn running on http://127.0.0.1:8000
```

---

## `.gitignore`

Make sure your `.gitignore` includes at minimum:

```
.env
venv/
__pycache__/
uploaded_pdfs/
chroma_db/
```

---

## API Endpoints

### `POST /upload_pdf`

Upload a PDF file and initialize the RAG pipeline.

> ⚠️ **Must be called before `/chat`.** The chat endpoint will fail if no PDF has been uploaded yet.

**Request:**
```
Content-Type: multipart/form-data
file: your_document.pdf
```

**Response:**
```json
{
    "message": "'your_document.pdf' uploaded and processed successfully",
    "filename": "your_document.pdf",
    "status": "ready"
}
```

---

### `POST /chat`

Send a question and get an answer from your uploaded PDF.

**Request Body:**
```json
{
    "question": "What is system design?",
    "session_id": null
}
```

- `question` — required
- `session_id` — optional. If `null`, a new session is auto-created

**Response:**
```json
{
    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "message_id": "1111-2222-3333-4444-555566667777",
    "question": "What is system design?",
    "answer": "System design is the process of..."
}
```

> ⚠️ **Save the returned `session_id`** to continue this conversation in future requests.

---

### `GET /get_session`

Retrieve the full chat history for a session.

**Request:**
```
GET /get_session?session_id=a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**Response:**
```json
{
    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "history": [
        {
            "message_id": "1111-2222-...",
            "question": "What is system design?",
            "answer": "System design is...",
            "timestamp": "2024-01-01T10:00:00Z"
        }
    ]
}
```

> **Note:** Returns an empty `history: []` if the `session_id` is invalid or not found.

---

## Usage Example

### Step 1 — Upload your PDF first

```bash
curl -X POST http://127.0.0.1:8000/upload_pdf \
  -F "file=@your_document.pdf"
```

### Step 2 — Start a new conversation

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is system design?"}'
```

### Step 3 — Continue existing conversation

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Can you explain more?", "session_id": "your-session-id-here"}'
```

### Step 4 — Get full chat history

```bash
curl http://127.0.0.1:8000/get_session?session_id=your-session-id-here
```

---

## Requirements

```
fastapi
uvicorn
asyncpg
python-dotenv
langchain
langchain-community
langchain-aws
langchain-core
langchain-text-splitters
chromadb
boto3
pypdf
pydantic
```

Install all:

```bash
pip install -r requirements.txt
```

---

## Tech Stack

| Component     | Technology                              |
|---------------|-----------------------------------------|
| API Framework | FastAPI                                 |
| LLM           | AWS Bedrock (claude-haiku-4-5-20251001) |
| Embeddings    | Amazon Titan Embed Text v2              |
| Vector Store  | ChromaDB                                |
| Database      | PostgreSQL                              |
| DB Driver     | asyncpg                                 |
| RAG Framework | LangChain                               |
| Server        | Uvicorn                                 |