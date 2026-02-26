import requests

_BASE = "https://fantasy.premierleague.com/api"


def get_current_gw() -> int:
    """Return the most recently finished gameweek number."""
    resp = requests.get(f"{_BASE}/bootstrap-static/", timeout=10)
    resp.raise_for_status()
    events = resp.json()["events"]
    finished = [e["id"] for e in events if e.get("finished")]
    if not finished:
        raise ValueError("No finished gameweeks yet this season.")
    return max(finished)


def get_entry_name(team_id: int) -> str:
    """Return the team name for a given FPL entry ID."""
    resp = requests.get(f"{_BASE}/entry/{team_id}/", timeout=10)
    if resp.status_code == 404:
        raise ValueError(f"Team ID {team_id} not found. Double-check your FPL Team ID.")
    resp.raise_for_status()
    return resp.json().get("name", f"Team {team_id}")


def get_entry_picks(team_id: int, gw: int) -> list[int]:
    """Return player element IDs from a team's picks for the given gameweek."""
    resp = requests.get(f"{_BASE}/entry/{team_id}/event/{gw}/picks/", timeout=10)
    if resp.status_code == 404:
        raise ValueError(f"No picks found for Team ID {team_id} in GW {gw}.")
    resp.raise_for_status()
    return [p["element"] for p in resp.json().get("picks", [])]
