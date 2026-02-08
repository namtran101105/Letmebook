from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings

from .monitor import deterministic_embedding

# Keep this in one place so query/upsert always agree
DEFAULT_EMBED_DIM = int(os.getenv("CHROMA_EMBED_DIM", "384"))


def get_chroma_host() -> str:
    return os.getenv("CHROMA_HOST", "chroma")


def get_chroma_port() -> int:
    return int(os.getenv("CHROMA_PORT", "8000"))


def get_collection_name() -> str:
    return os.getenv("CHROMA_COLLECTION", "monvoyage_places_v1")


def get_client() -> chromadb.HttpClient:
    return chromadb.HttpClient(
        host=get_chroma_host(),
        port=get_chroma_port(),
        settings=Settings(allow_reset=False, anonymized_telemetry=False),
    )


def get_collection():
    """
    Centralize collection creation so metadata/dim is consistent everywhere.
    """
    client = get_client()
    return client.get_or_create_collection(
        name=get_collection_name(),
        metadata={"dim": DEFAULT_EMBED_DIM},
    )


def upsert_place_docs(
    place_id: int,
    source_url: str,
    category: Optional[str],
    doc_texts: List[str],
    metadata_extra: Optional[Dict[str, Any]] = None,
) -> int:
    """
    Upsert one or more documents into Chroma for a place.

    Uses a deterministic placeholder embedding so you can test end-to-end without
    downloading a real model yet. Replace later with a real embedding function,
    then recreate the Chroma collection to match the new embedding dimension.

    Returns number of docs upserted.
    """
    col = get_collection()

    metabase: Dict[str, Any] = {"place_id": place_id, "url": source_url}
    if category:
        metabase["category"] = category
    if metadata_extra:
        metabase.update(metadata_extra)

    ids = [f"place:{place_id}:{i}" for i in range(len(doc_texts))]
    embeddings = [deterministic_embedding(t, dim=DEFAULT_EMBED_DIM) for t in doc_texts]
    metadatas = [{**metabase, "chunk": i} for i in range(len(doc_texts))]

    col.upsert(ids=ids, documents=doc_texts, embeddings=embeddings, metadatas=metadatas)
    return len(doc_texts)


def delete_place_docs(place_id: int) -> None:
    col = get_collection()
    col.delete(where={"place_id": place_id})


def query_places(
    query_text: str,
    top_k: int = 5,
    where: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Query Chroma and return a flat list of results with metadata + document text.

    NOTE: With the deterministic placeholder embedding, results won't be
    semantically meaningful, but it validates the full RAG pipeline end-to-end.
    """
    col = get_collection()

    q_emb = deterministic_embedding(query_text, dim=DEFAULT_EMBED_DIM)

    res = col.query(
        query_embeddings=[q_emb],
        n_results=top_k,
        where=where or {},
        include=["metadatas", "documents", "distances"],
    )

    # Chroma returns list-of-lists for a batch; we query 1 item => index [0]
    metadatas = (res.get("metadatas") or [[]])[0]
    documents = (res.get("documents") or [[]])[0]
    distances = (res.get("distances") or [[]])[0]

    out: List[Dict[str, Any]] = []
    for meta, doc, dist in zip(metadatas, documents, distances):
        # meta can be None in some edge cases; guard it
        meta = meta or {}
        out.append(
            {
                "place_id": meta.get("place_id"),
                "url": meta.get("url"),
                "category": meta.get("category"),
                "chunk": meta.get("chunk"),
                "distance": dist,
                "document": doc,
                "metadata": meta,
            }
        )

    return out


def has_docs_for_place(place_id: int) -> bool:
    """
    Utility for production-style pipelines:
    lets you decide whether to re-index (e.g., on first run or if Chroma was wiped).
    """
    col = get_collection()
    res = col.get(where={"place_id": place_id}, include=["ids"], limit=1)
    return bool(res and res.get("ids"))
