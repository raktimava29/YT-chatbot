from fastapi import APIRouter, HTTPException
from services.transcript import (TranscriptRequest, TranscriptSearchRequest, TranscriptProviderError, fetch_transcript)

from services.transcript import TranscriptRequest, TranscriptSearchRequest,fetch_transcript
from services.splitter import split_transcript
from services.vector_store import create_vector_store, search_transcript

router = APIRouter(prefix="/transcript", tags=["Transcript"])

@router.post("/")
def get_transcript(request: TranscriptRequest):
    try:
        text = fetch_transcript(
            request.video_id,
            request.language,
        )

        chunks = split_transcript(
            transcript=text,
            video_id=request.video_id,
        )

        return {
            "video_id": request.video_id,
            "language": request.language,
            "transcript": text,
            "chunks": [
                {
                    "text": chunk.page_content,
                    "metadata": chunk.metadata,
                }
                for chunk in chunks
            ],
        }

    except TranscriptProviderError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@router.post("/index")
def index_transcript(request: TranscriptRequest):
    try:
        text = fetch_transcript(
            request.video_id,
            request.language,
        )

        chunks = split_transcript(
            transcript=text,
            video_id=request.video_id,
        )

        for chunk in chunks:
            chunk.metadata["language"] = request.language

        create_vector_store(
            chunks,
            request.video_id,
        )

        return {
            "message": "Transcript indexed successfully",
            "video_id": request.video_id,
            "total_chunks": len(chunks),
        }

    except TranscriptProviderError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@router.post("/search")
def search(request: TranscriptSearchRequest):
    try:
        results = search_transcript(
            video_id=request.video_id,
            query=request.query,
            k=request.k,
        )

        return {
            "video_id": request.video_id,
            "query": request.query,
            "results": results,
        }

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc