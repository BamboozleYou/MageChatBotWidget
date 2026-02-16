# Mage Data AI Chatbot — Complete Project

A self-hosted RAG chatbot for magedata.ai. Replaces the placeholder `Chatbot.astro` with a real AI-powered assistant backed by a FastAPI + ChromaDB + OpenRouter backend.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│  Astro Frontend (GitHub Pages)                       │
│                                                      │
│  Chatbot.astro  ──→  POST /api/chat ──→  Backend    │
│  (vanilla JS)        POST /api/lead                  │
└──────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────┐
│  FastAPI Backend (VPS / Serverless)                   │
│                                                      │
│  main.py  ─→  rag.py  ─→  ChromaDB (vectors)        │
│                        ─→  OpenRouter LLM (free)     │
│                        ─→  Google Embeddings         │
│               ─→  HubSpot (lead webhook)             │
└──────────────────────────────────────────────────────┘
```

## Project Structure

```
mage-chatbot-project/
├── frontend/                          # Drop into your Astro site
│   └── src/
│       ├── components/interactive/
│       │   └── Chatbot.astro          # ★ Main widget — replaces existing
│       ├── utils/
│       │   └── chatbot.ts             # ★ Configuration file
│       └── styles/
│           └── chatbot.css            # Extra animations (optional)
│
├── backend/                           # Python API server
│   ├── main.py                        # FastAPI endpoints
│   ├── rag.py                         # RAG pipeline (retriever + LLM)
│   ├── ingest.py                      # Knowledge base ingestion script
│   ├── requirements.txt               # Python dependencies
│   └── .env.example                   # Environment variable template
│
└── README.md                          # This file
```

---

## Setup — Backend

### 1. Install dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your API keys:
#   GOOGLE_API_KEY     — for embeddings (gemini-embedding-001)
#   OPENROUTER_API_KEY — for LLM (free tier, no credit card)
```

Get your free keys:
- **Google AI**: https://aistudio.google.com/apikey
- **OpenRouter**: https://openrouter.ai/keys (no credit card needed)

### 3. Ingest your knowledge base

Place your PDF documents in a `documents/` folder, then run:

```bash
# With PDFs + llms.txt
python ingest.py --pdf-dir ./documents --llms-txt ./llms.txt

# With PDFs only
python ingest.py --pdf-dir ./documents
```

This creates the `chroma_db/` directory with all vectorized content.

### 4. Start the server

```bash
uvicorn main:app --reload --port 8000
```

Test it:
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"What is Mage Data?"}]}'
```

---

## Setup — Frontend

### 1. Copy files into your Astro project

```bash
# From the project root:
cp frontend/src/components/interactive/Chatbot.astro \
   /path/to/your-site/src/components/interactive/Chatbot.astro

cp frontend/src/utils/chatbot.ts \
   /path/to/your-site/src/utils/chatbot.ts

# Optional: extra animations
cp frontend/src/styles/chatbot.css \
   /path/to/your-site/src/styles/chatbot.css
