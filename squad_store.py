import json
import os

SQUAD_FILE = os.path.join("data", "my_squad.json")


def save_squad(squad):
    """Persist squad player IDs grouped by position."""
    data = {}
    for p in squad:
        data.setdefault(p["position"], []).append(p["id"])
    os.makedirs("data", exist_ok=True)
    with open(SQUAD_FILE, "w") as f:
        json.dump(data, f)


def load_squad_ids():
    """Returns {position: [id, ...]} or empty dict if no saved squad."""
    if not os.path.exists(SQUAD_FILE):
        return {}
    with open(SQUAD_FILE) as f:
        return json.load(f)
