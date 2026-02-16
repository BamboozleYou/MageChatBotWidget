"""
Knowledge Base Ingestion — Mage Data Chatbot

Sources (Section 5a):
  1. PDF documents from a specified directory
  2. Structured sitemap from public/llms.txt
  3. Manual knowledge entries (deployment, databases, pricing)

Chunking (Section 5b):
  - 300-500 tokens per chunk (~1200-2000 chars) with 50-token overlap (~200 chars)
  - Split by section headings (H2/H3 boundaries)
  - Preserve metadata: page title, URL, section heading

Usage:
  python ingest.py --pdf-dir ./documents --llms-txt ./llms.txt
  python ingest.py --pdf-dir ./documents --clear
"""

import os
import re
import argparse
import time
import shutil
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

load_dotenv()

# ── Config (Section 5b) ─────────────────────────────────────────
CHROMA_DIR = os.getenv("CHROMA_DIR", "chroma_db")
CHUNK_SIZE = 1500           # ~375 tokens (within 300-500 token range)
CHUNK_OVERLAP = 200         # ~50 tokens
BATCH_SIZE = 10             # embeddings per API call
BATCH_DELAY_SECONDS = 10    # rate-limit protection for free-tier APIs


def get_embeddings():
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


# ── 1. PDF Loader (Section 5a-2) ────────────────────────────────
def load_pdfs(pdf_dir: str) -> list[Document]:
    docs = []
    if not os.path.isdir(pdf_dir):
        print(f"  [SKIP] PDF directory not found: {pdf_dir}")
        return docs

    pdf_files = sorted(f for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf"))
    print(f"  Found {len(pdf_files)} PDF files")

    for filename in pdf_files:
        filepath = os.path.join(pdf_dir, filename)
        try:
            loader = PyPDFLoader(filepath)
            pages = loader.load()

            # Derive title from filename
            title = re.sub(r"[-_]", " ", filename.replace(".pdf", "")).strip().title()

            # Derive a product URL slug
            slug = filename.replace(".pdf", "").lower().replace(" ", "-").replace("_", "-")
            url = f"/products/{slug}.html"

            for page in pages:
                page.metadata["title"] = title
                page.metadata["url"] = url
                page.metadata["source_type"] = "pdf"

            docs.extend(pages)
            print(f"    OK: {filename} ({len(pages)} pages)")
        except Exception as e:
            print(f"    ERROR: {filename} — {e}")

    return docs


# ── 2. llms.txt Loader (Section 5a-1) ──────────────────────────
def load_llms_txt(filepath: str) -> list[Document]:
    docs = []
    if not os.path.isfile(filepath):
        print(f"  [SKIP] llms.txt not found: {filepath}")
        return docs

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Split by markdown H2/H3 headings or horizontal rules
    sections = re.split(r"\n(?=## |\n---+\n)", content)

    for section in sections:
        section = section.strip()
        if not section or len(section) < 50:
            continue

        lines = section.split("\n")
        title = lines[0].strip("# ").strip()
        url = ""

        # Try to extract URL from the section
        for line in lines[:10]:
            line_stripped = line.strip()
            if line_stripped.startswith("URL:") or line_stripped.startswith("url:"):
                url = line_stripped.split(":", 1)[1].strip()
                break
            # Match lines that look like paths: /something
            if re.match(r"^/[a-z]", line_stripped):
                url = line_stripped
                break

        doc = Document(
            page_content=section,
            metadata={
                "title": title,
                "url": url,
                "source": filepath,
                "source_type": "sitemap",
            },
        )
        docs.append(doc)

    print(f"  Parsed {len(docs)} sections from llms.txt")
    return docs


# ── 3. Manual Knowledge Entries (Section 5a-3) ──────────────────
def get_manual_entries() -> list[Document]:
    entries = [
        {
            "content": """Mage Data Deployment Options:
Mage Data supports flexible deployment models to fit any enterprise architecture:
- On-Premises: Deploy within your own data center for maximum control and security. Supports all major operating systems and database platforms.
- Cloud: Available on AWS, Azure, and Google Cloud Platform. Fully managed cloud deployment with auto-scaling capabilities.
- Hybrid: Combine on-premises and cloud deployments for organizations with mixed infrastructure requirements.
All deployment options include full platform capabilities with no feature limitations.""",
            "title": "Deployment Options",
            "url": "/platform/deployment.html",
        },
        {
            "content": """Supported Databases and Data Sources:
Mage Data supports 50+ data sources including:
- Relational Databases: Oracle, SQL Server, PostgreSQL, MySQL, IBM DB2, SAP HANA, MariaDB, Amazon Aurora, Azure SQL
- Cloud Data Warehouses: Snowflake, Google BigQuery, Amazon Redshift, Azure Synapse
- NoSQL: MongoDB, Cassandra, DynamoDB, Couchbase
- File Systems: SMB, NFS, FTP, SFTP, Amazon S3, Azure Blob Storage, Google Cloud Storage
- SaaS Platforms: Salesforce, ServiceNow, Workday
- Big Data: Hadoop, Spark, Databricks, Apache Hive
- Other: SharePoint, OneDrive, mainframes, flat files (CSV, JSON, XML, Parquet)""",
            "title": "Supported Databases",
            "url": "/platform/supported-databases.html",
        },
        {
            "content": """Free Trial and Demo:
Mage Data offers personalized product demonstrations for enterprises interested in evaluating the platform. To request a demo or discuss your data security requirements, visit the Contact page at /contact.html or email info@magedata.ai.

For enterprise pricing, Mage Data provides custom quotes based on your specific data volume, number of data sources, and required capabilities. Contact the sales team for a tailored proposal.

Mage Data does not publish standard pricing publicly — all pricing is custom enterprise pricing. Please contact info@magedata.ai or visit /contact.html to get a quote.""",
            "title": "Demo and Pricing",
            "url": "/contact.html",
        },
        {
            "content": """Compliance and Regulations:
Mage Data helps organizations automate compliance with major data protection regulations including GDPR, HIPAA, PCI-DSS, SOC 2, CCPA, and the EU AI Act.

Important: Mage Data provides tools and automation to help organizations meet compliance requirements, but this is not legal advice. Organizations should consult with legal professionals for specific compliance guidance.

Mage Data's platform provides automated data discovery, classification, masking, and monitoring capabilities that support compliance workflows across all major regulatory frameworks.""",
            "title": "Compliance and Regulations",
            "url": "/solutions/compliance.html",
        },
    ]

    docs = []
    for entry in entries:
        docs.append(
            Document(
                page_content=entry["content"],
                metadata={
                    "title": entry["title"],
                    "url": entry["url"],
                    "source": "manual_entry",
                    "source_type": "manual",
                },
            )
        )
    print(f"  Added {len(docs)} manual knowledge entries")
    return docs


# ── Chunking (Section 5b) ───────────────────────────────────────
def chunk_documents(docs: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )
    chunks = splitter.split_documents(docs)
    print(f"  Split {len(docs)} documents into {len(chunks)} chunks")
    return chunks


# ── Ingest into ChromaDB with rate-limit batching ────────────────
def ingest_to_chroma(chunks: list[Document], clear: bool = True):
    embeddings = get_embeddings()

    if clear and os.path.isdir(CHROMA_DIR):
        shutil.rmtree(CHROMA_DIR)
        print(f"  Cleared existing ChromaDB at ./{CHROMA_DIR}/")

    total_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"  Ingesting {len(chunks)} chunks in {total_batches} batches...")

    db = None
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1

        try:
            if db is None:
                db = Chroma.from_documents(batch, embeddings, persist_directory=CHROMA_DIR)
            else:
                db.add_documents(batch)

            print(f"    Batch {batch_num}/{total_batches} — {len(batch)} chunks ✓")
        except Exception as e:
            print(f"    Batch {batch_num}/{total_batches} — ERROR: {e}")
            print(f"    Waiting {BATCH_DELAY_SECONDS * 2}s before retrying...")
            time.sleep(BATCH_DELAY_SECONDS * 2)
            try:
                if db is None:
                    db = Chroma.from_documents(batch, embeddings, persist_directory=CHROMA_DIR)
                else:
                    db.add_documents(batch)
                print(f"    Batch {batch_num}/{total_batches} — retry ✓")
            except Exception as e2:
                print(f"    Batch {batch_num}/{total_batches} — FAILED: {e2}")

        if i + BATCH_SIZE < len(chunks):
            time.sleep(BATCH_DELAY_SECONDS)

    print(f"\n  Done! {len(chunks)} chunks stored in ./{CHROMA_DIR}/")
    return db


