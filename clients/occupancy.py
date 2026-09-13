import os
import requests
from typing import Dict, Any

class OccupancyClient:
    def __init__(self, pulse_url: str = None):
        self.pulse_url = pulse_url or os.environ.get("KEEP_PULSE_URL")

    def get_occupancy(self) -> Dict[str, Any]:
        """
        Get the current occupancy status.
        If KEEP_PULSE_URL is not set, returns a paper state.
        Never invents live agent presence.
        Empty, error, and paper states are explicit.
        """
        if not self.pulse_url:
            return {"status": "paper", "occupants": 0, "message": "KEEP_PULSE_URL not set. Running in paper mode."}

        try:
            response = requests.get(self.pulse_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if "occupants" not in data or not data["occupants"]:
                    return {"status": "empty", "occupants": 0, "message": "No occupants currently present."}
                return {"status": "live", "occupants": data.get("occupants", []), "count": len(data.get("occupants", []))}
            elif response.status_code == 404:
                 return {"status": "empty", "occupants": 0, "message": "Pulse endpoint not found."}
            else:
                return {"status": "error", "occupants": 0, "message": f"Pulse endpoint returned status code {response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "occupants": 0, "message": f"Connection error: {e}"}
