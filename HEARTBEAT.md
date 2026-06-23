---
summary: "Workspace template for HEARTBEAT.md"
title: "HEARTBEAT.md template"
read_when:
  - Bootstrapping a workspace manually
---

# ReClaw engine (companion at /opt/reclaw)
# - curl -f http://${RECLAW_GATEWAY_HOST:-host.docker.internal}:8000/health   (host.docker.internal from inside OpenClaw container; 127.0.0.1 from bare host shell)
# - consider the rural demo (tools/reclaw-rural-demo) for primary counties when due
# Keep this file mostly empty to skip heartbeat API calls. Add short tasks only when needed for periodic checks (small instructions for recurring wakes).
