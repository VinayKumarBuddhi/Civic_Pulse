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

from database.models import NGOModel, ReportsModel


_chroma_client: Optional[Client] = None
_emb_model: Optional[SentenceTransformer] = None

# Single collection shared for NGO embeddings (and later issues/chatbot docs)
_DOC_COLLECTION_NAME = "documents"
_EMB_MODEL_NAME = "all-MiniLM-L6-v2"

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


def _build_issue_text(report: Dict[str, Any]) -> str:
    """
    Build a descriptive text representation for an issue/report to feed into the
    embedding model. Follows REPORTS_SCHEMA: includes description, categories,
    address/location, status, severity, and reporter username.
    """
    if not report:
        return ""

    description = report.get("Description", "")
    categories = report.get("Categories", []) or []
    username = report.get("Username", "")
    status = report.get("Status") or report.get("status") or ""
    severity = report.get("severityScore", 0.0) or 0.0

    # Address formatting
    address = report.get("Address") or {}
    address_parts = [
        address.get("area", ""),
        address.get("city", ""),
        address.get("district", "") or address.get("dist", ""),
        address.get("state", ""),
        address.get("pincode", ""),
    ]
    address_text = ", ".join([p for p in address_parts if p])

    # Location lat/long
    loc = report.get("Location") or {}
    loc_text = ""
    lat = loc.get("latitude")
    lon = loc.get("longitude")
    if lat is not None and lon is not None:
        try:
            loc_text = f"Lat: {float(lat):.6f}, Lon: {float(lon):.6f}"
        except Exception:
            loc_text = f"Location: {lat},{lon}"

    categories_text = ", ".join(categories) if categories else ""

    parts = [
        f"Issue: {description}" if description else "",
        f"Categories: {categories_text}" if categories_text else "",
        f"Reported by: {username}" if username else "",
        f"Address: {address_text}" if address_text else "",
        loc_text,
        f"Status: {status}" if status else "",
        f"Severity: {severity}/10" if severity else "",
    ]

    # Filter empty parts and join
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

    # Ensure documents collection exists
    existing = {c.name for c in client.list_collections()}
    if _DOC_COLLECTION_NAME not in existing:
        client.create_collection(name=_DOC_COLLECTION_NAME)
    existing = {c.name for c in client.list_collections()}
    # Only build embeddings if collection is empty or embedding model changed
    collection = client.get_or_create_collection(name=_DOC_COLLECTION_NAME)
    try:
        stats = collection.get(include=["metadatas"]) or {}
        metas = stats.get("metadatas", [[]])[0] if stats else []
        if not metas:
            # empty - initial build
            create_or_rebuild_index()
        else:
            # check emb_model tag on first metadata
            first_meta = metas[0] if metas else {}
            if first_meta.get("emb_model") != _EMB_MODEL_NAME:
                print("[INFO] Embedding model mismatch or changed; rebuilding index")
                create_or_rebuild_index()
            else:
                print("[INFO] existing embeddings found; skipping rebuild")
    except Exception:
        # fallback to safe rebuild
        create_or_rebuild_index()
    print(f"[INFO] collections after init: {existing}")


def _get_all_collection():
    """
    Helper to get the Chroma collection for NGOs.
    Assumes initialize_vector_store() has been called.
    """
    client = _get_chroma_client()
    return client.get_or_create_collection(name=_DOC_COLLECTION_NAME)


def create_all_ngo_embeddings() -> None:
    print("Creating NGO embeddings...")
    """
    Create embeddings for all existing NGOs and store in vector DB.
    Call this:
    - Once after first setting up the vector DB
    - When you need to rebuild the index
    """
    collection = _get_all_collection()

    ngos = NGOModel.find_all_active()
    if not ngos:
        return

    emb_model = _get_embedding_model()

    ids: List[str] = []
    texts: List[str] = []
    metadatas: List[Dict[str, Any]] = []

    for ngo in ngos:
        raw_id = str(ngo["_id"])
        pref_id = f"ngo:{raw_id}"
        text = _build_ngo_text(ngo)
        ids.append(pref_id)
        texts.append(text)
        raw_meta = {
            "type": "ngo",
            "source_id": raw_id,
            "username": ngo.get("Username", ""),
            "categories": ngo.get("Categories", []),
            "city": ngo.get("Address", {}).get("city", ""),
            "state": ngo.get("Address", {}).get("state", ""),
            "pincode": ngo.get("Address", {}).get("pincode", ""),
            "emb_model": _EMB_MODEL_NAME,
        }
        metadatas.append(_normalize_metadata(raw_meta))

    embeddings = emb_model.encode(texts, show_progress_bar=True).tolist()

    # Clear existing entries for these IDs then add


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


