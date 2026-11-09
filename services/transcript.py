
import os
import time
import logging

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

SUPADATA_BASE_URL = "https://api.supadata.ai/v1"
SUPADATA_TIMEOUT = 30.0
SUPADATA_MAX_WAIT = 120
SUPADATA_POLL_INTERVAL = 2


class TranscriptRequest(BaseModel):
    video_id: str
    language: str = "en"


class TranscriptSearchRequest(BaseModel):
    video_id: str
    query: str
    k: int = Field(default=4, ge=1, le=20)


class TranscriptProviderError(Exception):
    pass


def _request_transcript(client: httpx.Client, video_id: str, language: str):
    response = client.get(
        "/transcript",
        params={
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "lang": language,
            "text": "false",
            "mode": "native",
        },
    )

    response.raise_for_status()
    return response.json()


def _wait_for_transcript(client: httpx.Client, job_id: str):
    deadline = time.monotonic() + SUPADATA_MAX_WAIT

    while time.monotonic() < deadline:
        response = client.get(f"/transcript/{job_id}")
        response.raise_for_status()

        result = response.json()
        status = result.get("status")

        if status == "completed":
            return result

        if status == "failed":
            raise TranscriptProviderError(
                f"Supadata transcript job failed: {result.get('error', 'Unknown error')}"
            )

        time.sleep(SUPADATA_POLL_INTERVAL)

    raise TranscriptProviderError(
        "Supadata transcript processing timed out"
    )


def fetch_transcript(video_id: str, language: str = "en"):
    api_key = os.getenv("SUPADATA_API_KEY")

    if not api_key:
        raise TranscriptProviderError(
            "SUPADATA_API_KEY environment variable is missing"
        )

    headers = {
        "x-api-key": api_key,
    }

    try:
        with httpx.Client(
            base_url=SUPADATA_BASE_URL,
            headers=headers,
            timeout=SUPADATA_TIMEOUT,
        ) as client:

            result = _request_transcript(
                client,
                video_id,
                language,
            )
            
            job_id = result.get("jobId")

            if job_id:
                result = _wait_for_transcript(client, job_id)

            segments = result.get("content")

            if not isinstance(segments, list):
                raise TranscriptProviderError(
                    "Supadata returned invalid transcript content"
                )

            transcript = []

            for segment in segments:
                start = segment["offset"] / 1000
                duration = segment["duration"] / 1000

                transcript.append({
                    "text": segment["text"],
                    "start": start,
                    "end": start + duration,
                    "duration": duration,
                })

            if not transcript:
                raise TranscriptProviderError(
                    "Supadata returned an empty transcript"
                )

            return transcript

    except httpx.HTTPStatusError as exc:
        logger.error(
            "Supadata HTTP error: status=%s",
            exc.response.status_code,
        )
        raise TranscriptProviderError(
            f"Supadata request failed with status {exc.response.status_code}"
        ) from exc

    except httpx.RequestError as exc:
        logger.exception("Supadata connection failed")
        raise TranscriptProviderError(
            "Could not connect to Supadata"
        ) from exc
