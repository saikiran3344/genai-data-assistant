import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from dotenv import load_dotenv

from ingestion.pipeline import run_ingestion
from llm.session import ChatSession
from vectorstore.store import setup_table, get_chunk_count, clear_documents
from auth.models import setup_auth_tables
from auth.utils import (
    register_user, get_user_by_email, verify_password,
    create_access_token, decode_token, get_user_by_id,
    deduct_token, has_tokens, submit_token_request,
    get_all_users, get_pending_requests,
    approve_token_request, reject_token_request,
    allocate_tokens_directly
)
load_dotenv()

app = FastAPI(
    title = "GENAI DATA ASSISTANT",
    description= "AI- powered assistant that answers questions over CSV, Excel, PDF",
    version = "2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_methods = ["*"],
    allow_headers = ["*"]
)

# Setup tables on startup
@app.on_event("startup")
def startup():
    setup_table()
    setup_auth_tables()
    print("Database tables ready.")

security    = HTTPBearer()
UPLOAD_DIR  = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# One session store per user_id
sessions: dict[int, ChatSession] = {}


# ── Auth dependency ─────────────────────────────────────

def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    payload = decode_token(creds.credentials)
    if not payload:
        raise HTTPException(status_code=401,
                            detail="Invalid or expired token")
    user = get_user_by_id(payload["user_id"])
    if not user or not user["is_active"]:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(status_code=403,
                            detail="Admin access required")
    return user


# ── Request models ──────────────────────────────────────

class RegisterRequest(BaseModel):
    email:    str
    password: str

class LoginRequest(BaseModel):
    email:    str
    password: str

class QuestionRequest(BaseModel):
    question: str

class TokenRequestModel(BaseModel):
    message:          str
    tokens_requested: int = 100

class ApproveRequest(BaseModel):
    tokens_to_add: int

class AllocateRequest(BaseModel):
    user_id: int
    tokens:  int


# ── Auth routes ─────────────────────────────────────────

@app.post("/register")
def register(req: RegisterRequest):
    if len(req.password) < 6:
        raise HTTPException(status_code=400,
                            detail="Password must be at least 6 characters")
    
    
    try:
        user = register_user(req.email, req.password)
        return {
            "message":          "Account created successfully",
            "email":            user["email"],
            "tokens_remaining": user["tokens_remaining"]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/login")
def login(req: LoginRequest):
    user = get_user_by_email(req.email)
    if not user or not verify_password(req.password,
                                       user["hashed_password"]):
        raise HTTPException(status_code=401,
                            detail="Invalid email or password")
    if not user["is_active"]:
        raise HTTPException(status_code=403,
                            detail="Account is deactivated")
    token = create_access_token({"user_id": user["id"],
                                  "role":    user["role"]})
    return {
        "access_token":     token,
        "token_type":       "bearer",
        "role":             user["role"],
        "tokens_remaining": user["tokens_remaining"]
    }


@app.get("/me")
def get_me(user: dict = Depends(get_current_user)):
    return user


# ── Chat routes (protected) ─────────────────────────────

@app.post("/ask")
def ask_question(req: QuestionRequest,
                 user: dict = Depends(get_current_user)):

    # Check quota
    if not has_tokens(user["id"]):
        raise HTTPException(
            status_code=429,
            detail="Token quota exceeded. Request more tokens from admin."
        )

    # Get or create session for this user
    if user["id"] not in sessions:
        sessions[user["id"]] = ChatSession()

    result = sessions[user["id"]].ask(req.question)

    # Deduct 1 token per question
    deduct_token(user["id"], req.question, tokens_used=1)

    # Refresh user data to get updated token count
    updated = get_user_by_id(user["id"])

    return {
        "answer":           result["answer"],
        "sources":          result["sources"],
        "retrieved_chunks": result["retrieved_chunks"],
        "tokens_remaining": updated["tokens_remaining"]
    }


@app.get("/token-status")
def token_status(user: dict = Depends(get_current_user)):
    return {
        "tokens_remaining": user["tokens_remaining"],
        "questions_asked":  user["questions_asked"]
    }


@app.post("/clear-history")
def clear_history(user: dict = Depends(get_current_user)):
    if user["id"] in sessions:
        sessions[user["id"]].clear()
    return {"message": "Conversation cleared"}


# ── Token request routes ────────────────────────────────

@app.post("/request-tokens")
def request_tokens(req: TokenRequestModel,
                   user: dict = Depends(get_current_user)):
    req_id = submit_token_request(
        user["id"], req.message, req.tokens_requested
    )
    return {
        "message":    "Token request submitted. Admin will review it.",
        "request_id": req_id
    }


# ── Upload route (protected) ────────────────────────────

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in {".csv", ".xlsx", ".pdf"}:
        raise HTTPException(status_code=400,
                            detail=f"Unsupported file type: {ext}")

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    docs = run_ingestion(file_path)
    return {
        "message":      f"{file.filename} ingested successfully",
        "chunks_stored": len(docs),
        "total_chunks":  get_chunk_count()
    }


# ── Admin routes ────────────────────────────────────────

@app.get("/admin/users")
def admin_get_users(admin: dict = Depends(require_admin)):
    return {"users": get_all_users()}


@app.get("/admin/requests")
def admin_get_requests(admin: dict = Depends(require_admin)):
    return {"requests": get_pending_requests()}


@app.post("/admin/requests/{request_id}/approve")
def admin_approve(request_id: int,
                  req: ApproveRequest,
                  admin: dict = Depends(require_admin)):
    approve_token_request(request_id, req.tokens_to_add)
    return {"message": f"Approved. Added {req.tokens_to_add} tokens."}


@app.post("/admin/requests/{request_id}/reject")
def admin_reject(request_id: int,
                 admin: dict = Depends(require_admin)):
    reject_token_request(request_id)
    return {"message": "Request rejected."}


@app.post("/admin/allocate")
def admin_allocate(req: AllocateRequest,
                   admin: dict = Depends(require_admin)):
    allocate_tokens_directly(req.user_id, req.tokens)
    return {
        "message": f"Allocated {req.tokens} tokens to user {req.user_id}"
    }


@app.put("/admin/users/{user_id}/deactivate")
def admin_deactivate(user_id: int,
                     admin: dict = Depends(require_admin)):
    from auth.models import get_connection
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("UPDATE users SET is_active = FALSE WHERE id = %s",
                (user_id,))
    conn.commit()
    cur.close()
    conn.close()
    return {"message": f"User {user_id} deactivated"}


@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}


@app.get("/stats")
def stats(user: dict = Depends(get_current_user)):
    return {
        "total_chunks":       get_chunk_count(),
        "conversation_turns": len(sessions.get(
            user["id"], ChatSession()).get_history()) // 2,
        "uploaded_files":     os.listdir(UPLOAD_DIR)
    }
