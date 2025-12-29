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

from database.models import NGOModel


_chroma_client: Optional[Client] = None
_emb_model: Optional[SentenceTransformer] = None

# Single collection shared for NGO embeddings (and later issues/chatbot docs)
_NGO_COLLECTION_NAME = "ngo_embeddings"


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
    initialize_vector_store()
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
        metadatas.append(
            {
                "ngo_id": ngo_id,
                "username": ngo.get("Username", ""),
                "categories": ngo.get("Categories", []),
                "city": ngo.get("Address", {}).get("city", ""),
                "state": ngo.get("Address", {}).get("state", ""),
                "pincode": ngo.get("Address", {}).get("pincode", ""),
            }
        )

    embeddings = emb_model.encode(texts, show_progress_bar=True).tolist()

    # Clear existing entries for a clean rebuild
    collection.delete(where={})

    collection.add(
        ids=ids,
        embeddings=embeddings,
        metadatas=metadatas,
        documents=texts,
    )

    # Persist to disk
    _get_chroma_client().persist()


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
        metadatas=[
            {
                "ngo_id": ngo_id,
                "username": ngo.get("Username", ""),
                "categories": ngo.get("Categories", []),
                "city": ngo.get("Address", {}).get("city", ""),
                "state": ngo.get("Address", {}).get("state", ""),
                "pincode": ngo.get("Address", {}).get("pincode", ""),
            }
        ],
        documents=[text],
    )

    _get_chroma_client().persist()


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
        _get_chroma_client().persist()
        return

    text = _build_ngo_text(ngo)
    embedding = emb_model.encode(text).tolist()

    # Delete old entry then re-add
    collection.delete(ids=[ngo_id])
    collection.add(
        ids=[ngo_id],
        embeddings=[embedding],
        metadatas=[
            {
                "ngo_id": ngo_id,
                "username": ngo.get("Username", ""),
                "categories": ngo.get("Categories", []),
                "city": ngo.get("Address", {}).get("city", ""),
                "state": ngo.get("Address", {}).get("state", ""),
                "pincode": ngo.get("Address", {}).get("pincode", ""),
            }
        ],
        documents=[text],
    )

    _get_chroma_client().persist()


def remove_ngo_from_vector_db(ngo_id: str) -> None:
    """
    Remove NGO from vector DB (if NGO is deleted/deactivated).
    """
    if not ngo_id:
        return

    initialize_vector_store()
    collection = _get_ngo_collection()

    collection.delete(ids=[ngo_id])
    _get_chroma_client().persist()


def search_vector_db(query_text: str, top_k: int = 5, where: Optional[Dict[str, Any]] = None):
    """
    Generic search helper for the shared vector DB. This will be reused
    by NGO matcher and chatbot.
    """
    if not query_text:
        return []

    initialize_vector_store()
    collection = _get_ngo_collection()
    emb_model = _get_embedding_model()

    query_embedding = emb_model.encode([query_text]).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        where=where or {},
    )

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

    return hits


