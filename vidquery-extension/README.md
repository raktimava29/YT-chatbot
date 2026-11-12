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