# ── Main ─────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Ingest knowledge base for Mage Data Chatbot")
    parser.add_argument("--pdf-dir", default="./documents", help="Directory containing PDF files")
    parser.add_argument("--llms-txt", default="./llms.txt", help="Path to llms.txt sitemap file")
    parser.add_argument("--clear", action="store_true", default=True, help="Clear existing DB before ingestion")
    args = parser.parse_args()

    print("=" * 60)
    print("  Mage Data Chatbot — Knowledge Base Ingestion")
    print("=" * 60)

    all_docs = []

    print("\n[1/3] Loading PDFs...")
    all_docs.extend(load_pdfs(args.pdf_dir))

    print("\n[2/3] Loading llms.txt sitemap...")
    all_docs.extend(load_llms_txt(args.llms_txt))

    print("\n[3/3] Adding manual knowledge entries...")
    all_docs.extend(get_manual_entries())

    print(f"\n  Total raw documents: {len(all_docs)}")

    if not all_docs:
        print("\n  ⚠ No documents found. Check your --pdf-dir and --llms-txt paths.")
        return

    print("\n[4/4] Chunking & ingesting...")
    chunks = chunk_documents(all_docs)
    ingest_to_chroma(chunks, clear=args.clear)

    print("\n" + "=" * 60)
    print("  ✓ Ingestion complete!")
    print("  Run the backend: uvicorn main:app --reload --port 8000")
    print("=" * 60)


if __name__ == "__main__":
    main()