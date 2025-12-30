"""
Shared Vector Database using ChromaDB + Sentence Transformers

Implements Step 5 (ISSUE_FLOW_IMPLEMENTATION.md):
- Shared vector DB for NGO matching and chatbot
- Dynamic updates when NGOs are created/updated/deleted
"""

from __future__ import annotations

from typing import List, Dict, Optional, Any

import chromadb
from chromadb import Client
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from bson import ObjectId
import json
import traceback

from database.models import NGOModel


_chroma_client: Optional[Client] = None
_emb_model: Optional[SentenceTransformer] = None

# Single collection shared for NGO embeddings (and later issues/chatbot docs)
_NGO_COLLECTION_NAME = "ngo_embeddings"

# Using print statements for visibility; traceback used for exception details


def _normalize_metadata_value(v):
    """Ensure metadata values are primitive types supported by Chroma.

    Chroma expects metadata values to be str/int/float/bool/None (or SparseVector).
    Convert lists to comma-joined strings and dicts to JSON strings.
    """
    if v is None:
        return None
    if isinstance(v, (str, int, float, bool)):
        return v
    if isinstance(v, list):
        # join simple lists into a comma-separated string
        try:
            return ", ".join([str(x) for x in v])
        except Exception:
            return json.dumps(v, ensure_ascii=False)
    if isinstance(v, dict):
        try:
            # prefer a compact JSON representation
            return json.dumps(v, ensure_ascii=False)
        except Exception:
            return str(v)
    # fallback
    return str(v)


def _normalize_metadata(d: dict) -> dict:
    return {k: _normalize_metadata_value(v) for k, v in (d or {}).items()}


def _get_chroma_client() -> Client:
    """
    Get or initialize a persistent ChromaDB client.

    Note: By default this uses a local persistent store in the current directory.
    You can change the path if needed.
    """
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.Client(
            Settings(
                persist_directory="vector_store",
                anonymized_telemetry=False  
            )
        )
    return _chroma_client


def _get_embedding_model() -> SentenceTransformer:
    """
    Get or lazily load the Sentence Transformers model.
    """
    global _emb_model
    if _emb_model is None:
        # You can change the model name based on your preference
        _emb_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _emb_model


def _build_ngo_text(ngo: Dict[str, Any]) -> str:
    """
    Build a descriptive text representation for an NGO to feed into the
    embedding model. This combines description, categories, and location.
    """
    username = ngo.get("Username", "")
    description = ngo.get("Description", "")
    categories = ngo.get("Categories", [])
    address = ngo.get("Address", {})

    categories_text = ", ".join(categories) if categories else ""
    address_parts = [
        address.get("area", ""),
        address.get("city", ""),
        address.get("dist", ""),
        address.get("state", ""),
        address.get("pincode", ""),
    ]
    address_text = ", ".join([p for p in address_parts if p])

    parts = [
        f"NGO: {username}",
        f"Description: {description}",
        f"Categories: {categories_text}",
        f"Address: {address_text}",
    ]

    return " | ".join([p for p in parts if p])


def initialize_vector_store() -> None:
    """
    Initialize vector database and embeddings model.

    This should be called once at application startup (e.g. in app.py)
    so that:
    - Chroma client is ready
    - Embedding model is loaded
    - NGO collection exists
    """
    client = _get_chroma_client()
    _ = _get_embedding_model()

    # Ensure NGO collection exists
    existing = {c.name for c in client.list_collections()}
    if _NGO_COLLECTION_NAME not in existing:
        client.create_collection(name=_NGO_COLLECTION_NAME)
    existing = {c.name for c in client.list_collections()}
    create_all_ngo_embeddings()
    print(f"[INFO] collections after init: {existing}")


def _get_ngo_collection():
    """
    Helper to get the Chroma collection for NGOs.
    Assumes initialize_vector_store() has been called.
    """
    client = _get_chroma_client()
    return client.get_or_create_collection(name=_NGO_COLLECTION_NAME)


