from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig

USERNAME = "ixljzrkx"
PASSWORD = "mh73piib4i1y"

proxies = [
    ("64.137.96.74", 6641),
    ("198.23.243.226", 6361),
    ("38.154.185.97", 6370),
    ("84.247.60.125", 6095),
    ("191.96.254.138", 6185),
    ("198.46.161.42", 5092),
    ("64.137.10.153", 5803),
    ("104.164.49.38", 7693),
    ("23.26.71.145", 5628),
]

for host, port in proxies:
    print(f"\nTesting {host}:{port}")

    proxy_url = f"http://{USERNAME}:{PASSWORD}@{host}:{port}"

    try:
        ytt = YouTubeTranscriptApi(
            proxy_config=GenericProxyConfig(
                http_url=proxy_url,
                https_url=proxy_url,
            )
        )

        transcript = ytt.fetch(
            "W4EwfEU8CGA",
            languages=["en"],
        )

        print("SUCCESS:", transcript.snippets[:2])
        print("WORKING PROXY:", host, port)
        break

    except Exception as e:
        print(type(e).__name__, str(e)[:250])