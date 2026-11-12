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
export interface StreamCallbacks {
  onToken: (token: string) => void;
  onSources: (sources: ChatSource[]) => void;
}

/** Read VidQuery SSE events and forward generated tokens as they arrive. */
export async function streamVideoAnswer(
  videoId: string,
  question: string,
  callbacks: StreamCallbacks,
  signal?: AbortSignal,
): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "text/event-stream" },
      body: JSON.stringify({ video_id: videoId, question }),
      signal,
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new Error("Could not connect to VidQuery server. Check your internet connection and try again.");
  }

  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);
    const detail = payload && typeof payload === "object" && "detail" in payload
      ? String((payload as { detail: unknown }).detail)
      : `Request failed (${response.status})`;
    throw new Error(detail);
  }
  if (!response.body) throw new Error("Streaming response body unavailable.");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let completed = false;

  const processEvent = (rawEvent: string) => {
    const data = rawEvent.split("\n")
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trimStart())
      .join("\n");
    if (!data) return;
    const event = JSON.parse(data) as
      | { type: "token"; content: string }
      | { type: "sources"; sources: ChatSource[] }
      | { type: "done" }
      | { type: "error"; detail: string };
    if (event.type === "token") callbacks.onToken(event.content);
    if (event.type === "sources") callbacks.onSources(event.sources ?? []);
    if (event.type === "done") completed = true;
    if (event.type === "error") throw new Error(event.detail);
  };

  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done }).replace(/\r\n/g, "\n");
      let boundary = buffer.indexOf("\n\n");
      while (boundary !== -1) {
        const rawEvent = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        processEvent(rawEvent);
        boundary = buffer.indexOf("\n\n");
      }
      if (done) break;
    }
    if (buffer.trim()) processEvent(buffer);
    if (!completed) throw new Error("VidQuery stream ended before completion.");
  } finally {
    reader.releaseLock();
  }
}

