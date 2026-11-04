from fastapi import APIRouter, HTTPException

from schemas.chat import ChatRequest
from services.rag import ask_video

router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)

@router.post("/ask")
def chat(request: ChatRequest):
    try:
        return ask_video(
            video_id=request.video_id,
            question=request.question
        )
        
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc)
        ) from exc