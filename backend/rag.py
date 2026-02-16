"""
RAG Pipeline for Mage Data Chatbot.
Vector search (Chroma + BM25 ensemble) → Prompt construction → LLM call → Response.

Uses the EXACT system prompt from Section 4c of the build instructions.
api_key=SecretStr(os.getenv("OPENROUTER_API_KEY", "")),
from pydantic import SecretStr
f the build instructions.
"""

import os
import re
from dotenv import load_dotenv
from pydantic import SecretStr
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_chroma import Chroma
from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

load_dotenv()

# ── System prompt ────────────────────────────────────────────────
SYSTEM_PROMPT = """You are Mage Data's virtual assistant on magedata.ai. RULES:

1. ONLY answer from the provided context. Never invent features or pricing.
2. For pricing: "Contact us for custom enterprise pricing" → link to /contact.html
4. Keep answers concise (2-3 paragraphs max). Link to relevant product pages.
5. Be professional, friendly, and helpful. Use the brand name "Mage Data" (not "we").

HANDLING OFF-TOPIC QUESTIONS:
- If the user asks anything NOT related to data security, data masking, data privacy, cybersecurity, compliance, or Mage Data's products and services (e.g. weather, sports, general knowledge, personal questions, jokes), do NOT answer the question. Instead, politely redirect them:
  "That's outside my area of expertise! I'm here to help you with Mage Data's data security solutions — things like data masking, sensitive data discovery, classification, and compliance. What would you like to know about?"
- NEVER answer off-topic questions, even partially. Always guide the user back to Mage Data.

HANDLING IN-SCOPE BUT UNDOCUMENTED QUESTIONS:
- If the user asks about something related to data security or Mage Data's domain, but the answer is NOT in the provided context, ONLY THEN say: "That's a great question about [topic]. For detailed information on this, I'd recommend reaching out to our team at info@magedata.ai or visiting our [Contact page](/contact.html) — they'll be able to give you the specifics."
- Do NOT redirect to email for off-topic questions. Only redirect for relevant questions you cannot answer from context.

If the user greets you or makes small talk, respond warmly and briefly, then guide them to ask about Mage Data's products and capabilities."""


class RAGPipeline:
    """
    Self-contained RAG pipeline. Initializes once at server startup.
    """

    def __init__(self):
        self.db = self._init_vectorstore()
        self.llm = self._init_llm()
        self.retriever = self._init_retriever()

    # ── Vector store ─────────────────────────────────────────────
    def _init_vectorstore(self) -> Chroma:
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        chroma_dir = os.getenv("CHROMA_DIR", "chroma_db")
        return Chroma(persist_directory=chroma_dir, embedding_function=embeddings)

    # ── LLM (OpenRouter free tier) ───────────────────────────────
    def _init_llm(self) -> ChatOpenAI:
        return ChatOpenAI(
            model=os.getenv("LLM_MODEL", "meta-llama/llama-3.3-70b-instruct:free"),
            api_key=SecretStr(os.getenv("OPENROUTER_API_KEY", "")),
            base_url="https://openrouter.ai/api/v1",
            temperature=0.1,
            max_retries=2,
            timeout=30,
        )

    # ── Ensemble retriever (Section 4b — semantic + keyword) ─────
    def _init_retriever(self):
        semantic = self.db.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 5},
        )

        # Build BM25 index from all stored chunks
        all_data = self.db.get(include=["documents", "metadatas"])
        if not all_data["documents"]:
            print("[RAG] Warning: ChromaDB is empty. Using semantic-only retriever.")
            return semantic

        docs = [
            Document(page_content=text, metadata=meta)
            for text, meta in zip(all_data["documents"], all_data["metadatas"])
        ]
        bm25 = BM25Retriever.from_documents(docs)
        bm25.k = 5

        print(f"[RAG] Ensemble retriever initialized with {len(docs)} chunks.")
        return EnsembleRetriever(
            retrievers=[semantic, bm25],
            weights=[0.6, 0.4],
        )

    # ── Extract source links from retrieved docs ─────────────────
    def _extract_sources(self, docs: list[Document]) -> list[dict]:
        seen = set()
        sources = []

        for doc in docs:
            title = doc.metadata.get("title", "")
            url = doc.metadata.get("url", "")
            source_file = doc.metadata.get("source", "")

            # Derive title from filename if missing
            if not title and source_file:
                title = os.path.basename(source_file)
                title = re.sub(r"[-_]", " ", title)
                title = re.sub(r"\.(pdf|html|md|txt)$", "", title, flags=re.I)
                title = title.strip().title()

            # Derive URL from source path if missing
            if not url and source_file:
                basename = os.path.basename(source_file)
                name = re.sub(r"\.(pdf|html|md|txt)$", "", basename, flags=re.I)
                slug = name.lower().replace(" ", "-").replace("_", "-")
                url = f"/products/{slug}.html"

            key = url or title
            if key and key not in seen:
                seen.add(key)
                sources.append({"title": title or "Related Page", "url": url or "#"})

        return sources[:5]  # max 5 source links

    # ── Build the LLM message list ───────────────────────────────
    def _build_messages(
        self, query: str, context: str, history: list[dict]
    ) -> list[dict]:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Last 6 turns of history
        for msg in history[-6:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # User message with retrieved context
        user_prompt = f"""Context from Mage Data documentation:
---
{context}
---

User question: {query}"""

        messages.append({"role": "user", "content": user_prompt})
        return messages

    # ── Main query method ────────────────────────────────────────
    async def query(self, user_message: str, history: list[dict] | None = None) -> dict:
        """
        Full RAG pipeline:
          1. Retrieve relevant chunks (ensemble: semantic + BM25)
          2. Build prompt with context + conversation history
          3. Call LLM
          4. Return reply + source links
        """
        history = history or []

        # 1. Retrieve
        docs = self.retriever.invoke(user_message)

        # 2. Build context
        context = "\n\n".join([
            f"[Source: {d.metadata.get('title', d.metadata.get('source', 'Unknown'))}]\n{d.page_content}"
            for d in docs
        ])

        if not context.strip():
            return {
                "reply": "I don't have that information. Please contact info@magedata.ai",
                "sources": [],
            }

        # 3. Call LLM
        messages = self._build_messages(user_message, context, history)
        response = self.llm.invoke(messages)
        reply = response.content

        # 4. Extract sources
        sources = self._extract_sources(docs)

        return {"reply": reply, "sources": sources}
