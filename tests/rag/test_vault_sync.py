"""
Tests for vault synchronization.
"""

import tempfile
from pathlib import Path

import pytest

from rag.vault_sync import VaultSynchronizer
from rag.vectorstore import VectorStore
from rag.ingestor import DocumentIngestor
from rag.embeddings import EmbeddingManager


class TestVaultSynchronizer:
    def test_discover_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir)
            # Create test files
            (vault / "note1.md").write_text("# Note 1\n\nContent here.")
            (vault / "subdir").mkdir()
            (vault / "subdir" / "note2.md").write_text("# Note 2\n\nMore content.")
            # Create file that should be skipped
            (vault / ".obsidian").mkdir()
            (vault / ".obsidian" / "config").write_text("obsidian config")

            sync = VaultSynchronizer(
                vault_path=vault,
                state_dir=Path(tmpdir) / "state",
            )
            files = sync._discover_files()
            paths = [f.name for f in files]
            assert "note1.md" in paths
            assert "note2.md" in paths
            assert "config" not in paths

    def test_file_checksum(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("test content")
            f.flush()

            sync = VaultSynchronizer(
                vault_path="/tmp",
                state_dir=Path(tempfile.gettempdir()),
            )
            cs1 = sync._file_checksum(Path(f.name))
            cs2 = sync._file_checksum(Path(f.name))
            assert cs1 == cs2
            assert len(cs1) == 32  # MD5 hex
            Path(f.name).unlink()

    def test_skip_patterns(self):
        sync = VaultSynchronizer(
            vault_path="/tmp",
            state_dir=Path(tempfile.gettempdir()),
        )
        # Files in .obsidian should be skipped
        assert any(".obsidian/" in p for p in sync.SKIP_PATTERNS)
        assert any("templates/" in p for p in sync.SKIP_PATTERNS)
        assert "**/inbox/**" in sync.SKIP_PATTERNS
        assert "inbox" in sync.HIDDEN_STATUSES
        assert "stub" in sync.HIDDEN_STATUSES

    def test_inbox_and_dry_run_not_discovered(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir)
            (vault / "Ravenstack").mkdir()
            (vault / "Ravenstack" / "wiki").mkdir(parents=True)
            (vault / "Ravenstack" / "inbox").mkdir()
            (vault / "Ravenstack" / "harvest" / "dry-run").mkdir(parents=True)
            (vault / "Ravenstack" / "principles.md").write_text("# P\n")
            (vault / "Ravenstack" / "wiki" / "hot.md").write_text("# hot\n")
            (vault / "Ravenstack" / "inbox" / "raw.md").write_text(
                "---\nstatus: inbox\n---\n# raw\n"
            )
            (vault / "Ravenstack" / "harvest" / "dry-run" / "x.md").write_text("# x\n")
            (vault / "Ravenstack" / "ops").mkdir()
            (vault / "Ravenstack" / "ops" / "morning-brief-2026-09-12.md").write_text(
                "# brief\n"
            )
            sync = VaultSynchronizer(
                vault_path=vault,
                state_dir=Path(tmpdir) / "state",
            )
            names = [str(p.relative_to(vault)).replace("\\", "/") for p in sync._discover_files()]
            assert "Ravenstack/principles.md" in names
            assert "Ravenstack/wiki/hot.md" in names
            assert not any("inbox" in n for n in names)
            assert not any("dry-run" in n for n in names)
            assert not any("morning-brief" in n for n in names)

    def test_state_persistence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sync = VaultSynchronizer(
                vault_path=Path(tmpdir),
                state_dir=Path(tmpdir) / "state",
            )
            sync._state = {
                "test.md": {"checksum": "abc123", "doc_id": "doc-1", "synced_at": "2026-01-01"}
            }
            sync._save_state()

            # Load in new instance
            sync2 = VaultSynchronizer(
                vault_path=Path(tmpdir),
                state_dir=Path(tmpdir) / "state",
            )
            assert "test.md" in sync2._state
            assert sync2._state["test.md"]["doc_id"] == "doc-1"

    def test_full_sync_empty_vault(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sync = VaultSynchronizer(
                vault_path=Path(tmpdir),
                state_dir=Path(tmpdir) / "state",
            )
            status = sync.full_sync()
            assert status.total_documents == 0
            assert not status.errors