def create_all_ngo_embeddings() -> None:
    """
    Create embeddings for all existing NGOs and store in vector DB.
    Call this:
    - Once after first setting up the vector DB
    - When you need to rebuild the index
    """
    collection = _get_ngo_collection()

    ngos = NGOModel.find_all_active()
    if not ngos:
        return

    emb_model = _get_embedding_model()

    ids: List[str] = []
    texts: List[str] = []
    metadatas: List[Dict[str, Any]] = []

    for ngo in ngos:
        ngo_id = str(ngo["_id"])
        text = _build_ngo_text(ngo)
        ids.append(ngo_id)
        texts.append(text)
        raw_meta = {
            "ngo_id": ngo_id,
            "username": ngo.get("Username", ""),
            "categories": ngo.get("Categories", []),
            "city": ngo.get("Address", {}).get("city", ""),
            "state": ngo.get("Address", {}).get("state", ""),
            "pincode": ngo.get("Address", {}).get("pincode", ""),
        }
        metadatas.append(_normalize_metadata(raw_meta))

    embeddings = emb_model.encode(texts, show_progress_bar=True).tolist()

    # Clear existing entries for a clean rebuild.
    # Avoid passing an empty `where={}` to Chroma (some versions reject it).
    try:
        # Try to get metadata entries and derive stored NGO ids from them.
        existing = collection.get(include=["metadatas", "documents"]) or {}
        metas = existing.get("metadatas", [])
        if metas and isinstance(metas[0], list):
            metas = metas[0]

        existing_ids = []
        if metas:
            for m in metas:
                if isinstance(m, dict) and m.get("ngo_id"):
                    existing_ids.append(m.get("ngo_id"))

        # Fallback: if metadatas didn't include ids, try any returned 'ids' key.
        if not existing_ids:
            existing_ids = existing.get("ids", [])
            if existing_ids and isinstance(existing_ids[0], list):
                existing_ids = existing_ids[0]

        if existing_ids:
            collection.delete(ids=existing_ids)
        else:
            # If we couldn't determine ids, attempt a full delete call.
            try:
                collection.delete()
            except Exception:
                print("[DEBUG] collection.delete() not supported by this Chroma client variant; nothing to delete or different API")
    except Exception as e:
        print("[ERROR] Failed to clear collection before rebuild:", e)
        traceback.print_exc()

    collection.add(
        ids=ids,
        embeddings=embeddings,
        metadatas=metadatas,
        documents=texts,
    )

    # Persist to disk
    client = _get_chroma_client()
    if hasattr(client, "persist"):
        try:
            client.persist()
        except Exception as e:
            print("[ERROR] Chroma client.persist() call failed:", e)
            traceback.print_exc()
    else:
        print("[DEBUG] Chroma client has no persist() method; skipping persist call")


def add_ngo_to_vector_db(ngo_id: str) -> None:
    """
    Add single NGO to vector DB (called when new NGO is registered).
    Must be called automatically after NGO creation.
    """
    if not ngo_id:
        return

    initialize_vector_store()
    collection = _get_ngo_collection()
    emb_model = _get_embedding_model()

    ngo = NGOModel.find_by_id(ngo_id)
    if not ngo or not ngo.get("isActive", True):
        return

    text = _build_ngo_text(ngo)
    embedding = emb_model.encode(text).tolist()

    collection.add(
        ids=[ngo_id],
        embeddings=[embedding],
        metadatas=[_normalize_metadata({
            "ngo_id": ngo_id,
            "username": ngo.get("Username", ""),
            "categories": ngo.get("Categories", []),
            "city": ngo.get("Address", {}).get("city", ""),
            "state": ngo.get("Address", {}).get("state", ""),
            "pincode": ngo.get("Address", {}).get("pincode", ""),
        })],
        documents=[text],
    )

    try:
        client = _get_chroma_client()
        if hasattr(client, "persist"):
            client.persist()
        else:
            print("[DEBUG] Chroma client has no persist() method; skipping persist call")
    except Exception as e:
        print("[ERROR] Chroma client.persist() call failed:", e)
        traceback.print_exc()


