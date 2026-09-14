import os, subprocess, datetime

vault = "/root/obsidian_vault/Ravenstack/ops/audits"
os.makedirs(vault, exist_ok=True)
today = datetime.date.today().isoformat()
report = f"{vault}/Weekly-Audit-{today}.md"

lessons = open("/root/ReClaw-2.0/data/auditor_lessons_log.yaml").read() if os.path.exists("/root/ReClaw-2.0/data/auditor_lessons_log.yaml") else "None recorded."
ps = subprocess.getoutput("cd /root/ReClaw-2.0 && docker compose ps")
gw = subprocess.getoutput("cd /root/ReClaw-2.0 && docker compose logs --no-follow --tail=50 openclaw-gateway 2>&1 | tail -n 8")

with open(report, "w") as f:
    f.write(f"# Raziel Weekly Audit ({today})\n\n## 1. Lessons Ledger\n```yaml\n{lessons}\n```\n\n## 2. Gateway Logs\n```text\n{gw}\n```\n\n## 3. Stack Status\n```text\n{ps}\n```\n")

print(f"[SUCCESS] Audit generated: {report}")
