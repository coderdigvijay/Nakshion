# RAG Pipeline Pattern (Nakshion)

## Architecture
1. Knowledge base: markdown files in `backend/knowledge_base/` (14 files, 35K+ words, 539 chunks)
2. Local embeddings: `sentence-transformers/all-MiniLM-L6-v2` (runs on Mac MPS, ~90MB model)
3. Vector store: ChromaDB persisted to `backend/data/chroma_db/`
4. Query enhancement: enrich user query with chart context before retrieval
5. Retrieval: top-5 most similar chunks injected as "REFERENCE KNOWLEDGE" in prompt

## Why local embeddings over API
- Gemini embedding API: 100 req/min limit, 539 chunks = rate limited to death
- Local model: 539 chunks indexed in 5 seconds, zero API calls
- Quality is comparable for retrieval tasks

## Chunking strategy
- Split by markdown headers (## and ###), not arbitrary word counts
- Each chunk is a coherent topic section
- Metadata: source file, section header stored in ChromaDB

## File hash tracking
- MD5 hashes stored in `data/chroma_db/file_hashes.json`
- Only re-indexes when knowledge base files actually change
- Startup skips indexing if no changes detected

## Graceful degradation
- If ChromaDB not installed → chat works without RAG
- If knowledge base empty → chat works without RAG
- If retrieval fails → logged, chat continues with just system prompt
