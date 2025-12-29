"""
RAG (Retrieval-Augmented Generation) Module

This module contains:
- vector_store.py: Shared vector database for NGO matching and chatbot
- ngo_matcher.py: RAG-based NGO matching for issue assignment
"""

from rag.vector_store import (
    initialize_vector_store,
    create_all_ngo_embeddings,
    add_ngo_to_vector_db,
    update_ngo_in_vector_db,
    remove_ngo_from_vector_db,
    search_vector_db
)

from rag.ngo_matcher import (
    search_similar_ngos,
    match_issue_to_ngo
)

__all__ = [
    # Vector store functions
    'initialize_vector_store',
    'create_all_ngo_embeddings',
    'add_ngo_to_vector_db',
    'update_ngo_in_vector_db',
    'remove_ngo_from_vector_db',
    'search_vector_db',
    # NGO matcher functions
    'search_similar_ngos',
    'match_issue_to_ngo',
]

