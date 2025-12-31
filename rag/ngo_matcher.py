"""
RAG-Based NGO Matcher

Implements Step 6 (ISSUE_FLOW_IMPLEMENTATION.md):
- Creates issue embeddings
- Searches shared vector DB for similar NGOs
- Matches issues to best NGO based on similarity
"""

from typing import List, Dict, Optional, Tuple
from bson import ObjectId

from rag.vector_store import search_vector_db
from database.models import ReportsModel, NGOModel


def _build_issue_text(report: Dict) -> str:
    """
    Build a descriptive text representation for an issue to feed into the
    embedding model. This combines description, categories, and location.
    """
    description = report.get("Description", "")
    categories = report.get("Categories", [])
    address = report.get("Address", {})
    severity_score = report.get("severityScore", 0.0)
    
    categories_text = ", ".join(categories) if categories else ""
    address_parts = [
        address.get("area", ""),
        address.get("city", ""),
        address.get("district", ""),
        address.get("state", ""),
        address.get("pincode", ""),
    ]
    address_text = ", ".join([p for p in address_parts if p])
    
    # Include severity in the text for better matching
    severity_text = f"Severity: {severity_score}/10" if severity_score > 0 else ""
    
    parts = [
        f"Issue: {description}",
        f"Categories: {categories_text}",
        f"Location: {address_text}",
    ]
    
    if severity_text:
        parts.append(severity_text)
    
    return " | ".join([p for p in parts if p])


def search_similar_ngos(
    issue_description: str,
    issue_categories: List[str],
    issue_location: Optional[Dict] = None,
    issue_address: Optional[Dict] = None,
    severity_score: float = 0.0,
    top_k: int = 5
) -> List[Tuple[str, float]]:
    """
    Search shared vector DB for NGOs similar to the issue.
    
    Args:
        issue_description: Issue description text
        issue_categories: List of issue categories
        issue_location: Optional location dict with latitude/longitude
        issue_address: Optional address dict
        severity_score: Issue severity score (0.0-10.0)
        top_k: Number of top matches to return
    
    Returns:
        List of (NGO ID, similarity_score) tuples sorted by score (highest first)
        Similarity score is 1 - distance (higher = more similar)
    """
    # Build query text from issue details
    categories_text = ", ".join(issue_categories) if issue_categories else ""
    
    address_parts = []
    if issue_address:
        address_parts = [
            issue_address.get("area", ""),
            issue_address.get("city", ""),
            issue_address.get("district", ""),
            issue_address.get("state", ""),
            issue_address.get("pincode", ""),
        ]
    address_text = ", ".join([p for p in address_parts if p])
    
    severity_text = f"Severity: {severity_score}/10" if severity_score > 0 else ""
    
    query_parts = [
        f"Issue: {issue_description}",
        f"Categories: {categories_text}",
    ]
    
    if address_text:
        query_parts.append(f"Location: {address_text}")
    
    if severity_text:
        query_parts.append(severity_text)
    
    query_text = " | ".join([p for p in query_parts if p])
    
    # Optional: Filter by location (city, state, pincode) for geographic matching    
    where_clause = {"type": "ngo"}
    # if issue_address:
    #     city = issue_address.get("city", "")
    #     state = issue_address.get("state", "")
    #     pincode = issue_address.get("pincode", "")

    #     # Add exact metadata filters when present
    #     if city:
    #         where_clause["city"] = city
    #     if state:
    #         where_clause["state"] = state
    #     if pincode:
    #         where_clause["pincode"] = pincode

    print("query_text......",query_text)
    # Search vector DB
    results = search_vector_db(query_text, top_k=top_k, where=where_clause)
    
    # Convert to list of (ngo_id, similarity_score) tuples
    matches = []
    for hit in results:
        # `search_vector_db` returns prefixed id e.g. "ngo:<id>" in `id` and may include `ngo_id` backwards-compatible
        raw_ngo_id = hit.get("ngo_id") or hit.get("id", "")
        # If id prefixed like "ngo:<id>", strip prefix
        if isinstance(raw_ngo_id, str) and raw_ngo_id.startswith("ngo:"):
            ngo_id = raw_ngo_id.split(":", 1)[1]
        else:
            ngo_id = raw_ngo_id

        distance = hit.get("distance")
        if ngo_id and distance is not None:
            similarity = 1.0 - distance
            matches.append((ngo_id, similarity))

    
    # Sort by similarity (highest first)
    matches.sort(key=lambda x: x[1], reverse=True)
    
    return matches


def match_issue_to_ngo(report_id: str) -> Optional[str]:
    """
    Match issue to best NGO using RAG.
    
    Args:
        report_id: Report/Issue ID (string)
    
    Returns:
        NGO ID of best match (string) or None if no match found
    """
    # Get issue details from Reports collection
    report = ReportsModel.find_by_id(report_id)
    if not report:
        return None
    
    # Extract issue details
    description = report.get("Description", "")
    categories = report.get("Categories", [])
    location = report.get("Location", {})
    address = report.get("Address", {})
    severity_score = report.get("severityScore", 0.0)
    
    if not description and not categories:
        # Can't match without at least description or categories
        return None
    
    # Search for similar NGOs
    matches = search_similar_ngos(
        issue_description=description,
        issue_categories=categories,
        issue_location=location,
        issue_address=address,
        severity_score=severity_score,
        top_k=5  # Get top 5, then filter for active NGOs
    )
    
    if not matches:
        return None
    print("matches found......",matches)
    # Filter matches to only active NGOs and verify they exist
    for ngo_id, similarity_score in matches:
        ngo = NGOModel.find_by_id(ngo_id)
        if ngo and ngo.get("isActive", True):
            # Found an active NGO match
            return ngo_id
    
    # No active NGO found in matches
    return None

