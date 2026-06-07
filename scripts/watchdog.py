#!/usr/bin/env python3
import time
import subprocess
import requests
import os
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BOSS_HEALTH_URL = "http://127.0.0.1:18789/health/boss"
CHECK_INTERVAL = 60
ALERT_WEBHOOK = os.getenv("ALERT_WEBHOOK", "https://your-webhook.example.com")  # Set in .env for Telegram/Discord mobile alerts

def check_boss():
    """Ping Boss health endpoint."""
    try:
        r = requests.get(BOSS_HEALTH_URL, timeout=5)
        return r.status_code == 200
    except Exception as e:
        logger.warning(f"Boss health check failed: {e}")
        return False

def pause_all_cells():
    """Touch pause flag for dashboard to detect and grayscale sprites."""
    pause_file = Path("/root/.openclaw/workspace/SYSTEM_PAUSED")
    pause_file.touch()
    logger.info("SYSTEM_PAUSED flag set. All cells paused.")

def send_alert(message: str):
    """Send alert via webhook (Telegram/Discord)."""
    try:
        requests.post(ALERT_WEBHOOK, json={"content": message}, timeout=10)
        logger.info("Alert sent.")
    except Exception as e:
        logger.error(f"Alert failed: {e}")

if __name__ == "__main__":
    logger.info("Boss Agent Watchdog started (interval=%s s). *CLANG*", CHECK_INTERVAL)
    while True:
        if not check_boss():
            pause_all_cells()
            send_alert("ReClaw Boss Agent is offline. All cells paused. Check the Hetzner box. SYSTEM_PAUSED flag set.")
        time.sleep(CHECK_INTERVAL)
