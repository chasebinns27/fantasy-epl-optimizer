from db import get_all_players

MAX_PER_CLUB = 3


def transfer_score(player):
    cost_in_millions = player["cost"] / 10
    value_score = (
        player["avg_points_last_3"] / cost_in_millions
        if cost_in_millions > 0 else 0
    )
    return (
        player["avg_points_last_3"] * 0.5
        + (6 - player["avg_fixture_difficulty_next_3"]) * 0.3
        + value_score * 0.2
    )


def club_counts(squad):
    """Returns {team_id: count} for current squad."""
    counts = {}
    for p in squad:
        counts[p["team_id"]] = counts.get(p["team_id"], 0) + 1
    return counts


def recommend_transfers(squad, player_out, extra_budget_tenths):
    """
    squad               : list of player dicts (the user's full 15)
    player_out          : the player dict being transferred out
    extra_budget_tenths : additional funds available (in tenths of £m)

    Returns up to 5 recommended replacements, sorted by transfer_score desc.
    """
    available_budget = player_out["cost"] + extra_budget_tenths

    squad_ids = {p["id"] for p in squad}
    remaining_squad = [p for p in squad if p["id"] != player_out["id"]]
    clubs = club_counts(remaining_squad)

    all_players = get_all_players()

    candidates = []
    for p in all_players:
        if p["id"] in squad_ids:
            continue
        if p["position"] != player_out["position"]:
            continue
        if p["cost"] > available_budget:
            continue
        if clubs.get(p["team_id"], 0) >= MAX_PER_CLUB:
            continue
        if p["recent_minutes"] == 0:
            continue

        p["transfer_score"] = round(transfer_score(p), 3)
        candidates.append(p)

    candidates.sort(key=lambda p: p["transfer_score"], reverse=True)
    return candidates[:5]


def recommend_all_transfers(squad, extra_budget_tenths=0):
    """
    Evaluate every possible single transfer across the squad.
    For each squad player, find their best available replacement, then rank
    all moves by the net improvement in transfer_score.

    Returns up to 5 dicts with keys: player_out, player_in, improvement.
    """
    moves = []
    for player_out in squad:
        candidates = recommend_transfers(squad, player_out, extra_budget_tenths)
        if not candidates:
            continue
        best_in = candidates[0]
        current_score = round(transfer_score(player_out), 3)
        improvement = round(best_in["transfer_score"] - current_score, 3)
        moves.append({
            "player_out": player_out,
            "player_in": best_in,
            "current_score": current_score,
            "improvement": improvement,
        })

    moves.sort(key=lambda m: m["improvement"], reverse=True)
    return moves[:5]
