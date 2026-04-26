"""
app/api/routes/chat.py
───────────────────────
Chat history management routes.

FUTURE IMPLEMENTATION:
  POST /api/v1/chat        – send message, save to history, return answer
  GET  /api/v1/chat        – get all chat sessions
  GET  /api/v1/chat/{id}   – get chat history for session
  DELETE /api/v1/chat/{id} – delete session
"""

from fastapi import APIRouter

router = APIRouter()


@router.post("/", summary="Chat (stub)")
async def chat():
    return {"message": "Chat endpoint – to be implemented."}


@router.get("/", summary="List chat sessions (stub)")
async def list_chats():
    return {"message": "List chats – to be implemented."}


@router.get("/{session_id}", summary="Get chat history (stub)")
async def get_chat(session_id: str):
    return {"message": f"Chat history for {session_id} – to be implemented."}
