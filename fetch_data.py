import sys
import requests
from db import init_db, upsert_players

BASE_URL = "https://fantasy.premierleague.com/api/"

POSITION_MAP = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}


def fetch(endpoint):
    url = BASE_URL + endpoint
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


def get_last_3_finished_gws(events):
    finished = [e["id"] for e in events if e["finished"]]
    return finished[-3:]


def build_gw_points(gw_ids):
    """Returns {player_id: [{"points": int, "minutes": int}, ...]} for each finished GW."""
    gw_points = {}
    for gw in gw_ids:
        print(f"  Fetching GW{gw} live data...")
        try:
            data = fetch(f"event/{gw}/live/")
            for element in data["elements"]:
                pid = element["id"]
                stats = element["stats"]
                gw_points.setdefault(pid, []).append({
                    "points": stats["total_points"],
                    "minutes": stats["minutes"],
                })
        except requests.RequestException as e:
            print(f"  Warning: could not fetch GW{gw} — {e}", file=sys.stderr)
    return gw_points


def build_team_fdr(fixtures):
    """Returns {team_id: [fdr, fdr, fdr]} for each team's next 3 upcoming fixtures."""
    upcoming = [
        f for f in fixtures
        if not f["finished"] and f.get("event") is not None
    ]
    upcoming.sort(key=lambda f: f["event"])

    team_fdr = {}
    for fixture in upcoming:
        home_id = fixture["team_h"]
        away_id = fixture["team_a"]
        home_fdr = fixture["team_h_difficulty"]
        away_fdr = fixture["team_a_difficulty"]

        home_list = team_fdr.setdefault(home_id, [])
        away_list = team_fdr.setdefault(away_id, [])

        if len(home_list) < 3:
            home_list.append(home_fdr)
        if len(away_list) < 3:
            away_list.append(away_fdr)

    return team_fdr


def build_player_records(players_raw, team_map, gw_points, team_fdr):
    records = []
    for p in players_raw:
        pid = p["id"]
        history = gw_points.get(pid, [])

        avg_points = (
            sum(h["points"] for h in history) / len(history)
            if history else 0.0
        )
        recent_minutes = sum(h["minutes"] for h in history)

        fdr_list = team_fdr.get(p["team"], [])
        avg_fdr = sum(fdr_list) / len(fdr_list) if fdr_list else 3.0

        records.append({
            "id": pid,
            "name": p["web_name"],
            "full_name": f"{p['first_name']} {p['second_name']}",
            "team": team_map.get(p["team"], "Unknown"),
            "team_id": p["team"],
            "position": POSITION_MAP.get(p["element_type"], "UNK"),
            "cost": p["now_cost"],
            "avg_points_last_3": round(avg_points, 2),
            "avg_fixture_difficulty_next_3": round(avg_fdr, 2),
            "total_points": p["total_points"],
            "minutes": p["minutes"],
            "recent_minutes": recent_minutes,
        })
    return records


def main():
    print("Initialising database...")
    init_db()

    print("Fetching bootstrap data...")
    bootstrap = fetch("bootstrap-static/")
    players_raw = bootstrap["elements"]
    teams_raw = bootstrap["teams"]
    events = bootstrap["events"]

    team_map = {t["id"]: t["name"] for t in teams_raw}

    last_3_gws = get_last_3_finished_gws(events)
    if not last_3_gws:
        print("No finished gameweeks found — cannot calculate recent form.")
        sys.exit(1)
    print(f"Using gameweeks: {last_3_gws}")

    gw_points = build_gw_points(last_3_gws)

    print("Fetching fixtures...")
    fixtures = fetch("fixtures/")
    team_fdr = build_team_fdr(fixtures)

    print("Building player records...")
    records = build_player_records(players_raw, team_map, gw_points, team_fdr)

    print(f"Writing {len(records)} players to database...")
    upsert_players(records)

    print("Done. Data is up to date.")


if __name__ == "__main__":
    main()
