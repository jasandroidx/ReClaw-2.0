with open("rag/vault_sync.py", "r") as f:
    content = f.read()

content = content.replace("        for path in fast_rglob(self.vault_path, \"*\"):\n\n                continue", "        for path in fast_rglob(self.vault_path, \"*\"):")

with open("rag/vault_sync.py", "w") as f:
    f.write(content)