```

### 2. Update the API endpoint

In `Chatbot.astro`, find the `CONFIG` object and update `apiEndpoint`:

```js
const CONFIG = {
  apiEndpoint: 'https://your-backend-domain.com/api/chat',
  // ...
};
```

Also update `chatbot.ts` to match.

### 3. Verify BaseLayout.astro

The widget should already be included. Confirm this line exists:

```astro
<!-- In src/layouts/BaseLayout.astro, after Footer -->
<Chatbot />
```

### 4. HubSpot (optional)

If you want lead capture to push to HubSpot, fill in the IDs in `CONFIG.leadCapture`:

```js
leadCapture: {
  enabled: true,
  triggerAfterMessages: 3,
  hubspotPortalId: 'YOUR_PORTAL_ID',
  hubspotFormId: 'YOUR_FORM_ID',
},
```

---

## Features Implemented

### Frontend Widget (Chatbot.astro)
- [x] Floating toggle bubble (fixed position, orange, pulse animation)
- [x] Chat panel with header, messages, input bar
- [x] Bot messages (white bubbles, left) + User messages (orange bubbles, right)
- [x] Bot avatar icon on messages
- [x] Typing indicator (3-dot bounce animation)
- [x] Quick reply chips ("Request a demo", "Learn about products", "Talk to sales")
- [x] Source link pills on bot responses
- [x] Markdown link rendering in bot messages
- [x] Lead capture inline form after 3 messages
- [x] HubSpot webhook submission
- [x] Cookie consent coexistence (MutationObserver shifts bubble up)
- [x] Deferred loading (5s idle or first interaction)
- [x] View Transition persistence (transition:persist + sessionStorage)
- [x] Accessibility: role="dialog", aria-labels, focus trap, Escape key, aria-live
- [x] Mobile responsive (full-width panel, 60vh max height)
- [x] GA4 analytics events (with consent check)
- [x] Error handling with fallback message
- [x] Panel open/close animations

### Backend API
- [x] POST /api/chat — RAG pipeline with response + sources
- [x] POST /api/lead — Lead capture with HubSpot + local logging
- [x] GET /api/health — Health check endpoint
- [x] Ensemble retriever (60% semantic + 40% BM25)
- [x] System prompt from Section 4c (exact text)
- [x] Conversation history support (last 6 turns)
- [x] Source URL extraction from document metadata

### Knowledge Base Ingestion
- [x] PDF loader with metadata enrichment
- [x] llms.txt sitemap parser
- [x] Manual knowledge entries (deployment, databases, pricing, compliance)
- [x] Recursive text splitting (1500 chars / 200 overlap)
- [x] Rate-limit-safe batched ingestion
- [x] Retry logic for failed batches

### Analytics Events (Section 8)
| Event | Trigger |
|---|---|
| `chatbot_opened` | User clicks chat bubble |
| `chatbot_message_sent` | User sends a message |
| `chatbot_quick_reply` | User clicks a quick reply chip |
| `chatbot_lead_capture` | User submits email |
| `chatbot_link_clicked` | User clicks a source link |

All events respect `localStorage.getItem('magedata_consent')`.

---

## Backend Deployment Options

| Option | How |
|---|---|
| **Railway** | `railway up` (free tier, auto-detects Python) |
| **Render** | Connect GitHub repo, auto-deploy (free tier available) |
| **Fly.io** | `fly launch` (free tier, 3 shared VMs) |
| **VPS** | Any Ubuntu server: `uvicorn main:app --host 0.0.0.0 --port 8000` |
| **Docker** | See Dockerfile below |

### Quick Docker deployment

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY backend/ .
RUN pip install --no-cache-dir -r requirements.txt
COPY chroma_db/ ./chroma_db/
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t mage-chatbot .
docker run -p 8000:8000 --env-file backend/.env mage-chatbot
```

---

## Testing Checklist (Section 11)

- [ ] Chat bubble renders on all pages after 5s or first interaction
- [ ] Chat bubble does not overlap cookie consent banner
- [ ] Chat panel opens/closes with animation, accessible via keyboard
- [ ] Messages round-trip to the backend API and display responses
- [ ] Bot responses include clickable links to product pages
- [ ] Typing indicator shows while waiting for API response
- [ ] Quick reply chips work and disappear after first use
- [ ] Lead capture form appears after 3 messages, submits to HubSpot
- [ ] GA4 events fire correctly (only when consent granted)
- [ ] Mobile: panel fits viewport, no overflow, scroll works
- [ ] View Transitions: chat state preserved when navigating pages
- [ ] Error handling: graceful message if API is down
- [ ] Lighthouse Performance score not degraded (deferred loading)

---

## Cost Estimate (Section 12)

| Component | Monthly Cost |
|---|---|
| LLM API (OpenRouter free tier) | $0 |
| Embeddings (Google free tier) | $0 |
| Vector store (ChromaDB self-hosted) | $0 |
| Backend hosting (Railway/Render free) | $0 |
| **Total (free tier)** | **$0/mo** |

For higher traffic, upgrade to paid LLM tiers ($20-100/mo).
