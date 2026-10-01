"""Nakshion RAG: header chunking with provenance, local bge-small embeddings, glossary/phonetic query planning for
Hindi/Hinglish, one-round-trip pgvector + FTS hybrid retrieval with RRF, versioned zero-downtime indexing.

Retrieved text is reference material only; CHART FACTS always win (enforced in app.llm.builder / validators).
Runbook: docs/rag-runbook.md. Eval: python -m evals.rag.run.
"""

from app.rag.retriever import RagMetrics, RetrievalConfig, RetrievalResult, Retriever, build_retriever
from app.rag.store import MemoryStore, PgVectorStore, RetrievedChunk, SearchSpec

__all__ = ["Retriever", "RetrievalConfig", "RetrievalResult", "RagMetrics", "build_retriever", "MemoryStore",
           "PgVectorStore", "RetrievedChunk", "SearchSpec"]
