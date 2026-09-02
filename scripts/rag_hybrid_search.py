#!/usr/bin/env python3
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))

import hashlib
import re
import sqlite3
import sys
from pathlib import Path

from rag.client import RAGClient

FTS_DB = Path('/root/ReClaw-2.0/data/memory/reclaw_memory.db')


def clean_terms(text):
    return ' AND '.join(re.findall(r'[A-Za-z0-9_]+', text))


def fingerprint(text):
    normalized = ' '.join((text or '').lower().split())
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def get_fts(query, limit=30):
    if not FTS_DB.exists():
        return []

    q = clean_terms(query)
    if not q:
        return []

    conn = sqlite3.connect(FTS_DB)
    try:
        rows = conn.execute(
            'SELECT source_path, heading, content '
            'FROM chunk_fts WHERE chunk_fts MATCH ? LIMIT ?',
            (q, limit),
        ).fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()

    output = []
    for path, heading, content in rows:
        output.append({
            'path': path,
            'section': heading,
            'text': content,
            'channel': 'fts',
        })
    return output


def get_vector(query, limit=30):
    response = RAGClient().search(
        query=query,
        top_k=limit,
        vault_only=True,
        min_score=0.0,
    )

    output = []
    for item in response.results:
        citation = item.citation
        output.append({
            'path': citation.source_path,
            'section': citation.section_header or 'Overview',
            'text': item.text,
            'channel': 'vector',
        })
    return output


def hybrid(query, limit=5):
    fused = {}

    for rank, item in enumerate(get_vector(query), 1):
        key = fingerprint(item['text'])
        if key not in fused:
            fused[key] = dict(item)
            fused[key]['rrf'] = 0.0
            fused[key]['channels'] = set()
        fused[key]['rrf'] += 1.0 / (60 + rank)
        fused[key]['channels'].add('vector')

    for rank, item in enumerate(get_fts(query), 1):
        key = fingerprint(item['text'])
        if key not in fused:
            fused[key] = dict(item)
            fused[key]['rrf'] = 0.0
            fused[key]['channels'] = set()
        fused[key]['rrf'] += 1.0 / (60 + rank)
        fused[key]['channels'].add('fts')

    rows = list(fused.values())
    for row in rows:
        if len(row['channels']) == 2:
            row['rrf'] += 0.02

    rows.sort(key=lambda row: row['rrf'], reverse=True)
    return rows[:limit]


def main():
    if len(sys.argv) < 2:
        print('Usage: python3 scripts/rag_hybrid_search.py YOUR_QUESTION')
        raise SystemExit(2)

    query = ' '.join(sys.argv[1:])
    rows = hybrid(query)

    print('QUERY:', query)
    print('RESULTS:', len(rows))

    for i, row in enumerate(rows, 1):
        print('=' * 88)
        print('[{}] score={:.4f} channels={}'.format(
            i, row['rrf'], ','.join(sorted(row['channels']))
        ))
        print('[[{}#{}]]'.format(row['path'], row['section']))
        print(row['text'][:700].replace(chr(10), ' '))


if __name__ == '__main__':
    main()