def create_all_issue_embeddings() -> None:
    print("Creating issue embeddings...")
    """Create embeddings for all existing issues/reports and store in vector DB."""
    collection = _get_all_collection()

    reports = ReportsModel.find_by_severity_range(0.0, 10.0) if hasattr(ReportsModel, 'find_by_severity_range') else []
    if not reports:
        return
    emb_model = _get_embedding_model()

    ids: List[str] = []
    texts: List[str] = []
    metadatas: List[Dict[str, Any]] = []

    for rpt in reports:
        raw_id = str(rpt.get('_id'))
        pref_id = f"issue:{raw_id}"
        text = _build_issue_text(rpt)
        ids.append(pref_id)
        texts.append(text)
        raw_meta = {
            "type": "issue",
            "source_id": raw_id,
            "site": rpt.get('Location') or rpt.get('Address', {}).get('city', ''),
            "status": rpt.get('Status') or rpt.get('status') or '',
            "emb_model": _EMB_MODEL_NAME,
        }
        metadatas.append(_normalize_metadata(raw_meta))

    embeddings = emb_model.encode(texts, show_progress_bar=True).tolist()

    try:
        collection.delete(ids=ids)
    except Exception:
        pass

    collection.add(
        ids=ids,
        embeddings=embeddings,
        metadatas=metadatas,
        documents=texts,
    )

    client = _get_chroma_client()
    if hasattr(client, "persist"):
        try:
            client.persist()
        except Exception as e:
            print("[ERROR] Chroma client.persist() call failed:", e)
            traceback.print_exc()
    else:
        print("[DEBUG] Chroma client has no persist() method; skipping persist call")


def create_or_rebuild_index(sources: Optional[List[str]] = None) -> None:
    """Create or rebuild the full index for requested sources.
    sources: list of 'ngos','issues','sites','faq' (sites/faq not implemented yet)
    """
    if sources is None:
        sources = ["ngos", "issues"]

    if "ngos" in sources:
        create_all_ngo_embeddings()
    if "issues" in sources:
        create_all_issue_embeddings()


