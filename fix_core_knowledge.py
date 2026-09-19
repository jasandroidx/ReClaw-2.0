with open("core/knowledge.py", "r") as f:
    content = f.read()

content = content.replace("from pathlib import Path\nfrom core.fs_utils import fast_rglob\nfrom typing import Any, Dict", "from pathlib import Path\nfrom typing import Any, Dict")
content = content.replace("        from core.fs_utils import fast_rglob\n        import joblib", "        import joblib")

with open("core/knowledge.py", "w") as f:
    f.write(content)
