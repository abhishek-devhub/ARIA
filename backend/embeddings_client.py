import numpy as np
import logging

logger = logging.getLogger(__name__)

_embedding_fn = None


def _get_embedding_fn():
    global _embedding_fn
    if _embedding_fn is None:
        logger.info("Loading ChromaDB DefaultEmbeddingFunction (all-MiniLM-L6-v2 via ONNX)...")
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
        _embedding_fn = DefaultEmbeddingFunction()
        logger.info("Embeddings function loaded successfully.")
    return _embedding_fn


def embed_text(text: str) -> list[float]:
    ef = _get_embedding_fn()
    result = ef([text])
    return list(result[0])


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    ef = _get_embedding_fn()
    results = ef(texts)
    return [list(r) for r in results]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    a_arr, b_arr = np.array(a), np.array(b)
    norm_a, norm_b = np.linalg.norm(a_arr), np.linalg.norm(b_arr)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a_arr, b_arr) / (norm_a * norm_b))
