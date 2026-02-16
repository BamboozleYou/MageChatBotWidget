# Mage Data AI Chatbot

A self-hosted RAG (Retrieval-Augmented Generation) chatbot for [magedata.ai](https://magedata.ai). An AI-powered assistant that answers questions about Mage Data's products and services, grounded in your own documentation.

**Two ways to use this project:**

| Path | Use When | File |
|------|----------|------|
| **🧪 Local Testing** | You want to test the chatbot standalone, no Astro needed | `test-chatbot.html` |
| **🚀 Astro Integration** | You're deploying into your live magedata.ai Astro site | `Chatbot.astro` |

Both paths share the **same backend**. Set up the backend once, then choose your frontend path.

**Cost: $0/month** on free tiers (OpenRouter LLM + HuggingFace embeddings + self-hosted ChromaDB).

---

## Table of Contents

1. [Architecture](#architecture)
2. [Project Structure](#project-structure)
3. [Backend Setup (Required for Both Paths)](#backend-setup-required-for-both-paths)
4. [Path A — Local Testing](#path-a--local-testing)
5. [Path B — Astro Site Integration](#path-b--astro-site-integration)
6. [Differences Between Local & Astro](#differences-between-local--astro)
7. [Configuration Reference](#configuration-reference)
8. [How the RAG Pipeline Works](#how-the-rag-pipeline-works)
9. [Lead Capture & HubSpot](#lead-capture--hubspot)
10. [Analytics Events](#analytics-events)
11. [Backend Deployment (Production)](#backend-deployment-production)
12. [Known Issues & Fixes](#known-issues--fixes)
13. [Testing Checklist](#testing-checklist)
14. [Cost Breakdown](#cost-breakdown)
15. [Troubleshooting](#troubleshooting)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  FRONTEND (choose one)                                          │
│                                                                 │
│  ┌─────────────────────┐   ┌──────────────────────────────┐    │
│  │ 🧪 test-chatbot.html│   │ 🚀 Chatbot.astro             │    │
│  │ Open in any browser │   │ Inside your Astro site       │    │
│  │ No build step       │   │ transition:persist           │    │
│  │ localhost:8000      │   │ Deferred loading             │    │
│  └────────┬────────────┘   │ Cookie consent coexistence   │    │
│           │                │ GA4 analytics                │    │
│           │                └──────────┬───────────────────┘    │
│           │                           │                         │
│           └───────────┬───────────────┘                         │
│                       ▼                                         │
│              POST /api/chat                                     │
│              POST /api/lead                                     │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│  BACKEND (shared — FastAPI + Python)                            │
│                                                                 │
│  main.py  ──→  rag.py  ──→  ChromaDB (vector store, local)     │
│                         ──→  OpenRouter LLM (free tier)         │
│                         ──→  HuggingFace Embeddings (local)     │
│            ──→  HubSpot (lead webhook, optional)                │
└─────────────────────────────────────────────────────────────────┘
```

**Data flow for each chat message:**

1. User types a question in the widget
2. Frontend sends the conversation history to `POST /api/chat`
3. Backend retrieves relevant document chunks via ensemble search (semantic + keyword)
4. Retrieved context + conversation history are sent to the LLM
5. LLM generates a response grounded in your documentation
6. Response + source links are returned and displayed in the chat

---

## Project Structure

```
mage-chatbot-project/
│
├── 📄 README.md                          ← You are here
├── 📄 test-chatbot.html                  ← 🧪 LOCAL TESTING (open in browser, no build)
├── 📄 Dockerfile                         ← Docker deployment for backend
├── 📄 .gitignore
│
├── backend/                              ← ⚙️  SHARED BACKEND (both paths use this)
│   ├── main.py                           │  FastAPI app: /api/chat, /api/lead, /api/health
│   ├── rag.py                            │  RAG pipeline: retrieval → prompt → LLM → response
│   ├── ingest.py                         │  Knowledge base ingestion (PDFs + llms.txt)
│   ├── requirements.txt                  │  Python dependencies
│   └── .env.example                      │  Environment variable template
│
└── frontend/                             ← 🚀 ASTRO INTEGRATION (copy into your Astro site)
    └── src/
        ├── components/interactive/
        │   └── Chatbot.astro             │  Main widget (HTML + CSS + JS, self-contained)
        ├── utils/
        │   └── chatbot.ts                │  Configuration file (API endpoint, UI strings)
        └── styles/
            └── chatbot.css               │  Supplementary animations (optional)
```

---

## Backend Setup (Required for Both Paths)

> **Do this first** — both local testing and Astro integration need the backend running.

### Step 1: Install Dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Requires Python 3.10+.** Key dependencies: FastAPI, ChromaDB, LangChain, sentence-transformers, rank_bm25.

### Step 2: Get Your Free API Key

1. Go to [openrouter.ai](https://openrouter.ai) and sign up (**no credit card needed**)
2. Create a key at [openrouter.ai/keys](https://openrouter.ai/keys)

### Step 3: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and paste your key:

```env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

Full list of variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENROUTER_API_KEY` | **Yes** | — | Free key from openrouter.ai |
| `LLM_MODEL` | No | `meta-llama/llama-3.3-70b-instruct:free` | Any OpenRouter model ID |
| `CHROMA_DIR` | No | `chroma_db` | Path to vector store directory |
| `ALLOWED_ORIGINS` | No | `*` | CORS origins (comma-separated) |
| `HUBSPOT_PORTAL_ID` | No | — | For lead capture → HubSpot |
| `HUBSPOT_FORM_ID` | No | — | For lead capture → HubSpot |

### Step 4: Ingest Your Knowledge Base

Create a `documents/` folder inside `backend/` and drop your PDFs in:

```bash
mkdir documents
# Copy your PDFs into documents/
```

Run the ingestion:

```bash
# PDFs + llms.txt sitemap
python ingest.py --pdf-dir ./documents --llms-txt ./llms.txt

# PDFs only
python ingest.py --pdf-dir ./documents

# Re-ingest from scratch (clears old data)
python ingest.py --pdf-dir ./documents --clear
```

The script supports three knowledge sources:

| Source | Flag | What It Does |
|--------|------|-------------|
| PDFs | `--pdf-dir ./documents` | Loads product docs, datasheets, whitepapers |
| llms.txt | `--llms-txt ./llms.txt` | Parses a structured sitemap with H2/H3 sections |
| Manual entries | Built-in | Adds deployment options, databases, pricing, compliance info |

**Chunking:** Documents are split into ~1500-character chunks with 200-character overlap, using section headings as natural boundaries. Each chunk keeps its source metadata for attribution.

### Step 5: Start the Backend

```bash
uvicorn main:app --reload --port 8000
```

**Verify it works:**

```bash
# Health check
curl http://localhost:8000/api/health
# → {"status":"ok","timestamp":"..."}

# Test chat
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"What is Mage Data?"}]}'
# → {"reply":"Mage Data is...","sources":[...]}
```

> **Leave this terminal running.** Open a new terminal for the next steps.

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/chat` | Send messages, get AI response + source links |
| `POST` | `/api/lead` | Submit lead capture data (email, name, company) |
| `GET` | `/api/health` | Health check — returns `{"status": "ok"}` |

**POST /api/chat — Request:**
```json
{
  "messages": [
    { "role": "user", "content": "What products does Mage Data offer?" }
  ],
  "sessionId": "optional-uuid"
}
```

**POST /api/chat — Response:**
```json
{
  "reply": "Mage Data offers several data security products including...",
  "sources": [
    { "title": "Static Data Masking", "url": "/products/static-data-masking.html" },
    { "title": "Dynamic Data Masking", "url": "/products/dynamic-data-masking.html" }
  ]
}
```

---

## Path A — Local Testing

> **Prerequisites:** Backend is running on `localhost:8000` (see [Backend Setup](#backend-setup-required-for-both-paths) above).

### What You Get

`test-chatbot.html` is a **single, self-contained HTML file** that includes a mock Mage Data website (navbar, hero section, product cards, footer) with the full chatbot widget embedded. No build tools, no Node.js, no Astro — just open it in a browser.

### Steps

#### 1. Open the file

```bash
# macOS
open test-chatbot.html

# Linux
xdg-open test-chatbot.html

# Windows
start test-chatbot.html

# Or just double-click it in your file manager
```

#### 2. Start chatting

Click the orange chat bubble in the bottom-right corner. The widget connects to `http://localhost:8000/api/chat` by default.

You'll see a yellow banner at the top confirming the endpoint:

> 🧪 **Test Page** — Chatbot is connecting to `http://localhost:8000/api/chat`

#### 3. Customize (optional)

To change the API endpoint or widget behavior, edit the `CONFIG` object near line 513:

```js
const CONFIG = {
  apiEndpoint: 'http://localhost:8000/api/chat',  // ← Change this
  leadCapture: {
    enabled: true,
    triggerAfterMessages: 4,    // Show lead form after 4 user messages
  },
  ui: {
    welcomeMessage: "Hi! I'm the Mage Data assistant. How can I help you today?",
    quickReplies: ['Request a demo', 'Learn about products', 'Talk to sales'],
    errorMessage: "Sorry, I'm having trouble connecting...",
  },
};
```

### What to Test Locally

Use this page to verify the full end-to-end flow before integrating into your Astro site:

- [ ] Chat bubble appears and opens/closes smoothly
- [ ] Messages round-trip to the backend and display responses
- [ ] Bot responses include clickable source link pills
- [ ] Typing indicator (3 bouncing dots) shows while waiting
- [ ] Quick reply chips work and disappear after first use
- [ ] Lead capture form appears after N messages
- [ ] After lead capture, **no double bot response** (this was a bug, now fixed)
- [ ] Error message shows gracefully if backend is stopped
- [ ] Mobile layout works (resize browser to < 480px)

### Pointing to a Remote Backend

If your backend is deployed (not on localhost), just change the endpoint:

```js
apiEndpoint: 'https://your-backend.railway.app/api/chat',
```

---

## Path B — Astro Site Integration

> **Prerequisites:** Backend is running (locally or deployed). You have an existing Astro site.

### What You Get

`Chatbot.astro` is a production-ready Astro component with features that `test-chatbot.html` doesn't have:

- **`transition:persist`** — survives Astro View Transition page navigations
- **Deferred loading** — loads after 5s idle or first user interaction (no Lighthouse impact)
- **Cookie consent coexistence** — auto-shifts the chat bubble when a consent banner is visible
- **GA4 analytics** — tracks events with consent checks
- **HubSpot integration** — submits leads to HubSpot forms (client-side + server-side)
- **`astro:after-swap` handling** — re-initializes after View Transition DOM swaps

### Steps

#### 1. Copy files into your Astro project

```bash
# From the mage-chatbot-project root:

# Required — the widget component
cp frontend/src/components/interactive/Chatbot.astro \
   /path/to/your-astro-site/src/components/interactive/Chatbot.astro

# Required — configuration
cp frontend/src/utils/chatbot.ts \
   /path/to/your-astro-site/src/utils/chatbot.ts

# Optional — supplementary animation styles
cp frontend/src/styles/chatbot.css \
   /path/to/your-astro-site/src/styles/chatbot.css
```

#### 2. Update the API endpoint

Open `Chatbot.astro` and find the `CONFIG` object (around line 545):

```js
const CONFIG = {
  apiEndpoint: 'https://your-api-domain.com/api/chat',  // ← YOUR BACKEND URL
  delayMs: 5000,
  leadCapture: {
    enabled: true,
    triggerAfterMessages: 4,
    hubspotPortalId: '',          // ← Fill in if using HubSpot
    hubspotFormId: '',            // ← Fill in if using HubSpot
  },
  ui: {
    title: 'Mage Data Assistant',
    welcomeMessage: "Hi! I'm the Mage Data assistant. How can I help you today?",
    quickReplies: ['Request a demo', 'Learn about products', 'Talk to sales'],
    placeholder: 'Type a message...',
    errorMessage: "Sorry, I'm having trouble connecting...",
  },
};
```

Also update `chatbot.ts` to match:

```ts
export const chatbotConfig = {
  apiEndpoint: 'https://your-api-domain.com/api/chat',
  // ...
};
```

> **For local development** against a local backend, use `http://localhost:8000/api/chat` as the endpoint temporarily. Switch to your production URL before deploying.

#### 3. Add the component to your layout

In your `src/layouts/BaseLayout.astro` (or whichever layout wraps all pages):

```astro
---
import Chatbot from '../components/interactive/Chatbot.astro';
---

<html>
  <body>
    <slot />
    <Footer />

    <!-- Chatbot — add after Footer, before closing </body> -->
    <Chatbot />
  </body>
</html>
```

> **Important:** Place `<Chatbot />` _after_ your `<Footer />` and _before_ `</body>`. The widget is `position: fixed` so it overlays the page content.

#### 4. Import supplementary styles (optional)

If you copied `chatbot.css`, import it in your global stylesheet:

```css
/* In src/styles/global.css */
@import './chatbot.css';
```

This is optional — all essential styles are already inline in `Chatbot.astro`. The CSS file just adds some extra scrollbar and focus-ring refinements.

#### 5. Configure View Transitions (if using them)

If your Astro site uses View Transitions, the widget already handles this via `transition:persist` on the root `<div>` and an `astro:after-swap` event listener. No extra config needed.

If you're **not** using View Transitions, the widget still works fine — the `astro:after-swap` listener simply never fires.

#### 6. Configure Cookie Consent Coexistence

The widget automatically watches for an element with `id="cookie-consent"`. If it detects a visible cookie banner, it shifts the chat bubble up (from `bottom: 24px` to `bottom: 120px`) so they don't overlap.

If your cookie consent banner has a different `id`, update this line in `Chatbot.astro`:

```js
function watchCookieBanner() {
  const banner = document.getElementById('cookie-consent');  // ← Your banner ID
  // ...
}
```

#### 7. Set up CORS on the backend

Make sure your backend allows requests from your Astro site's domain. In `backend/.env`:

```env
ALLOWED_ORIGINS=https://magedata.ai,https://www.magedata.ai,http://localhost:4321
```

#### 8. Build and test

```bash
# In your Astro project
npm run dev        # Start dev server (usually localhost:4321)
```

Verify:
- [ ] Chat bubble appears on all pages
- [ ] Opens/closes, messages work
- [ ] Navigate to another page → chat state is preserved
- [ ] Lead capture form appears and submits
- [ ] No double bot response after lead capture

#### 9. Deploy

Deploy your Astro site as usual (Vercel, Netlify, GitHub Pages, etc.). The chatbot is just another component — no special build config needed.

---

## Differences Between Local & Astro

| Feature | `test-chatbot.html` (Local) | `Chatbot.astro` (Production) |
|---------|----------------------------|------------------------------|
| **How to run** | Double-click / open in browser | Part of Astro build |
| **Default endpoint** | `http://localhost:8000/api/chat` | `https://your-api-domain.com/api/chat` |
| **Build tools needed** | None | Astro |
| **View Transition persistence** | No | Yes (`transition:persist`) |
| **Deferred loading** | No (loads immediately) | Yes (5s idle or first interaction) |
| **Cookie consent coexistence** | No | Yes (MutationObserver) |
| **GA4 analytics** | No | Yes (with consent check) |
| **HubSpot client-side submit** | No | Yes |
| **Backend lead endpoint** | Yes | Yes |
| **Mobile responsive** | Yes | Yes |
| **Keyboard accessible** | Yes | Yes |
| **Session state (survives refresh)** | Yes (sessionStorage) | Yes (sessionStorage) |
| **Lead capture form** | Yes | Yes |
| **Source link pills** | Yes | Yes |
| **The core chatbot logic** | Identical | Identical |

Both files include the **same bug fix** for the double-response issue after lead capture (the `local: true` flag on the "Thanks" message).

---

## Configuration Reference

### CONFIG Object (in both files)

```js
const CONFIG = {
  // ── API ──────────────────────────────────
  apiEndpoint: 'http://localhost:8000/api/chat',  // Backend URL

  // ── Deferred Loading (Astro only) ────────
  delayMs: 5000,                          // Load widget after this many ms

  // ── Lead Capture ─────────────────────────
  leadCapture: {
    enabled: true,                         // true = show lead form
    triggerAfterMessages: 4,               // Show after N user messages
    hubspotPortalId: '',                   // HubSpot portal ID (Astro only)
    hubspotFormId: '',                     // HubSpot form ID (Astro only)
  },

  // ── UI Copy ──────────────────────────────
  ui: {
    title: 'Mage Data Assistant',          // Header title
    welcomeMessage: "Hi! I'm the ...",     // First bot message
    quickReplies: [...],                   // Chip buttons shown initially
    placeholder: 'Type a message...',      // Input placeholder
    errorMessage: "Sorry, I'm having...",  // Shown when API fails
  },
};
```

### Backend .env Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | — | **Required.** Free key from openrouter.ai |
| `LLM_MODEL` | `meta-llama/llama-3.3-70b-instruct:free` | Any OpenRouter model ID |
| `CHROMA_DIR` | `chroma_db` | Path to vector store directory |
| `ALLOWED_ORIGINS` | `*` | CORS origins. Set to your domain(s) in production |
| `HUBSPOT_PORTAL_ID` | — | HubSpot portal ID |
| `HUBSPOT_FORM_ID` | — | HubSpot form ID |

---

## How the RAG Pipeline Works

The RAG pipeline (`rag.py`) runs four steps for every user message:

### 1. Retrieval — Ensemble Search

Two retrievers run in parallel, their results are merged:

- **Semantic retriever** (60% weight) — ChromaDB vector similarity search using `sentence-transformers/all-MiniLM-L6-v2` embeddings. Finds chunks _conceptually_ similar to the query.
- **BM25 keyword retriever** (40% weight) — classic TF-IDF keyword matching. Catches exact terms embedding models might miss (product names, acronyms).

Each retriever returns the top 5 chunks → merged and deduplicated.

### 2. Context Assembly

Retrieved chunks are formatted with source metadata:

```
[Source: Static Data Masking]
Mage Data's Static Data Masking solution permanently replaces sensitive data...

[Source: Deployment Options]
Mage Data supports flexible deployment models including on-premises, cloud...
```

### 3. Prompt Construction

The system prompt enforces strict guardrails:
- Only answer from provided context (no hallucination)
- Redirect off-topic questions back to Mage Data
- For pricing, direct to the contact page
- Keep responses concise (2-3 paragraphs max)
- Include links to relevant product pages

The last 6 conversation turns are included for multi-turn context.

### 4. LLM Call & Response

The assembled prompt goes to the LLM via OpenRouter. The response is returned with source links extracted from the retrieved document metadata.

---

## Lead Capture & HubSpot

### How It Works

1. After N user messages (default: 4), an inline form appears requesting name, email, company
2. The input bar is disabled until the form is submitted
3. On submit, the data is sent to:
   - **HubSpot** — if portal + form IDs are configured (Astro version, client-side)
   - **Backend `/api/lead`** — always, for local logging + optional server-side HubSpot
4. A "Thanks" message displays and chatting resumes
5. The form only appears **once per session** (tracked via sessionStorage)

### HubSpot Setup (Astro version only)

1. In HubSpot, create a form with fields: `email`, `firstname`, `company`, `lead_source`
2. Copy the portal ID and form ID
3. Paste into `CONFIG.leadCapture` in `Chatbot.astro`:
   ```js
   hubspotPortalId: '12345678',
   hubspotFormId: 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
   ```
4. Optionally also set them in `backend/.env` for server-side submission as a backup

---

## Analytics Events

> **Astro version only.** The local test page does not include analytics.

All events fire via `gtag()` and respect cookie consent. Events only fire if `localStorage.getItem('magedata_consent')` returns `{ analytics_storage: 'granted' }`.

| Event Name | Trigger | Label |
|------------|---------|-------|
| `chatbot_opened` | User clicks the chat bubble | — |
| `chatbot_message_sent` | User sends a message | First 50 chars |
| `chatbot_quick_reply` | User clicks a quick reply chip | Chip text |
| `chatbot_lead_capture` | User submits the lead form | `email_collected` |
| `chatbot_link_clicked` | User clicks a source link | Link URL |

---

## Backend Deployment (Production)

When you're ready to move beyond `localhost:8000`:

### Option 1: Railway (recommended for simplicity)

```bash
cd backend
railway login
railway up
# Railway auto-detects Python, installs deps, starts uvicorn
```

Set your env vars in the Railway dashboard.

### Option 2: Render

1. Push the `backend/` folder to a GitHub repo
2. Connect it to [render.com](https://render.com)
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add env vars in the Render dashboard

### Option 3: Docker (any host)

```bash
# From the project root (one level above backend/)
# Make sure chroma_db/ exists inside backend/ — run ingest.py first

docker build -t mage-chatbot .
docker run -p 8000:8000 --env-file backend/.env mage-chatbot
```

> **Important:** Run `ingest.py` before building the image. The Dockerfile copies `chroma_db/` into the container.

### Option 4: Any VPS (Ubuntu, etc.)

```bash
cd backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

Use `systemd` or `supervisor` to keep it running. Put `nginx` in front for HTTPS.

### After Deploying the Backend

1. Note your backend URL (e.g., `https://mage-chatbot.up.railway.app`)
2. Update `CONFIG.apiEndpoint` in whichever frontend you're using:
   - `test-chatbot.html` → for continued local testing against production backend
   - `Chatbot.astro` → for your live Astro site
3. Update `ALLOWED_ORIGINS` in `backend/.env` to include your frontend domain(s)

### Production Checklist

- [ ] `ALLOWED_ORIGINS` set to your actual domain(s) (not `*`)
- [ ] `CONFIG.apiEndpoint` points to deployed backend URL (HTTPS)
- [ ] Both frontend and backend are on HTTPS
- [ ] `chroma_db/` is populated (run `ingest.py` before deploying)
- [ ] Health check works: `curl https://your-backend/api/health`
- [ ] Full flow tested: open chat → send message → receive response → lead capture

---

## Known Issues & Fixes

### Double Bot Response After Lead Capture ✅ Fixed

**Problem:** After submitting the lead form, the "Thanks! I've noted your details" message was included in the conversation history sent to the LLM. When the user sent their next message, the LLM saw its own "Thanks" message, treated the user's reply as a continuation, and generated a full product info response — resulting in two back-to-back bot messages.

**Root cause:** The "Thanks" message was stored as a regular `assistant` message and sent to the API like any other.

**Fix (applied in both `test-chatbot.html` and `Chatbot.astro`):**

```js
// 1. Tag the thanks message as local-only (not sent to API)
messages.push({
  role: 'assistant',
  content: "Thanks! I've noted your details. How can I help you?",
  local: true    // ← this flag
});

// 2. Filter local messages out of the API payload
body: JSON.stringify({
  messages: messages
    .filter(m => !m.local)    // ← skip local-only messages
    .map(m => ({ role: m.role, content: m.content })),
  sessionId
})
```

The "Thanks" message still renders in the chat UI but never reaches the LLM.

---

## Testing Checklist

### Backend (run these first)

- [ ] `curl http://localhost:8000/api/health` returns `{"status":"ok"}`
- [ ] `curl -X POST http://localhost:8000/api/chat ...` returns a valid response
- [ ] Vector store has data (`chroma_db/` directory is not empty)

### Widget — Both Paths

- [ ] Orange chat bubble appears in bottom-right corner
- [ ] Bubble pulse animation plays on first load
- [ ] Clicking bubble opens panel with smooth animation
- [ ] Clicking X or pressing Escape closes panel
- [ ] Welcome message displays on open
- [ ] Quick reply chips are visible when no messages exist
- [ ] Clicking a chip sends it as a message and chips disappear
- [ ] User message appears in orange bubble (right side)
- [ ] Typing indicator (3 dots) shows while waiting for response
- [ ] Bot response appears in white bubble (left side) with avatar
- [ ] Source link pills are clickable
- [ ] Markdown links `[text](url)` render as clickable links
- [ ] Bold text `**text**` renders correctly
- [ ] Error message shows if backend is stopped
- [ ] Mobile: resize to < 480px, panel fills width, scrolling works
- [ ] Keyboard: Tab cycles through focusable elements in panel
- [ ] Session state: refresh page, reopen chat → messages are preserved

### Lead Capture — Both Paths

- [ ] Lead form appears after N messages (check `triggerAfterMessages`)
- [ ] Input bar is disabled while form is showing
- [ ] Empty or invalid email shows red border, form doesn't submit
- [ ] Valid email: form disappears, "Thanks" message shows
- [ ] After lead capture, next user message gets **one** bot response (not two)
- [ ] Lead form does not appear again (once per session)
- [ ] Backend logs the lead: check terminal output for `[LEAD] ...`

### Astro-Specific (Path B only)

- [ ] Widget renders on every page that includes `<Chatbot />`
- [ ] Navigate to another page → chat state is preserved (View Transitions)
- [ ] Widget loads lazily (check Network tab — JS doesn't block initial render)
- [ ] Cookie consent banner doesn't overlap chat bubble
- [ ] GA4 events fire (check browser console or GA4 Realtime report)
- [ ] HubSpot receives lead data (if configured)
- [ ] Lighthouse Performance score is not degraded by the widget

---

## Cost Breakdown

| Component | Monthly Cost |
|-----------|-------------|
| LLM API (OpenRouter free tier — Llama 3.3 70B) | $0 |
| Embeddings (HuggingFace `all-MiniLM-L6-v2`, runs locally) | $0 |
| Vector store (ChromaDB, self-hosted) | $0 |
| Backend hosting (Railway / Render free tier) | $0 |
| **Total** | **$0/month** |

For higher traffic (>100 conversations/day), consider upgrading to paid LLM tiers on OpenRouter ($5–100/month depending on model and volume).

---

## Troubleshooting

### "Sorry, I'm having trouble connecting"

This means the frontend can't reach the backend.

1. **Is the backend running?**
   ```bash
   curl http://localhost:8000/api/health
   ```
2. **Does the endpoint match?** Check `CONFIG.apiEndpoint` in your frontend file matches the backend URL exactly
3. **CORS error?** Open browser DevTools → Console. If you see `Access-Control-Allow-Origin` errors, update `ALLOWED_ORIGINS` in `backend/.env`

### Empty responses / "I don't have that information"

1. **Is the vector store populated?**
   ```bash
   ls -la backend/chroma_db/
   ```
   If empty or missing, run `python ingest.py --pdf-dir ./documents`
2. **Are your PDFs readable?** Try opening them — some scanned PDFs won't extract text
3. **Add more knowledge:** The more documents you ingest, the better the responses

### ChromaDB errors on startup

```bash
# Delete and re-create the vector store
rm -rf chroma_db/
python ingest.py --pdf-dir ./documents --clear
```

### OpenRouter API errors (429, 401, etc.)

- **401:** Your API key is wrong or missing. Check `backend/.env`
- **429:** Rate limited. The free tier has limits — wait a moment and retry
- **Try another model:** Edit `.env`:
  ```env
  LLM_MODEL=google/gemma-2-9b-it:free
  ```

### Lead form not appearing

1. Check `CONFIG.leadCapture.enabled` is `true`
2. Check `CONFIG.leadCapture.triggerAfterMessages` — you need to send that many messages first
3. Clear sessionStorage (the form only shows once per session):
   - Open DevTools → Application → Session Storage → delete `mage_chat_state`

### Chat state is stale / weird after code changes

Clear the session:
- DevTools → Application → Session Storage → delete `mage_chat_state`
- Or open an incognito window

---

## License

This project is proprietary to Mage Data. All rights reserved.
