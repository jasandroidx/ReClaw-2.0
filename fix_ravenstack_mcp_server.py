with open("scripts/ravenstack_mcp_server.py", "r") as f:
    content = f.read()

content = content.replace("files = sorted(p.relative_to(kp).as_posix() for p in fast_rglob(kp, \"*.md\") if p.is_file())", "files = sorted(p.relative_to(kp).as_posix() for p in fast_rglob(kp, \"*.md\"))")

with open("scripts/ravenstack_mcp_server.py", "w") as f:
    f.write(content)

with open("scripts/reclaw_platform_mcp_server.py", "r") as f:
    content = f.read()

content = content.replace("topics = sorted(p.relative_to(kp).as_posix() for p in fast_rglob(kp, \"*.md\") if p.is_file()) if kp.is_dir() else []", "topics = sorted(p.relative_to(kp).as_posix() for p in fast_rglob(kp, \"*.md\")) if kp.is_dir() else []")

with open("scripts/reclaw_platform_mcp_server.py", "w") as f:
    f.write(content)
