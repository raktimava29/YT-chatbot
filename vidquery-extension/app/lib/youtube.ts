export interface YouTubeVideo {
  videoId: string;
  title: string;
  url: string;
  thumbnailUrl: string;
  channelUrl?: string;
}

const VIDEO_ID_PATTERN = /^[a-zA-Z0-9_-]{11}$/;

/** Extract supported YouTube video IDs from watch, shorts, live, embed and youtu.be URLs. */
export function extractYouTubeVideoId(rawUrl: string): string | null {
  try {
    const url = new URL(rawUrl);
    const hostname = url.hostname.toLowerCase().replace(/^www\./, "").replace(/^m\./, "");
    let videoId: string | null = null;

    if (hostname === "youtu.be") {
      videoId = url.pathname.split("/").filter(Boolean)[0] ?? null;
    } else if (hostname === "youtube.com") {
      if (url.pathname === "/watch") {
        videoId = url.searchParams.get("v");
      } else {
        const match = url.pathname.match(/^\/(?:shorts|live|embed|v)\/([a-zA-Z0-9_-]{11})(?:\/|$)/);
        videoId = match?.[1] ?? null;
      }
    }

    return videoId && VIDEO_ID_PATTERN.test(videoId) ? videoId : null;
  } catch {
    return null;
  }
}

export function buildYouTubeVideo(tab: chrome.tabs.Tab): YouTubeVideo | null {
  if (!tab.url) return null;
  const videoId = extractYouTubeVideoId(tab.url);
  if (!videoId) return null;

  const title = (tab.title ?? "")
    .replace(/\s*[-|–]\s*YouTube\s*$/i, "")
    .trim();

  return {
    videoId,
    title: title || "YouTube video",
    url: `https://www.youtube.com/watch?v=${videoId}`,
    thumbnailUrl: `https://img.youtube.com/vi/${videoId}/hqdefault.jpg`,
  };
}
