from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig
from pydantic import BaseModel, Field

class TranscriptRequest(BaseModel):
    video_id: str
    language: str = "en"
    
class TranscriptSearchRequest(BaseModel):
    video_id: str
    query: str
    k: int = Field(default=4, ge=1, le=20)
    
ytt = YouTubeTranscriptApi(
        # proxy_config=GenericProxyConfig(
        #     http_url="http://127.0.0.1:8000",
        #     https_url="http://127.0.0.1:8000",
        # )
    )

def fetch_transcript(video_id: str, language: str="en"):
    transcript = ytt.fetch(video_id, languages=[language])
    return " ".join(snippet.text for snippet in transcript)
