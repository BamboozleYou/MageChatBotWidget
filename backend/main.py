"""
Mage Data Chatbot — FastAPI Backend
Endpoints:
  POST /api/chat   — RAG chat completion
  POST /api/lead   — Lead capture → HubSpot webhook + local log
  GET  /api/health  — Health check
"""

import os
import uuid
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx
from rag import RAGPipeline

# ── App ──────────────────────────────────────────────────────────
app = FastAPI(title="Mage Data Chatbot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type"],
)

# ── RAG singleton (loaded once at startup) ───────────────────────
rag = RAGPipeline()

# ── Request / Response Schemas (Section 4a) ──────────────────────

class Message(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str

class ChatRequest(BaseModel):
    messages: list[Message]
    sessionId: str = Field(default_factory=lambda: str(uuid.uuid4()))

class Source(BaseModel):
    title: str
    url: str

class ChatResponse(BaseModel):
    reply: str
    sources: list[Source] = []

class LeadRequest(BaseModel):
    email: str
    firstname: str = ""
    company: str = ""
    sessionId: str = ""

class LeadResponse(BaseModel):
    success: bool
    message: str = ""


# ── POST /api/chat ───────────────────────────────────────────────
@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Receives conversation messages, runs RAG pipeline, returns response + sources.
    """
    if not req.messages:
        raise HTTPException(400, "No messages provided")

    user_message = req.messages[-1].content
    history = [{"role": m.role, "content": m.content} for m in req.messages[:-1]]

    try:
        result = await rag.query(user_message, history)
        return ChatResponse(
            reply=result["reply"],
            sources=[Source(**s) for s in result.get("sources", [])],
        )
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] RAG error: {e}")
        return ChatResponse(
            reply="Sorry, I'm having trouble connecting right now. Please try again or contact info@magedata.ai",
            sources=[],
        )


# ── POST /api/lead (Section 7) ──────────────────────────────────
HUBSPOT_PORTAL_ID = os.getenv("HUBSPOT_PORTAL_ID", "")
HUBSPOT_FORM_ID = os.getenv("HUBSPOT_FORM_ID", "")

@app.post("/api/lead", response_model=LeadResponse)
async def capture_lead(req: LeadRequest):
    """
    Captures lead info. Sends to HubSpot if configured, otherwise logs locally.
    """
    if not req.email:
        raise HTTPException(400, "Email is required")

    # HubSpot form submission
    if HUBSPOT_PORTAL_ID and HUBSPOT_FORM_ID:
        url = f"https://api.hsforms.com/submissions/v3/integration/submit/{HUBSPOT_PORTAL_ID}/{HUBSPOT_FORM_ID}"
        payload = {
            "fields": [
                {"name": "email", "value": req.email},
                {"name": "firstname", "value": req.firstname},
                {"name": "company", "value": req.company},
                {"name": "lead_source", "value": "Chatbot"},
            ],
            "context": {
                "pageUri": "https://magedata.ai",
                "pageName": "Chatbot Lead Capture",
            },
            "legalConsentOptions": {
                "consent": {
                    "consentToProcess": True,
                    "text": "I agree to allow Mage Data to store and process my personal data.",
                }
            },
        }
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, timeout=10)
                if resp.status_code in (200, 201):
                    return LeadResponse(success=True, message="Thank you! We'll be in touch.")
                else:
                    print(f"[HUBSPOT] Error {resp.status_code}: {resp.text}")
        except Exception as e:
            print(f"[HUBSPOT] Webhook failed: {e}")

    # Fallback: log locally
    print(f"[LEAD] {datetime.now().isoformat()} | {req.email} | {req.firstname} | {req.company} | session={req.sessionId}")
    return LeadResponse(success=True, message="Thank you! We'll be in touch.")


# ── GET /api/health ──────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}
