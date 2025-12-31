import os
import json
import traceback
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import streamlit as st
from openai import OpenAI

from rag.vector_store import search_vector_db

# Optional embedding helper; not required because search_vector_db accepts text queries
# from rag.embeddings import embed_texts
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def build_context(hits: List[Dict[str, Any]], max_chars: int = 3000) -> str:
    """Build a concatenated context string from retrieval hits.
    Prioritize faq/site first, then issue, then ngo when ordering snippets.
    """
    if not hits:
        return ""

    # Assign priority based on metadata type when present
    def priority(hit: Dict[str, Any]) -> int:
        meta = hit.get("metadata", {}) or {}
        t = meta.get("type") if isinstance(meta, dict) else None
        if t == "faq":
            return 0
        if t == "site_info" or t == "site":
            return 1
        if t == "issue":
            return 2
        if t == "ngo":
            return 3
        return 4

    sorted_hits = sorted(hits, key=priority)

    parts: List[str] = []
    seen_ids = set()
    for h in sorted_hits:
        # Attempt to extract a stable id
        hid = h.get("ngo_id") or h.get("id") or h.get("source_id") or str(h.get("metadata", {}).get("ngo_id", ""))
        if hid in seen_ids:
            continue
        seen_ids.add(hid)
        meta = h.get("metadata", {}) or {}
        header = f"Source: {hid}"
        if isinstance(meta, dict):
            # include a short metadata summary
            md_items = []
            for k in ("type", "location", "city", "site", "status"):
                if meta.get(k):
                    md_items.append(f"{k}={meta.get(k)}")
            if md_items:
                header += " (" + ", ".join(md_items) + ")"
        doc = (h.get("document") or "").strip()
        if not doc:
            continue
        snippet = doc if len(doc) <= 800 else doc[:800] + "..."
        parts.append(header + "\n" + snippet)

    context = "\n\n---\n\n".join(parts)
    if len(context) > max_chars:
        return context[:max_chars]
    return context


def build_prompt(question: str, context: str) -> str:
    """Construct the prompt for the LLM using RAG-safe instructions."""
    system = (
        "You are a helpful civic assistant. Use the context provided to answer the user's question."
        " If the information is not present in the context, reply 'Information not available'. Be concise."
        '''You are Civic Pulse, an intelligent civic assistance chatbot.

Behavior rules:
- Reply confidently and directly, not as if you are searched from the context for information.
- If the question is unrelated to civic issues, NGOs, public services, or the platform, answer in a general helpful way.
- If information is not found in the provided context, clearly say it is not available.

Platform overview:
Civic Pulse is a civic issue reporting and management system with four roles: User, NGO, Volunteer, and Admin.

Core features:
- Users can report civic issues, track their status, apply as volunteers, and use a RAG-based chatbot.
- NGOs receive automatically matched issues using RAG, manage volunteers, assign work, and update issue progress.
- Volunteers view assigned issues and update issue status.
- Admins manage NGOs, volunteers, and monitor system-wide activity.

Issue reporting flow:
1. User reports an issue → stored in the Reports collection.
2. RAG system matches the issue with suitable NGOs based on category and description.
3. Best NGO is assigned automatically.
4. NGO assigns the issue to volunteers.
5. Volunteers update progress and mark issues resolved.
6. Status updates are visible to users and NGOs.


Database overview:
- User: stores users and their reported issues.
- Reports: stores all issues with status and assignments.
- NGO: stores NGO profiles, categories, issues, and volunteers.
- Volunteers: stores volunteer profiles and assigned works.
- Applications: stores volunteer applications to NGOs.
- Admin: stores admin accounts.

main rule is should not reply like "in the provided context" rather should reply like you know the answer.
'''
    )
    prompt = f"{system}\n\nContext:\n{context}\n\nUser Question:\n{question}\n\nAnswer:" 
    return prompt


def call_llm(
    prompt: str,
    model: str = "gpt-4.1-mini",
    max_tokens: int = 512
) -> Dict[str, Any]:
    """
    Call OpenAI LLM using Responses API.
    Returns: {"text": str, "raw": Any}
    """
    client = OpenAI(api_key=OPENAI_API_KEY)
    if not OPENAI_API_KEY:
        return _fallback_response(prompt)

    try:
        response = client.responses.create(
            model=model,
            input=prompt,
            max_output_tokens=max_tokens,
            temperature=0.0,
        )

        return {
            "text": response.output_text.strip(),
            "raw": response
        }

    except Exception as e:
        err = str(e).lower()
        print("[ERROR] OpenAI call failed:", e)
        traceback.print_exc()

        if "quota" in err or "insufficient_quota" in err:
            return {
                "text": "LLM request failed due to insufficient quota. Check billing.",
                "raw": {"error": str(e)}
            }

        if "rate" in err:
            return {
                "text": "LLM request failed due to rate limiting. Please retry later.",
                "raw": {"error": str(e)}
            }

        return _fallback_response(prompt)
def _fallback_response(prompt: str) -> Dict[str, Any]:
    if not prompt:
        return {"text": "No prompt provided.", "raw": None}

    ctx = ""
    if "Context:" in prompt:
        ctx = prompt.split("Context:")[1]

    summary = "\n".join(ctx.splitlines()[:6])

    return {
        "text": (
            "Using retrieved context:\n"
            f"{summary}\n\n"
            "Answer: The information above was found in the retrieved context. "
            "If you need more details, please provide more data."
        ),
        "raw": None
    }


def parse_recommendations_from_hits(hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert retrieval hits to lightweight recommendations usable by the UI."""
    recs = []
    for h in hits:
        meta = h.get("metadata") or {}
        hid = h.get("ngo_id") or h.get("id") or meta.get("source_id") or meta.get("ngo_id")
        rec = {
            "id": hid,
            "type": (meta.get("type") if isinstance(meta, dict) else None) or "ngo",
            "score": None if h.get("distance") is None else round(1.0 - float(h.get("distance")), 4),
            "snippet": (h.get("document") or "")[:300],
            "metadata": meta,
        }
        recs.append(rec)
    return recs


def chat_with_rag(question: str, top_k: int = 6, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Full pipeline: retrieval -> prompt -> LLM -> return structured result."""
    if not question or not question.strip():
        return {"answer": "Please ask a question.", "recommendations": [], "references": [], "raw": None}

    # Retrieval (search_vector_db accepts raw text query)
    try:
        hits = search_vector_db(question, top_k=top_k, where=filters)
    except Exception as e:
        print("[ERROR] Retrieval failed:", e)
        traceback.print_exc()
        hits = []

    context = build_context(hits)
    prompt = build_prompt(question, context)
    llm_result = call_llm(prompt)

    answer_text = llm_result.get("text") if isinstance(llm_result, dict) else str(llm_result)
    recs = parse_recommendations_from_hits(hits)
    refs = [r.get("id") for r in recs if r.get("id")]

    return {
        "answer": answer_text,
        "recommendations": recs,
        "references": refs,
        "raw": llm_result.get("raw") if isinstance(llm_result, dict) else None,
    }
