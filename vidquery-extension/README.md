# VidQuery Chrome Extension

VidQuery lets users index YouTube transcripts and chat with videos from a persistent browser side panel.

## Requirements

- Node.js 20+
- Chrome or Brave with Manifest V3 extension support

## Setup

```bash
npm install
```

Optional backend override: copy `.env.example` to `.env` and set `VITE_API_BASE_URL`.

Default backend: `https://vidquery-npa6.onrender.com`

## Build

```bash
npm run build
```

Load the generated `dist/` folder as an unpacked extension from `chrome://extensions` (or `brave://extensions`). Enable Developer mode, choose **Load unpacked**, and select `dist/`.

## Phase 4 features

- Separate chat history for each YouTube video
- Multiple sessions per video
- Automatic message persistence in `chrome.storage.local`
- Restore sessions when side panel reopens
- Create, rename, switch, and delete sessions
- Persist indexed-video state, so reopening a conversation does not require re-indexing
- Suggested questions and clickable transcript citations

Chat history, selected sessions, and indexed-video IDs stay in browser local extension storage. No chat history is sent to the backend for storage.


## Phase 5 chat improvements

- Assistant answers render lightweight Markdown (headings, lists, emphasis, inline code, fenced code blocks).
- Sources stay collapsed by default. Click the Sources row/arrow to expand timestamp citations.
- Copy answer, retry failed response, and stop the active browser request.
- Stop aborts the extension's fetch request; backend inference may continue if server does not support cancellation.

The current `/chat/ask` endpoint returns a complete JSON response, not a token stream. True token-by-token streaming requires a streaming endpoint in the FastAPI backend; this phase does not pretend otherwise.

## Token streaming (Phase 6)

The extension now uses `POST /chat/stream` instead of waiting for the complete `POST /chat/ask` JSON response. The FastAPI endpoint streams Server-Sent Events (SSE):

- `{"type":"token","content":"..."}` — append generated text immediately.
- `{"type":"sources","sources":[...]}` — deliver timestamp citations after generation.
- `{"type":"done"}` — mark response complete.
- `{"type":"error","detail":"..."}` — report a stream failure.

The existing `POST /chat/ask` endpoint remains available for backward compatibility. Transcript retrieval and reranking remain unchanged. Generation uses LangChain `rag_chain.astream(...)` with the existing Groq model.

### Deploy streaming backend

1. Copy updated backend files `services/rag.py` and `routers/chat_router.py` into backend repository.
2. Commit and push changes to GitHub.
3. Deploy latest backend revision on Render.
4. Verify `POST https://YOUR_BACKEND/chat/stream` returns `Content-Type: text/event-stream` when sent JSON body `{"video_id":"VIDEO_ID","question":"Summarize this video"}`. Use a video that has already been indexed.
5. Rebuild extension with `npm install` and `npm run build`.
6. Reload unpacked extension from `dist/`.

Do not switch extension to streaming before deploying backend update. Older backend will return 404 for `/chat/stream`.

### Stop generation

The Stop button aborts the browser fetch. This closes the streaming response; the UI keeps any partial answer already received. Sources arrive only after successful generation completes.
