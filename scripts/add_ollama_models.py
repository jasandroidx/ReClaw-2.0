#!/usr/bin/env python3
"""
SUPERSEDED -- do not use. Run scripts/fix_ollama_discovery.py instead.

This script hand-added model rows to models.providers.ollama.models. That was
the wrong fix. Per docs.openclaw.ai/providers/ollama/model-discovery:

  "A nonempty models.providers.ollama.models list selects manual models
   and skips discovery."

A nonempty list is precisely what stops OpenClaw from seeing the rest of the
pulled tags, so adding entries by hand keeps discovery switched off and leaves
you re-editing JSON every time you pull a model. Emptying the list is the fix.

It also assumed the list held plain strings; the real schema holds objects
({id, name, ...}), which is why this script failed to find anything and told
you to open the Raw JSON editor.
"""

import sys

print(__doc__.strip(), file=sys.stderr)
sys.exit(2)
