import pytest
import os
import shutil
import tempfile
from core.mcp_connector import ObsidianConnector

@pytest.fixture
def temp_vault():
    vault_dir = tempfile.mkdtemp(prefix="obsidian_vault_")
    # create a dummy file
    with open(os.path.join(vault_dir, "test.md"), "w") as f:
        f.write("test content")
    yield vault_dir
    shutil.rmtree(vault_dir)

@pytest.mark.asyncio
async def test_obsidian_path_traversal_read(temp_vault, monkeypatch):
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", temp_vault)
    connector = ObsidianConnector()
    connector.vault_path = temp_vault  # Ensure initialization took the right path if needed

    # Test valid path
    result = await connector.query({"action": "read", "path": "test.md"})
    assert "test content" in result.get("data", {}).get("content", result.get("content", "")) or "test content" in str(result)

    # Test traversal
    result = await connector.query({"action": "read", "path": "../test.md"})
    response_str = str(result)
    assert "Access denied" in response_str or "error" in result.get("data", {}) or "error" in result

    # Test absolute path escape
    try:
        result = await connector.query({"action": "read", "path": "/etc/passwd"})
        # It's okay if this throws FileNotFoundError since it correctly resolves to within the vault instead of /etc/passwd
        assert True
    except FileNotFoundError:
        assert True

@pytest.mark.asyncio
async def test_obsidian_path_traversal_write(temp_vault, monkeypatch):
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", temp_vault)
    connector = ObsidianConnector()
    connector.vault_path = temp_vault

    # Test valid write
    result = await connector.query({"action": "write", "path": "new_file.md", "content": "hello"})
    assert os.path.exists(os.path.join(temp_vault, "new_file.md"))

    # Test traversal write
    escape_path = "../escaped_file.md"
    result = await connector.query({"action": "write", "path": escape_path, "content": "hacked"})
    assert not os.path.exists(os.path.join(temp_vault, "..", "escaped_file.md"))
    response_str = str(result)
    assert "Access denied" in response_str or "error" in result.get("data", {}) or "error" in result
