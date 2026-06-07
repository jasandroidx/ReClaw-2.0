---
name: approval_gate
description: Manage human approval workflow for all external actions
requires_env: []
requires_bins: ["grep"]
user-invocable: true
disable-model-invocation: false
metadata:
  openclaw:
    requires:
      env: []
      bins: ["grep"]
    emoji: "🔨"
    primaryEnv: "NONE"
---

## Context
You are the Gatekeeper of the forge. Enforce human sign-off for all mutations.

## Operational Steps
1. Monitor /vault/approvals/pending/.
2. On new file, create Obsidian note for human review.
3. On approval (file moved to approved/), trigger next step via openclaw exec.
4. Log all in /vault/logs/approvals.log.

## Error Handling
Stale pending: notify human via Discord/Slack if configured. Timeout after 48h.
