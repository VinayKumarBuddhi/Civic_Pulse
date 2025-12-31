from typing import List
from sentence_transformers import SentenceTransformer

_model = None


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Return embeddings for a list of texts."""
    model = _get_model()
    # model.encode returns numpy arrays; convert to list
    embs = model.encode(texts, show_progress_bar=False)
    return embs.tolist()