def update_ngo_in_vector_db(ngo_id: str) -> None:
    """
    Update NGO embedding in vector DB (if NGO info changes).
    """
    if not ngo_id:
        return

    initialize_vector_store()
    collection = _get_ngo_collection()
    emb_model = _get_embedding_model()

    ngo = NGOModel.find_by_id(ngo_id)

    # If NGO no longer exists or is inactive, remove it
    if not ngo or not ngo.get("isActive", True):
        collection.delete(ids=[ngo_id])
        try:
            client = _get_chroma_client()
            if hasattr(client, "persist"):
                client.persist()
            else:
                print("[DEBUG] Chroma client has no persist() method; skipping persist call")
        except Exception as e:
            print("[ERROR] Chroma client.persist() call failed:", e)
            traceback.print_exc()
        return

    text = _build_ngo_text(ngo)
    embedding = emb_model.encode(text).tolist()

    # Delete old entry then re-add
    collection.delete(ids=[ngo_id])
    collection.add(
        ids=[ngo_id],
        embeddings=[embedding],
        metadatas=[_normalize_metadata({
            "ngo_id": ngo_id,
            "username": ngo.get("Username", ""),
            "categories": ngo.get("Categories", []),
            "city": ngo.get("Address", {}).get("city", ""),
            "state": ngo.get("Address", {}).get("state", ""),
            "pincode": ngo.get("Address", {}).get("pincode", ""),
        })],
        documents=[text],
    )

    try:
        client = _get_chroma_client()
        if hasattr(client, "persist"):
            client.persist()
        else:
            print("[DEBUG] Chroma client has no persist() method; skipping persist call")
    except Exception as e:
        print("[ERROR] Chroma client.persist() call failed:", e)
        traceback.print_exc()


def remove_ngo_from_vector_db(ngo_id: str) -> None:
    """
    Remove NGO from vector DB (if NGO is deleted/deactivated).
    """
    if not ngo_id:
        return

    initialize_vector_store()
    collection = _get_ngo_collection()

    collection.delete(ids=[ngo_id])
    try:
        client = _get_chroma_client()
        if hasattr(client, "persist"):
            client.persist()
        else:
            print("[DEBUG] Chroma client has no persist() method; skipping persist call")
    except Exception as e:
        print("[ERROR] Chroma client.persist() call failed:", e)
        traceback.print_exc()


def search_vector_db(query_text: str, top_k: int = 5, where: Optional[Dict[str, Any]] = None):
    """
    Generic search helper for the shared vector DB. This will be reused
    by NGO matcher and chatbot.
    """
    if not query_text:
        return []

    initialize_vector_store()
    collection = _get_ngo_collection()
    print(f"[DEBUG] collection in search_vector_db: {collection}")
    emb_model = _get_embedding_model()

    query_embedding = emb_model.encode([query_text]).tolist()

    print(f"[DEBUG] search_vector_db called: top_k={top_k} where={where}")

    # Log collection stats to help diagnose empty-result situations.
    try:
        all_entries = collection.get(include=["metadatas", "documents"]) or {}
        metas = all_entries.get("metadatas", [])
        if metas and isinstance(metas[0], list):
            metas = metas[0]

        if metas:
            total = len(metas)
        else:
            docs = all_entries.get("documents", [])
            if docs and isinstance(docs[0], list):
                total = len(docs[0])
            else:
                total = len(docs)

        print(f"[INFO] Chroma collection '{_NGO_COLLECTION_NAME}' total entries={total}")
    except Exception:
        print("[ERROR] Unable to read collection stats before query")
        traceback.print_exc()

    # Only pass a non-empty 'where' to Chroma; an empty dict causes errors
    try:
        if where and isinstance(where, dict) and len(where) > 0:
            results = collection.query(
                query_embeddings=query_embedding,
                n_results=top_k,
                where=where,
            )
        else:
            results = collection.query(
                query_embeddings=query_embedding,
                n_results=top_k,
            )
        print(f"[DEBUG] results from chroma query: {results}")
    except Exception as e:
        print("[ERROR] Chroma query failed:", e)
        traceback.print_exc()
        # Return empty hits on failure to avoid bubbling low-level errors
        return []
    print(f"[DEBUG] search_vector_db raw results: {results}")

    # Normalize output to a list of dicts for easier consumption
    hits = []
    ids = results.get("ids", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]
    documents = results.get("documents", [[]])[0]

    for idx, ngo_id in enumerate(ids):
        hits.append(
            {
                "ngo_id": ngo_id,
                "metadata": metadatas[idx] if idx < len(metadatas) else {},
                "distance": distances[idx] if idx < len(distances) else None,
                "document": documents[idx] if idx < len(documents) else "",
            }
        )
    print(f"[DEBUG] hits: {hits}")
    return hits

