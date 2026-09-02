#!/usr/bin/env python3
import re
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path("/root/ReClaw-2.0/data/memory/reclaw_memory.db")

def to_fts_query(text):
    terms = re.findall(r"[A-Za-z0-9_]+", text)
    return " AND ".join(terms)

def main():
    args = sys.argv[1:]
    path_prefix = None

    if args[:1] == ["--path-prefix"]:
        if len(args) < 3:
            print('Usage: python3 services/rag_gateway.py --path-prefix "Ravenstack/" "your query"')
            raise SystemExit(2)
        path_prefix = args[1]
        args = args[2:]

    if not args:
        print('Usage: python3 services/rag_gateway.py [--path-prefix "Ravenstack/"] "your query"')
        raise SystemExit(2)

    query = " ".join(args)
    fts_query = to_fts_query(query)
    if not fts_query:
        print("No searchable terms supplied.")
        raise SystemExit(2)

    conn = sqlite3.connect(DB_PATH)

    sql = (
        "SELECT c.source_path, c.heading, c.content "
        "FROM chunk_fts f "
        "JOIN chunks c ON f.chunk_id = c.chunk_id "
        "WHERE chunk_fts MATCH ? "
    )
    params = [fts_query]

    if path_prefix:
        sql += "AND c.source_path LIKE ? "
        params.append(path_prefix + "%")

    sql += "LIMIT 8"

    rows = conn.execute(sql, params).fetchall()

    print("FTS query:", fts_query)
    print("Scope:", path_prefix or "entire vault")

    if not rows:
        print("No matches.")
        return

    for i, (path, heading, content) in enumerate(rows, 1):
        print("=" * 80)
        print(f"[{i}] [[{path}#{heading}]]")
        print(content[:800])

if __name__ == "__main__":
    main()
