import json
import logging
import os
from collections.abc import AsyncIterator

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from starlette.concurrency import run_in_threadpool

from core.errors import DependencyUnavailableError
from services.reranker import retrieve_and_rerank

load_dotenv()

logger = logging.getLogger(__name__)

llm = ChatGroq(
    model="qwen/qwen3.8-27b",
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY"),
)

prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You are a helpful assistant answering questions about YouTube videos.

Answer using ONLY the provided transcript context.

Rules:
1. Do not use external knowledge.
2. Do not invent information.
3. If context does not contain answer, clearly say:
   "This information is not available in the video transcript."
4. Give clear, concise answers.
5. Explain technical concepts using context provided.
6. Do not mention retrieval or reranking.
7. When relevant, mention timestamp references from the provided context
   using [HH:MM:SS] format.
8. Only use timestamps explicitly provided in the context.
   Never invent timestamps.
9. Place timestamp references directly beside the claims they support.
   Do not append a separate timestamp list at the end.
"""
    ),
    (
        "human",
        """
Transcript context:

{context}

Question:
{question}

Answer:
"""
    ),
])

rag_chain = prompt | llm | StrOutputParser()

UNAVAILABLE_MESSAGE = "This information is not available in the video transcript."


def format_timestamp(seconds: float) -> str:
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def retrieve_video_context(video_id: str, question: str):
    """Retrieve and format transcript context shared by regular and streaming chat."""
    try:
        results = retrieve_and_rerank(
            video_id=video_id,
            query=question,
            top_k=4,
            candidate_k=20,
        )
    except Exception as exc:
        logger.exception("Transcript retrieval failed")
        raise DependencyUnavailableError("Transcript retrieval unavailable") from exc

    if not results or float(results[0][1]) < -5.0:
        return None, []

    context_parts = []
    sources = []

    for doc, score in results:
        start_time = doc.metadata.get("start_time")
        end_time = doc.metadata.get("end_time")
        if start_time is not None and end_time is not None:
            timestamp = (
                f"[{format_timestamp(start_time)} - "
                f"{format_timestamp(end_time)}]"
            )
        else:
            timestamp = "[Timestamp unavailable]"
        context_parts.append(f"{timestamp}\n{doc.page_content}")

        source = {
            "chunk_id": doc.metadata["chunk_id"],
            "score": round(float(score), 4),
            "content": doc.page_content,
            "start_time": start_time,
            "end_time": end_time,
        }
        if start_time is not None:
            source["youtube_url"] = (
                f"https://www.youtube.com/watch?v={video_id}"
                f"&t={int(start_time)}s"
            )
        sources.append(source)

    return "\n\n".join(context_parts), sources


def ask_video(video_id: str, question: str):
    context, sources = retrieve_video_context(video_id, question)
    if context is None:
        return {"answer": UNAVAILABLE_MESSAGE, "sources": []}

    try:
        answer = rag_chain.invoke({"context": context, "question": question})
    except Exception as exc:
        logger.exception("Answer generation failed")
        raise DependencyUnavailableError("Answer generation unavailable") from exc

    return {"answer": answer, "sources": sources}


async def stream_video_answer(video_id: str, question: str) -> AsyncIterator[str]:
    """Yield Server-Sent Events containing answer tokens, sources, and completion."""
    def event(payload: dict) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    try:
        context, sources = await run_in_threadpool(
            retrieve_video_context, video_id, question
        )
        if context is None:
            yield event({"type": "token", "content": UNAVAILABLE_MESSAGE})
            yield event({"type": "sources", "sources": []})
            yield event({"type": "done"})
            return

        async for token in rag_chain.astream({
            "context": context,
            "question": question,
        }):
            if token:
                yield event({"type": "token", "content": token})

        yield event({"type": "sources", "sources": sources})
        yield event({"type": "done"})
    except Exception:
        logger.exception("Streaming answer generation failed")
        yield event({
            "type": "error",
            "detail": "Answer generation unavailable. Please retry.",
        })
