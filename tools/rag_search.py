"""
RAG search tool — search a local ChromaDB knowledge base.
Documents are indexed from the `knowledge/` directory.
"""

import os
import logging

from agent.tools import BaseTool

logger = logging.getLogger("tools.rag_search")

# Lazy-initialized ChromaDB collection
_collection = None
_embed_fn = None


def init_rag(knowledge_dir: str, embed_fn) -> None:
    """Initialize the RAG system with a knowledge directory and embedding function."""
    global _collection, _embed_fn
    _embed_fn = embed_fn

    import chromadb
    from chromadb.config import Settings

    client = chromadb.Client(Settings(
        anonymized_telemetry=False,
        is_persistent=True,
        persist_directory=os.path.join(knowledge_dir, "..", ".chromadb"),
    ))

    try:
        _collection = client.get_collection("knowledge_base")
        logger.info("loaded existing ChromaDB collection (%d docs)", _collection.count())
    except Exception:
        _collection = client.create_collection("knowledge_base")
        logger.info("created new ChromaDB collection")

    # Index any new files
    _index_new_files(knowledge_dir)


def _index_new_files(knowledge_dir: str) -> None:
    """Index text files from knowledge_dir that haven't been indexed yet."""
    if not os.path.isdir(knowledge_dir):
        return

    # Get already-indexed file IDs
    existing = set()
    if _collection.count() > 0:
        results = _collection.get()
        existing = set(results.get("ids", []))

    for fname in os.listdir(knowledge_dir):
        fpath = os.path.join(knowledge_dir, fname)
        if not os.path.isfile(fpath):
            continue
        if fname in existing:
            continue

        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception:
            continue

        if not content.strip():
            continue

        # Split long documents into chunks (simple: paragraph-based)
        chunks = _split_text(content, max_chars=1000)
        for i, chunk in enumerate(chunks):
            chunk_id = f"{fname}_chunk{i}"
            try:
                embedding = _embed_fn([chunk])[0]
                _collection.add(
                    ids=[chunk_id],
                    embeddings=[embedding],
                    documents=[chunk],
                    metadatas=[{"source": fname, "chunk": i}],
                )
            except Exception as e:
                logger.warning("failed to index %s: %s", chunk_id, e)

    logger.info("RAG index: %d documents total", _collection.count())


def _split_text(text: str, max_chars: int = 1000) -> list[str]:
    """Split text into chunks by paragraphs, respecting max_chars."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) < max_chars:
            current = (current + "\n\n" + para).strip()
        else:
            if current:
                chunks.append(current)
            current = para
    if current:
        chunks.append(current)
    return chunks or [text]


class RAGSearchTool(BaseTool):
    name = "rag_search"
    description = "Search the local knowledge base for relevant documents. Use this when the user asks about information that might be in the local document collection."
    parameters = {
        "query": {
            "type": "string",
            "description": "The search query to find relevant documents.",
        },
        "top_k": {
            "type": "integer",
            "description": "Number of results to return (default 3, max 5).",
        },
    }

    def execute(self, query: str, top_k: int = 3) -> str:
        global _collection, _embed_fn

        if _collection is None or _embed_fn is None:
            return "RAG is not initialized. Place documents in the `knowledge/` directory and restart."

        top_k = min(top_k, 5)
        try:
            query_embedding = _embed_fn([query])[0]
            results = _collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
            )
        except Exception as e:
            return f"RAG search failed: {e}"

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        if not documents:
            return f"No relevant documents found for '{query}'."

        lines = []
        for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances), 1):
            source = meta.get("source", "unknown") if meta else "unknown"
            lines.append(f"### Result {i} (source: {source}, relevance: {1-dist:.2f})\n{doc[:800]}")
        return "\n\n---\n\n".join(lines)
