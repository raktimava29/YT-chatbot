const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "https://vidquery-npa6.onrender.com"
).replace(/\/$/, "");

export interface IndexTranscriptResponse {
  message: string;
  video_id: string;
  total_chunks: number;
}

export interface ChatSource {
  chunk_id: string;
  score: number;
  content: string;
  start_time: number | null;
  end_time: number | null;
  youtube_url?: string;
}

export interface ChatResponse {
  answer: string;
  sources: ChatSource[];
}

async function request<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new Error("Could not connect to VidQuery server. Check your internet connection and try again.");
  }

  const payload: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const detail =
      payload && typeof payload === "object" && "detail" in payload
        ? String((payload as { detail: unknown }).detail)
        : `Request failed (${response.status})`;
    throw new Error(detail);
  }

  return payload as T;
}

export function indexTranscript(videoId: string, language = "en") {
  return request<IndexTranscriptResponse>("/transcript/index", {
    video_id: videoId,
    language,
  });
}

export function askVideo(videoId: string, question: string, signal?: AbortSignal) {
  return request<ChatResponse>("/chat/ask", {
    video_id: videoId,
    question,
  }, signal);
}
