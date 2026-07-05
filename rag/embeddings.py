"""
Embedding Manager — local embeddings using sentence-transformers.

Uses all-MiniLM-L6-v2 by default (small, fast, CPU-friendly, MIT license).
Supports GPU if available. Everything works offline.

Future: support Ollama embeddings, custom fine-tuned models.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .models import DocumentChunk


class EmbeddingManager:
    """
    Manage embedding model and encode text chunks.

    Default model: 'all-MiniLM-L6-v2' (384 dimensions, ~80MB)
    - 22M parameters, runs fast on CPU
    - Good balance of speed and quality
    - MIT license (commercial safe)

    Alternative models (future):
    - 'all-mpnet-base-v2' (768d, higher quality, slower)
    - 'BAAI/bge-small-en' (384d, optimized for retrieval)
    """

    DEFAULT_MODEL = "all-MiniLM-L6-v2"
    EMBEDDING_DIM = 384  # for all-MiniLM-L6-v2

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,  # "cpu", "cuda", or None (auto)
        cache_dir: str | Path = "data/rag_embeddings",
        batch_size: int = 32,
    ):
        self.model_name = model_name or self.DEFAULT_MODEL
        self.device = device
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.batch_size = batch_size
        self._model = None
        self._embedding_dim: int | None = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def load_model(self) -> None:
        """Lazy-load the embedding model."""
        if self.is_loaded:
            return
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise RuntimeError(
                "sentence-transformers not installed. "
                "Run: pip install sentence-transformers"
            )

        self._model = SentenceTransformer(self.model_name, device=self.device)
        self._embedding_dim = self._model.get_sentence_embedding_dimension()

    def embed_chunks(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        """
        Embed a list of chunks. Mutates chunks in-place with embeddings.
        Uses disk cache to avoid re-embedding.
        """
        if not chunks:
            return chunks

        self.load_model()

        # Check cache for each chunk
        texts_to_embed: list[str] = []
        indices_to_embed: list[int] = []

        for i, chunk in enumerate(chunks):
            cached = self._get_cached_embedding(chunk)
            if cached:
                chunk.embedding = cached
            else:
                texts_to_embed.append(chunk.text)
                indices_to_embed.append(i)

        if texts_to_embed:
            # Batch encode
            embeddings = self._model.encode(
                texts_to_embed,
                batch_size=self.batch_size,
                show_progress_bar=len(texts_to_embed) > 50,
                convert_to_numpy=True,
            )

            for idx_in_batch, chunk_idx in enumerate(indices_to_embed):
                embedding = embeddings[idx_in_batch].tolist()
                chunks[chunk_idx].embedding = embedding
                self._cache_embedding(chunks[chunk_idx], embedding)

        return chunks

    def embed_query(self, query: str) -> list[float]:
        """Embed a search query."""
        self.load_model()
        embedding = self._model.encode(query, convert_to_numpy=True)
        return embedding.tolist()

    @property
    def embedding_dim(self) -> int:
        if self._embedding_dim is None:
            self.load_model()
        return self._embedding_dim or self.EMBEDDING_DIM

    def _cache_key(self, chunk: DocumentChunk) -> str:
        """Generate cache key from chunk content hash."""
        content = f"{chunk.text}:{self.model_name}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _cache_path(self, chunk: DocumentChunk) -> Path:
        return self.cache_dir / f"{self._cache_key(chunk)}.json"

    def _get_cached_embedding(self, chunk: DocumentChunk) -> list[float] | None:
        """Get cached embedding if available."""
        cache_path = self._cache_path(chunk)
        if cache_path.exists():
            try:
                data = json.loads(cache_path.read_text())
                if data.get("model") == self.model_name:
                    return data.get("embedding")
            except (json.JSONDecodeError, KeyError):
                pass
        return None

    def _cache_embedding(self, chunk: DocumentChunk, embedding: list[float]) -> None:
        """Cache embedding to disk."""
        cache_path = self._cache_path(chunk)
        cache_path.write_text(json.dumps({
            "model": self.model_name,
            "embedding": embedding,
            "chunk_id": chunk.id,
        }, indent=2))

    def get_info(self) -> dict:
        """Get information about the embedding model."""
        return {
            "model_name": self.model_name,
            "embedding_dim": self.embedding_dim if self.is_loaded else self.EMBEDDING_DIM,
            "device": self.device or "auto",
            "loaded": self.is_loaded,
            "cache_dir": str(self.cache_dir),
        }
