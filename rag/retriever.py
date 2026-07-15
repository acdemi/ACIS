"""Hybrid RAG retriever with optional Qdrant backend.

The public entrypoint is ``retrieve(query, crop='', top_k=3)``. It prefers
Qdrant when configured and available, then falls back to the in-memory disease
search in ``rag.knowledge_base`` so the MVP remains runnable offline.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import os
import re
from typing import Any
from uuid import uuid5, NAMESPACE_URL

from rag.knowledge_base import CROP_MAP, DISEASE_DB, search_disease

DEFAULT_COLLECTION = "agri_knowledge_v1"
DEFAULT_QDRANT_URL = "http://localhost:6333"
VECTOR_SIZE = 256

RetrievalHit = dict[str, Any]


def _normalize_crop(crop: str = "") -> str:
    if not crop:
        return ""
    return CROP_MAP.get(crop.lower(), crop)


def _qdrant_available() -> bool:
    try:
        import qdrant_client  # noqa: F401
    except Exception:
        return False
    return True


_QDRANT_AVAILABLE = _qdrant_available()


def _get_backend() -> str:
    backend = os.environ.get("AGRI_AI_RAG_BACKEND", "auto").strip().lower()
    if backend not in {"auto", "qdrant", "memory"}:
        return "auto"
    return backend


def _get_top_k(top_k: int | None = None) -> int:
    if top_k is not None:
        return max(1, int(top_k))
    try:
        return max(1, int(os.environ.get("AGRI_AI_RAG_TOP_K", "3")))
    except ValueError:
        return 3


def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z0-9_]+", text.lower())
    tokens.extend(char for char in text if "\u4e00" <= char <= "\u9fff")
    phrases = [
        "黄斑",
        "霉层",
        "叶背",
        "叶片背面",
        "灰色",
        "灰黑色",
        "绒状",
        "轮纹",
        "同心",
        "褐色",
        "多角",
        "结露",
        "湿度",
        "通风",
        "番茄",
        "黄瓜",
    ]
    tokens.extend(phrase for phrase in phrases if phrase in text)
    return tokens


def embed_text(text: str) -> list[float]:
    """Deterministic local hash embedding for MVP retrieval.

    This avoids external model downloads and keeps Qdrant optional. Replace this
    function later with a real embedding model while keeping the same vector size
    contract per collection version.
    """
    vector = [0.0] * VECTOR_SIZE
    for token in _tokenize(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % VECTOR_SIZE
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign

    norm = math.sqrt(sum(value * value for value in vector))
    if not norm:
        return vector
    return [round(value / norm, 6) for value in vector]


def _knowledge_documents() -> list[dict[str, Any]]:
    documents = []
    for disease_id, disease in DISEASE_DB.items():
        text_parts = [
            disease["name"],
            disease["crop"],
            disease.get("pathogen", ""),
            "症状：" + "；".join(disease.get("symptoms", [])),
            "发病条件：" + "；".join(
                f"{key}={value}" for key, value in disease.get("conditions", {}).items()
            ),
            "预防：" + "；".join(disease.get("prevention", [])),
            "处理：" + "；".join(disease.get("treatment", [])),
        ]
        documents.append(
            {
                "id": disease_id,
                "title": disease["name"],
                "crop": disease["crop"],
                "text": "\n".join(part for part in text_parts if part),
                "source": "knowledge_base.disease",
                "metadata": {
                    "disease_id": disease_id,
                    "pathogen": disease.get("pathogen", ""),
                    "symptoms": disease.get("symptoms", []),
                    "conditions": disease.get("conditions", {}),
                    "prevention": disease.get("prevention", []),
                    "treatment": disease.get("treatment", []),
                },
            }
        )
    return documents


def _memory_hits(query: str, crop: str = "", top_k: int | None = None) -> list[RetrievalHit]:
    limit = _get_top_k(top_k)
    hits = []
    for result in search_disease(query, crop)[:limit]:
        disease = result.get("full_info", {})
        text = "\n".join(
            [
                disease.get("name", result.get("name", "")),
                "症状：" + "；".join(disease.get("symptoms", [])),
                "预防：" + "；".join(disease.get("prevention", [])),
                "处理：" + "；".join(disease.get("treatment", [])),
            ]
        )
        hits.append(
            {
                "id": result.get("disease_id", result.get("name", "")),
                "title": result.get("name", "未知病害"),
                "crop": result.get("crop", ""),
                "text": text,
                "score": float(result.get("match_score", 0.0)),
                "source": "memory",
                "metadata": {
                    "backend": "memory",
                    "matched_symptoms": result.get("matched_symptoms", []),
                    "match_score": result.get("match_score", 0.0),
                    "full_info": disease,
                },
            }
        )
    return hits


def _qdrant_client():
    from qdrant_client import QdrantClient

    return QdrantClient(url=os.environ.get("QDRANT_URL", DEFAULT_QDRANT_URL), timeout=3.0)


def _collection_name() -> str:
    return os.environ.get("QDRANT_COLLECTION", DEFAULT_COLLECTION)


def ensure_collection() -> None:
    from qdrant_client.models import Distance, VectorParams

    client = _qdrant_client()
    collection = _collection_name()
    collections = client.get_collections().collections
    if any(item.name == collection for item in collections):
        return
    client.create_collection(
        collection_name=collection,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )


def index_builtin_knowledge() -> int:
    from qdrant_client.models import PointStruct

    ensure_collection()
    client = _qdrant_client()
    points = []
    for document in _knowledge_documents():
        point_id = str(uuid5(NAMESPACE_URL, f"agri-ai:{document['id']}"))
        points.append(
            PointStruct(
                id=point_id,
                vector=embed_text(document["text"]),
                payload=document,
            )
        )
    client.upsert(collection_name=_collection_name(), points=points)
    return len(points)


def _qdrant_hits(query: str, crop: str = "", top_k: int | None = None) -> list[RetrievalHit]:
    client = _qdrant_client()
    crop_zh = _normalize_crop(crop)
    query_filter = None
    if crop_zh:
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        query_filter = Filter(
            must=[FieldCondition(key="crop", match=MatchValue(value=crop_zh))]
        )

    search_result = client.search(
        collection_name=_collection_name(),
        query_vector=embed_text(query),
        query_filter=query_filter,
        limit=_get_top_k(top_k),
        with_payload=True,
    )

    hits = []
    for point in search_result:
        payload = dict(point.payload or {})
        metadata = dict(payload.get("metadata") or {})
        metadata["backend"] = "qdrant"
        hits.append(
            {
                "id": str(payload.get("id") or point.id),
                "title": str(payload.get("title") or "未知知识片段"),
                "crop": str(payload.get("crop") or ""),
                "text": str(payload.get("text") or ""),
                "score": float(point.score),
                "source": str(payload.get("source") or "qdrant"),
                "metadata": metadata,
            }
        )
    return hits


def retrieve(query: str, crop: str = "", top_k: int | None = None) -> list[RetrievalHit]:
    """Retrieve agriculture knowledge hits from Qdrant or memory fallback."""
    backend = _get_backend()
    if backend == "memory":
        return _memory_hits(query, crop, top_k)

    if backend in {"auto", "qdrant"} and (backend == "qdrant" or _QDRANT_AVAILABLE):
        try:
            hits = _qdrant_hits(query, crop, top_k)
            if hits or backend == "qdrant":
                return hits
        except Exception:
            if backend == "qdrant":
                raise

    return _memory_hits(query, crop, top_k)


def retrieve_with_backend(query: str, crop: str = "", top_k: int | None = None) -> dict[str, Any]:
    """Retrieve hits and report which backend produced them."""
    backend = _get_backend()
    if backend == "memory":
        return {"backend": "memory", "matches": _memory_hits(query, crop, top_k)}

    if backend in {"auto", "qdrant"} and (backend == "qdrant" or _QDRANT_AVAILABLE):
        try:
            hits = _qdrant_hits(query, crop, top_k)
            if hits or backend == "qdrant":
                return {"backend": "qdrant", "matches": hits}
            return {
                "backend": "fallback",
                "matches": _memory_hits(query, crop, top_k),
                "error": "Qdrant returned no hits",
            }
        except Exception as exc:
            if backend == "qdrant":
                raise
            return {
                "backend": "fallback",
                "matches": _memory_hits(query, crop, top_k),
                "error": str(exc),
            }

    return {"backend": "memory", "matches": _memory_hits(query, crop, top_k)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Agri AI hybrid RAG retriever")
    parser.add_argument("--index", action="store_true", help="index built-in knowledge into Qdrant")
    parser.add_argument("--query", help="query text for smoke retrieval")
    parser.add_argument("--crop", default="", help="optional crop filter, e.g. tomato/番茄")
    parser.add_argument("--top-k", type=int, default=None, help="number of hits to return")
    args = parser.parse_args()

    if args.index:
        count = index_builtin_knowledge()
        print(f"indexed {count} documents into {_collection_name()}")

    if args.query:
        result = retrieve_with_backend(args.query, args.crop, args.top_k)
        print(f"backend: {result['backend']}")
        if result.get("error"):
            print(f"fallback_reason: {result['error']}")
        for hit in result["matches"]:
            print(f"- {hit['score']:.3f} | {hit['title']} | {hit['crop']} | {hit['source']}")

    if not args.index and not args.query:
        parser.print_help()


if __name__ == "__main__":
    main()