def add_report_to_vector_db(report_id: str) -> None:
    """
    Add a single report/issue to the vector DB. Call this after creating a report.
    """
    if not report_id:
        return

    collection = _get_all_collection()
    emb_model = _get_embedding_model()

    rpt = ReportsModel.find_by_id(report_id)
    if not rpt:
        return

    text = _build_issue_text(rpt)
    embedding = emb_model.encode(text).tolist()
    pref_id = f"issue:{report_id}"

    raw_meta = {
        "type": "issue",
        "source_id": report_id,
        "site": rpt.get('Location') or rpt.get('Address', {}).get('city', ''),
        "status": rpt.get('Status') or rpt.get('status') or '',
        "emb_model": _EMB_MODEL_NAME,
    }

    collection.add(
        ids=[pref_id],
        embeddings=[embedding],
        metadatas=[_normalize_metadata(raw_meta)],
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


def update_report_in_vector_db(report_id: str) -> None:
    """
    Update a single report/issue in the vector DB. If the report is removed
    or inactive, it will be deleted from the index.
    """
    if not report_id:
        return

    collection = _get_all_collection()
    emb_model = _get_embedding_model()

    rpt = ReportsModel.find_by_id(report_id)

    # If report no longer exists, remove it
    if not rpt:
        pref_id = f"issue:{report_id}"
        try:
            collection.delete(ids=[pref_id])
        except Exception:
            pass
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

    text = _build_issue_text(rpt)
    embedding = emb_model.encode(text).tolist()
    pref_id = f"issue:{report_id}"

    try:
        collection.delete(ids=[pref_id])
    except Exception:
        pass

    raw_meta = {
        "type": "issue",
        "source_id": report_id,
        "site": rpt.get('Location') or rpt.get('Address', {}).get('city', ''),
        "status": rpt.get('Status') or rpt.get('status') or '',
        "emb_model": _EMB_MODEL_NAME,
    }

    collection.add(
        ids=[pref_id],
        embeddings=[embedding],
        metadatas=[_normalize_metadata(raw_meta)],
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


def remove_report_from_vector_db(report_id: str) -> None:
    """
    Remove a report/issue from the vector DB (called when report deleted).
    """
    if not report_id:
        return

    collection = _get_all_collection()

    pref_id = f"issue:{report_id}"
    try:
        collection.delete(ids=[pref_id])
    except Exception:
        pass
    try:
        client = _get_chroma_client()
        if hasattr(client, "persist"):
            client.persist()
        else:
            print("[DEBUG] Chroma client has no persist() method; skipping persist call")
    except Exception as e:
        print("[ERROR] Chroma client.persist() call failed:", e)
        traceback.print_exc()


def add_ngo_to_vector_db(ngo_id: str) -> None:
    """
    Add single NGO to vector DB (called when new NGO is registered).
    Must be called automatically after NGO creation.
    """
    if not ngo_id:
        return


    collection = _get_all_collection()
    emb_model = _get_embedding_model()

    ngo = NGOModel.find_by_id(ngo_id)
    if not ngo or not ngo.get("isActive", True):
        return

    text = _build_ngo_text(ngo)
    embedding = emb_model.encode(text).tolist()
    pref_id = f"ngo:{ngo_id}"

    collection.add(
        ids=[pref_id],
        embeddings=[embedding],
        metadatas=[_normalize_metadata({
            "type": "ngo",
            "source_id": ngo_id,
            "username": ngo.get("Username", ""),
            "categories": ngo.get("Categories", []),
            "city": ngo.get("Address", {}).get("city", ""),
            "state": ngo.get("Address", {}).get("state", ""),
            "pincode": ngo.get("Address", {}).get("pincode", ""),
            "emb_model": _EMB_MODEL_NAME,
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


    collection = _get_all_collection()
    emb_model = _get_embedding_model()

    ngo = NGOModel.find_by_id(ngo_id)

    # If NGO no longer exists or is inactive, remove it
    if not ngo or not ngo.get("isActive", True):
        pref_id = f"ngo:{ngo_id}"
        collection.delete(ids=[pref_id])
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

    # Delete old entry then re-add (using prefixed id)
    pref_id = f"ngo:{ngo_id}"
    try:
        collection.delete(ids=[pref_id])
    except Exception:
        pass
    collection.add(
        ids=[pref_id],
        embeddings=[embedding],
        metadatas=[_normalize_metadata({
            "type": "ngo",
            "source_id": ngo_id,
            "username": ngo.get("Username", ""),
            "categories": ngo.get("Categories", []),
            "city": ngo.get("Address", {}).get("city", ""),
            "state": ngo.get("Address", {}).get("state", ""),
            "pincode": ngo.get("Address", {}).get("pincode", ""),
            "emb_model": _EMB_MODEL_NAME,
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

    collection = _get_all_collection()

    pref_id = f"ngo:{ngo_id}"
    collection.delete(ids=[pref_id])
    try:
        client = _get_chroma_client()
        if hasattr(client, "persist"):
            client.persist()
        else:
            print("[DEBUG] Chroma client has no persist() method; skipping persist call")
    except Exception as e:
        print("[ERROR] Chroma client.persist() call failed:", e)
        traceback.print_exc()


def search_vector_db(query_text: str, top_k, where: Optional[Dict[str, Any]] = None):
    """
    Generic search helper for the shared vector DB. This will be reused
    by NGO matcher and chatbot.
    """
    if not query_text:
        return []

    collection = _get_all_collection()
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

        print(f"[INFO] Chroma collection '{_DOC_COLLECTION_NAME}' total entries={total}")
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

    for idx, id in enumerate(ids):
        hits.append(
            {
                "id": id,
                "metadata": metadatas[idx] if idx < len(metadatas) else {},
                "distance": distances[idx] if idx < len(distances) else None,
                "document": documents[idx] if idx < len(documents) else "",
            }
        )
    print(f"[DEBUG] hits: {hits}")
    return hits

