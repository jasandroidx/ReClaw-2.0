import sys
import json
import socket
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler

# Hard socket timeout so remote network checks never hang
socket.setdefaulttimeout(0.5)

OLLAMA_HOSTS = {
    "hetzner": "http://127.0.0.1:11434",
    "gatehouse": "http://100.111.101.90:11434"
}

def check_ollama():
    active_inferences = []
    for node, base_url in OLLAMA_HOSTS.items():
        try:
            req = urllib.request.Request(
                f"{base_url}/api/ps", 
                headers={"User-Agent": "RavenstackReactor/1.0"}
            )
            with urllib.request.urlopen(req, timeout=0.5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    for m in data.get("models", []):
                        active_inferences.append({
                            "node": node,
                            "model": m.get("name"),
                            "size_vram": m.get("size_vram", 0)
                        })
        except Exception:
            pass

    is_generating = len(active_inferences) > 0
    return {
        "status": "forging" if is_generating else "idle",
        "color": "#ff2a6d" if is_generating else "#2de2e6",
        "active_models": active_inferences
    }

class ReactorHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/reactor/state" or self.path == "/":
            payload = check_ollama()
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    if "--serve" in sys.argv:
        server = HTTPServer(("127.0.0.1", 8105), ReactorHandler)
        server.serve_forever()
    else:
        # Instant CLI test mode — returns JSON and exits to shell
        print(json.dumps(check_ollama(), indent=2))
