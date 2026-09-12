"""
RAG Configuration — integrates with core ReClaw settings.

Usage:
    from rag.config import get_rag_settings
    settings = get_rag_settings()
    print(settings.chunk_size)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.config import get_settings


class RAGSettings:
    """
    RAG-specific settings, layered on top of core ReClaw config.

    Reads from .env with RAG_ prefix, falls back to sensible defaults.
    """

    def __init__(self):
        self._core = get_settings()
        self._env = self._load_env()

    def _load_env(self) -> dict[str, str]:
        """Load RAG-prefixed env vars."""
        import os
        return {
            k.replace("RAG_", "").lower(): v
            for k, v in os.environ.items()
            if k.startswith("RAG_")
        }

    def _get(self, key: str, default: Any) -> Any:
        """Get value from env or default."""
        val = self._env.get(key.lower())
        if val is None:
            return default
        # Type conversion
        if isinstance(default, bool):
            return val.lower() in ("true", "1", "yes", "on")
        if isinstance(default, int):
            return int(val)
        if isinstance(default, float):
            return float(val)
        return val

    # Chunking
    @property
    def chunk_size(self) -> int:
        return self._get("chunk_size", 500)

    @property
    def chunk_overlap(self) -> int:
        return self._get("chunk_overlap", 100)

    @property
    def chunk_strategy(self) -> str:
        return self._get("chunk_strategy", "recursive")

    # Embeddings
    @property
    def embedding_model(self) -> str:
        return self._get("model", "all-MiniLM-L6-v2")

    @property
    def embedding_device(self) -> str | None:
        return self._get("device", None)

    @property
    def embedding_cache_dir(self) -> Path:
        return Path(self._get("cache_dir", "data/rag_embeddings"))

    # Vector Store
    @property
    def persist_dir(self) -> Path:
        return Path(self._get("persist_dir", "data/rag_chroma"))

    @property
    def collection_name(self) -> str:
        return self._get("collection", "reclaw_knowledge")

    # Vault Sync
    @property
    def vault_sync_interval(self) -> int:
        return self._get("vault_sync_interval", 300)

    @property
    def distilled_only(self) -> bool:
        """Default on: index compiled wiki/topics, not harvest/ops dumps."""
        return self._get("distilled_only", True)

    @property
    def vault_path(self) -> Path:
        """Get vault path from core settings."""
        return self._core.obsidian_vault_path

    # Expose core settings
    @property
    def core(self):
        return self._core

    def to_dict(self) -> dict[str, Any]:
        """Export all settings as dict."""
        return {
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "chunk_strategy": self.chunk_strategy,
            "embedding_model": self.embedding_model,
            "embedding_device": self.embedding_device,
            "embedding_cache_dir": str(self.embedding_cache_dir),
            "persist_dir": str(self.persist_dir),
            "collection_name": self.collection_name,
            "vault_sync_interval": self.vault_sync_interval,
            "distilled_only": self.distilled_only,
            "vault_path": str(self.vault_path),
        }


# Singleton
_rag_settings: RAGSettings | None = None


def get_rag_settings() -> RAGSettings:
    """Get the shared RAG settings instance."""
    global _rag_settings
    if _rag_settings is None:
        _rag_settings = RAGSettings()
    return _rag_settings
