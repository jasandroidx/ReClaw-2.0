import sys
import json
import random
import socket
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler

socket.setdefaulttimeout(1.0)

GATEHOUSE_URL = "http://100.111.101.90:8765/alert"
OLLAMA_GENERATE_URL = "http://127.0.0.1:11434/api/generate"

FALLBACK_QUIPS = {
    "raziel": [
        "Routing task vectors through local gateway :18789.",
        "Token burn: 0.00. Sovereign local compute is nominal.",
        "Awaiting next operational directive from the Ravenlord."
    ],
    "clawforge": [
        "Forging FastMCP tools on port :8100.",
        "Docker compose containers running green across the stack.",
        "Hardening systemd daemon bridges."
    ],
    "scribe": [
        "Committing atomic notes to Obsidian vault.",
        "Healing broken wikilinks across /knowledge/.",
        "Formatting incoming transcripts to Oracle standard."
    ],
    "auditor": [
        "Verifying mathematical rigor and dual-receipt provenance.",
        "Scanning audit worklist for anomalous patterns.",
        "Zero policy infractions detected."
    ]
}

def generate_local_chatter(agent: str) -> str:
    prompt = f"You are {agent} in a 16-bit cyber-arcane fortress. Say one brief, witty, in-character sentence (under 12 words) about your current system duties. Output plain text only."
    try:
        data = json.dumps({"model": "phi4-mini", "prompt": prompt, "stream": False}).encode("utf-8")
        req = urllib.request.Request(OLLAMA_GENERATE_URL, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            if resp.status == 200:
                result = json.loads(resp.read().decode("utf-8"))
                return result.get("response", "").strip()
    except Exception:
        pass
    return random.choice(FALLBACK_QUIPS.get(agent, ["Standing by on the fortress line."]))

def send_to_gatehouse(title: str, message: str) -> bool:
    try:
        data = json.dumps({"title": title, "message": message, "play_chime": True}).encode("utf-8")
        req = urllib.request.Request(GATEHOUSE_URL, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            return resp.status == 200
    except Exception:
        return False

class Tier1Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        # /api/chatter?agent=raziel
        if self.path.startswith("/api/chatter"):
            agent = "raziel"
            if "agent=" in self.path:
                agent = self.path.split("agent=")[1].split("&")[0]
            text = generate_local_chatter(agent)
            payload = {"agent": agent, "text": text}
            self.respond_json(payload)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        # /api/corvid/dispatch
        if self.path == "/api/corvid/dispatch":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)
            success = send_to_gatehouse(
                title="Corvid Dispatch: " + data.get("type", "Courier Task"),
                message=data.get("message", "Task routed from Keep")
            )
            self.respond_json({"dispatched": success})
        else:
            self.send_response(404)
            self.end_headers()

    def respond_json(self, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    if "--serve" in sys.argv:
        server = HTTPServer(("127.0.0.1", 8106), Tier1Handler)
        print("Tier 1 Daemon listening on http://127.0.0.1:8106")
        server.serve_forever()
    else:
        # Instant CLI test
        print("Testing local chatter for Raziel:")
        print(generate_local_chatter("raziel"))
