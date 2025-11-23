"""Utility helpers for loading embedding models in a single place."""

from __future__ import annotations

import threading

from langchain_huggingface import HuggingFaceEmbeddings

_EMBEDDINGS_CACHE: HuggingFaceEmbeddings | None = None
_LOAD_LOCK = threading.Lock()


def _build_embeddings() -> HuggingFaceEmbeddings:
    """Instantiate the shared HuggingFace embeddings client.

    Newer versions of torch raise "Cannot copy out of meta tensor" when
    ``SentenceTransformer`` attempts to move lazily-loaded weights from the
    temporary ``meta`` device to CPU. Explicitly disabling the low memory path
    ensures tensors are materialised before ``.to('cpu')`` executes.
    """

    base_kwargs = {
        "model_name": "sentence-transformers/all-MiniLM-L6-v2",
        "model_kwargs": {
            "device": "cpu",
            # Force full weight loading to avoid meta tensor copies on torch>=2.9
            "model_kwargs": {"low_cpu_mem_usage": False},
        },
        "encode_kwargs": {"normalize_embeddings": True},
    }

    try:
        return HuggingFaceEmbeddings(**base_kwargs)
    except NotImplementedError as err:
        raise RuntimeError(
            "Failed to load sentence-transformers embeddings with the current "
            "torch build. Try reinstalling 'sentence-transformers<5' or torch<2.9."
        ) from err


def get_embeddings() -> HuggingFaceEmbeddings:
    """Return a cached embeddings client so we load the model only once."""

    global _EMBEDDINGS_CACHE

    if _EMBEDDINGS_CACHE is None:
        with _LOAD_LOCK:
            if _EMBEDDINGS_CACHE is None:
                _EMBEDDINGS_CACHE = _build_embeddings()

    return _EMBEDDINGS_CACHE
