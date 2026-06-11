# 🗺️ The "Clawsmith" Master Roadmap
**Objective:** Transition from a static visual shell to a persistent, revenue-generating agent operation.

---

## 🚦 Current Status: Phase 1 (The "Wake Up")
**Current state:** Visual Dashboard is live (Port 8085), but Agent Cells are not yet deployed. We have the "theater," but the "actors" haven't arrived.

---

## Phase 1: The "Wake Up" (Plumbing & Connectivity)
*Before adding more agents, we must ensure the existing visual shell can actually communicate with the backend logic.*

- [ ] **Event Bus Activation:** Verify the `ws://127.0.0.1:18789` (or designated port) is active and the Dashboard is successfully listening for events.
- [ ] **Cell Deployment:** Run `clawsmith.py` to generate the actual physical directories for the agents (e.g., `~/.openclaw/workspace/rooms/grant_hall/`).
- [ ] **The "Soul" Injector:** Create the `SOUL.md` and `AGENTS.md` files for the primary agents so they have personalities and instructions.
- [ ] **Visual Handshake:** Trigger a "Hello World" event from a cell to the dashboard to confirm the sprite changes from `zzz...` to `typing...`.

## Phase 2: The "Expansion" (Populating the Floor)
*Filling the room with the specialist roster defined in Session 1.*

- [ ] **Deploy the Specialist Roster:**
    - [ ] **Purple Grant Watcher:** (Central Hub / Grant alerts).
    - [ ] **Red Silent Auditor:** (High-ticket reporting).
    - [ ] **Green Job Aggregator:** (Lead list generation).
    - [ ] **Orange Marketplace Flipper:** (Feed monitoring).
- [ ] **Desk Anchoring:** Map each agent's ID to their specific coordinate on the 2.5D isometric map.
- [ ] **Memory Initialization:** Setup the `memory.db` (ReClaw) for each cell to ensure they remember what they did across restarts.

## Phase 3: The "Economy" (Passive Income & Loops)
*Turning the agents from "chatbots" into "workers" who generate value.*

- [ ] **Loop Configuration:** Set up the `cron` jobs or internal loops that trigger the agents to search for grants/jobs/leads.
- [ ] **Revenue Triggers:** Implement the logic in `SOUL.md` that identifies a "payable" event (e.g., finding a $49/mo grant alert).
- [ ] **Vault Integration:** Ensure all "wins" are written to `/root/obsidian_vault` so the user can review money-making opportunities.
- [ ] **Dashboard HUD Update:** Connect the "Funding Tracker" on the dashboard to the actual count of leads/grants found.

## Phase 4: The "Fortress" (Reliability & Oversight)
*Ensuring the system remains stable and autonomous.*

- [ ] **Watchdog Deployment:** Activate `watchdog.py` to ping the Boss agent every 60s.
- [ ] **The "Death" Protocol:** Configure the dashboard to grayscale if the Watchdog detects a crash.
- [ ] **Auto-Recovery:** Set up the system to automatically restart the `http.server` and Agent cells on boot.
- [ ] **Failure Theater:** Create a log in the vault for "Agent Failures" to audit why loops broke.

## Phase 5: The "High Value" (RaterHub & New Verticals)
*Applying the stable operation to professional high-value work.*

- [ ] **Browser Automation Layer:** Build the safe "Assistant" flow for RaterHub/SxS rating tasks.
- [ ] **Screen-Shot Analysis:** Use the vision model to analyze rating pages and suggest quality scores.
- [ ] **New Room Design:** Use Clawsmith to architect a specific "Rating Room" on the dashboard for this specific vertical.

---

**Created:** 2026-06-11
**Version:** 1.0 (Initial Roadmap)
