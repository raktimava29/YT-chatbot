import os 
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
    
proxy_url = (
    f"http://{os.environ['PROXY_USERNAME']}:"
    f"{os.environ['PROXY_PASSWORD']}@"
    f"{os.environ['PROXY_HOST']}:"
    f"{os.environ['PROXY_PORT']}"
)

ytt = YouTubeTranscriptApi(
    proxy_config=GenericProxyConfig(
        http_url=proxy_url,
        https_url=proxy_url,
    )
)

def fetch_transcript(video_id: str, language: str="en"):
    transcript = ytt.fetch(video_id, languages=[language])
    
    return [
        {
            "text": snippet.text,
            "start": snippet.start,
            "end": snippet.start + snippet.duration,
            "duration": snippet.duration
        }
        for snippet in transcript.snippets
    ]
