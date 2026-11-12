from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from schemas.chat import ChatRequest
from services.rag import ask_video, stream_video_answer

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/ask")
def chat(request: ChatRequest):
    """Non-streaming endpoint retained for existing clients."""
    return ask_video(
        video_id=request.video_id,
        question=request.question,
    )


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """Stream generated answer as Server-Sent Events."""
    return StreamingResponse(
        stream_video_answer(
            video_id=request.video_id,
            question=request.question,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
