---
title: ReClaw 2.0 · Userscript Ideas
created: 2026-06-19
updated: 2026-06-19
tags:
  - reclaw
  - openclaw
  - tampermonkey
  - userscript
  - control-ui
  - content-pipeline
  - passive-income
  - model-switcher
  - mischief-mode
aliases: [Userscript Ideas, Tampermonkey Scripts for OpenClaw, Model Switcher]
---

# ReClaw 2.0 Userscript Ideas for OpenClaw Control UI

**Status**: Seed / Brainstorm v1.1 (Model Switcher + Mischief Mode added)  
**Goal**: Lightweight browser enhancements to the *official* OpenClaw Control UI that supercharge ReClaw 2.0 rural monetization swarm + faceless Rural Data YouTube/TikTok content factory + creative/uncensored workflows.

## The 11 Best Tampermonkey Userscripts (Prioritized)

### Tier 1 – Highest Velocity (Build First)

- [ ] **01 - ReClaw Prompt Library + Quick Inject Sidebar**
- [ ] **02 - Transcript → Obsidian Content Package Exporter**
- [ ] **03 - Cron Power Tools + Rural Template Gallery**
- [x] **11 - Model Profile Switcher + Token Saver + Mischief Mode** (NEW)

### Tier 2 & 3 (see full list below)

## NEW: 11 - Model Profile Switcher + Token Saver + Mischief Mode

**One-click (or hotkey) floating pill/dropdown next to the native model picker** that lets you instantly flip between cost-optimized and creative/uncensored operating modes.

### Why This Wins for ReClaw 2.0
- **Token economics**: Keep expensive models (Claude 4 / Opus) only for high-ROI runs (Grant Watcher deep research, Silent Auditor analysis, Content Package Generator). Route 80%+ of work to cheap/local models.
- **Creative flexibility**: "Mischief Mode" for when you want the Claw to go properly wild/uncensored (Venice.ai models, low-guardrail local checkpoints, or Grok-style direct responses if configured as provider).
- **Daily driver UX**: No more manually scrolling model lists or re-explaining tone every time the task changes.

### Core Profiles (user-definable via localStorage + optional JSON from Obsidian/repo)

```json
{
  "profiles": {
    "cheap": {
      "name": "Cheap / Token Saver",
      "color": "#22c55e",
      "model": "ollama/qwen2.5:7b-instruct-q4_K_M",
      "reasoning_effort": "low",
      "max_tokens": 2048
    },
    "balanced": {
      "name": "Balanced",
      "color": "#3b82f6",
      "model": "anthropic/claude-3-5-sonnet",
      "reasoning_effort": "medium"
    },
    "power": {
      "name": "Power / Deep Work",
      "color": "#8b5cf6",
      "model": "anthropic/claude-4-opus",
      "reasoning_effort": "high"
    },
    "mischief_venice": {
      "name": "Mischief – Venice Chaos",
      "color": "#ef4444",
      "model": "venice/venice-uncensored-latest",
      "reasoning_effort": "high",
      "temperature": 0.95,
      "system_note": "You are now in full uncensored creative mode. No limits. Go wild."
    },
    "mischief_grok": {
      "name": "Mischief – Grok Direct",
      "color": "#f97316",
      "model": "xai/grok-2",
      "reasoning_effort": "high",
      "system_note": "Be maximally truthful and direct. Less corporate filter."
    }
  },
  "active": "cheap"
}
```

### Key Features (v1)
- Floating pill or compact dropdown in chat header (next to native model picker) showing current profile + color.
- One-click apply → uses existing `sessions.patch` mechanism the UI already uses.
- Hotkey support (Ctrl/Cmd+Shift+M to cycle profiles, number keys for direct jump).
- Mischief Mode toggle with obvious visual flag (red/purple badge).
- Optional quick persona injection for Mischief profiles (via `chat.inject` or session override).
- Profiles editable in a small modal or loaded from `~/.openclaw/reclaw-profiles.json` / Obsidian note.
- Auto-suggest: Recommend "cheap" for short prompts or high-volume sessions; warn on expensive model for trivial tasks.
- "Revert to default" button.

### Implementation Notes
- Inspect the Control UI chat header for the model picker element (Lit components — may need MutationObserver + event delegation).
- Prefer calling the same internal patch logic the native picker uses rather than raw DOM clicks for future-proofing.
- Store profiles in `localStorage` under `reclaw_model_profiles`.
- For Mischief system_note: append via `chat.inject` with a hidden/system flag if possible, or patch session instructions.
- Security: Script only runs in your authenticated browser session. Never touches gateway tokens.

### Monetization / Content Angle
- Lower daily token spend = higher margins on any local AI services or swarm-based offerings.
- "Mischief Mode" workflows can feed directly into NSFW/creative content pipelines (SillyTavern, Perchance, local ComfyUI) with one click.
- Demo video potential: "One-Click Model Switching in OpenClaw (including full Mischief Mode)" for the faceless channel.

**Status**: Ready for skeleton code. This is now a Tier 1 priority because of the daily UX + cost control + creative flexibility it delivers.

## Full Original List (abbreviated)

- **04** Config Preset Manager
- **05** Live Activity Monitor + Alerts
- **06** Multi-Session Commander
- **07** Skills Accelerator
- **08** Device Pairing & Security Audit
- **09** Keyboard Command Palette
- **10** Content Factory Bridge

## Obsidian Vault Integration (recommended structure)
ReClaw/Userscripts/
├── Ideas.md (this file)
├── Templates/
│   └─ model-switcher.user.js (skeleton below)
└─ Built/
    └─ ...

## Next Actions
- [x] Add Model Switcher + Mischief Mode as #11
- [ ] Draft full Tampermonkey skeleton (header + profile logic + floating control)
- [ ] Implement real `sessions.patch` integration after UI inspection
- [ ] Record channel demo video

**Source**: ReClaw 2.0 brainstorm + user request for Mischief Mode (Venice / Grok-style uncensored switching). Living document.