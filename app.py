import subprocess
import sys

import streamlit as st

from db import get_all_players, get_last_updated
from optimizer import recommend_transfers, recommend_all_transfers
from squad_store import save_squad, load_squad_ids

POSITIONS = ["GKP", "DEF", "MID", "FWD"]
POSITION_COUNTS = {"GKP": 2, "DEF": 5, "MID": 5, "FWD": 3}

FDR_COLOR = {1: "🟢", 2: "🟢", 3: "🟡", 4: "🔴", 5: "🔴"}


def fdr_label(fdr):
    icon = FDR_COLOR.get(round(fdr), "⚪")
    return f"{icon} {fdr:.1f}"


def cost_label(cost_tenths):
    return f"£{cost_tenths / 10:.1f}m"


def run_fetch():
    result = subprocess.run(
        [sys.executable, "fetch_data.py"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        st.success("Data refreshed successfully.")
    else:
        st.error(f"Fetch failed:\n{result.stderr}")


def build_player_options(players, position):
    filtered = [p for p in players if p["position"] == position]
    filtered.sort(key=lambda p: p["name"])
    return {f"{p['name']} ({p['team']}, {cost_label(p['cost'])})": p for p in filtered}


def render_transfer_table(rows):
    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Score": st.column_config.NumberColumn(format="%.3f"),
            "Avg Pts (last 3)": st.column_config.NumberColumn(format="%.2f"),
            "Improvement": st.column_config.NumberColumn(format="%+.3f"),
        },
    )


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="FPL Transfer Optimizer", page_icon="⚽", layout="wide")
st.title("⚽ FPL Transfer Optimizer")

# ── Sidebar: data status + refresh + budget ───────────────────────────────────
with st.sidebar:
    st.header("Data")
    last_updated = get_last_updated()
    if last_updated:
        st.caption(f"Last updated: {last_updated[:16]}")
    else:
        st.caption("No data yet.")

    if st.button("🔄 Refresh Data from FPL API"):
        with st.spinner("Fetching latest data..."):
            run_fetch()
        st.rerun()

    st.divider()
    st.header("Budget")
    extra_budget = st.number_input(
        "Extra funds available (£m)",
        min_value=0.0, max_value=20.0, value=0.0, step=0.1,
        help="Money in the bank beyond what selling your transfer-out player raises."
    )

# ── Load players + saved squad ────────────────────────────────────────────────
all_players = get_all_players()
if not all_players:
    st.warning("No player data found. Click **Refresh Data** in the sidebar to fetch it.")
    st.stop()

id_to_player = {p["id"]: p for p in all_players}
saved_ids = load_squad_ids()  # {position: [id, ...]}

# ── Squad selection ───────────────────────────────────────────────────────────
st.header("Your Squad")
st.caption("Select all 15 players. Your selection is saved automatically.")

squad = []
selection_complete = True

cols = st.columns(4)
for col, pos in zip(cols, POSITIONS):
    with col:
        st.subheader(pos)
        options = build_player_options(all_players, pos)
        required = POSITION_COUNTS[pos]

        # Restore saved labels that still exist in the current options
        saved_labels = [
            label for pid in saved_ids.get(pos, [])
            if pid in id_to_player
            for label, p in options.items()
            if p["id"] == pid
        ]

        selected_labels = st.multiselect(
            f"Select {required} {pos}(s)",
            options=list(options.keys()),
            default=saved_labels,
            max_selections=required,
            key=f"squad_{pos}",
            label_visibility="collapsed",
        )
        for label in selected_labels:
            squad.append(options[label])
        if len(selected_labels) < required:
            selection_complete = False

# Save squad whenever it is complete
if selection_complete:
    save_squad(squad)

st.divider()

if not squad:
    st.info("Select your squad above to continue.")
    st.stop()

extra_tenths = int(extra_budget * 10)

# ── Section 1: Best transfers across whole squad ──────────────────────────────
st.header("Best Available Transfers")
st.caption("The 5 moves with the biggest improvement in transfer score across your whole squad.")

if st.button("Find Best Transfers (Auto)", type="primary"):
    if not selection_complete:
        st.warning("Please complete your full 15-player squad first.")
    else:
        moves = recommend_all_transfers(squad, extra_tenths)
        if not moves:
            st.info("No eligible transfers found. Try increasing your budget.")
        else:
            rows = []
            for i, m in enumerate(moves, start=1):
                p_out = m["player_out"]
                p_in = m["player_in"]
                rows.append({
                    "Rank": i,
                    "Transfer Out": f"{p_out['name']} ({p_out['team']})",
                    "Transfer In": p_in["name"],
                    "Club (In)": p_in["team"],
                    "Cost (In)": cost_label(p_in["cost"]),
                    "Avg Pts (last 3)": p_in["avg_points_last_3"],
                    "Next 3 FDR": fdr_label(p_in["avg_fixture_difficulty_next_3"]),
                    "Score": p_in["transfer_score"],
                    "Improvement": m["improvement"],
                })
            render_transfer_table(rows)
            st.caption(
                "Improvement = incoming player's score − outgoing player's score. "
                "Score = (avg pts × 0.5) + ((6 − FDR) × 0.3) + (pts/cost × 0.2)."
            )

st.divider()

# ── Section 2: Transfer out a specific player ─────────────────────────────────
st.header("Transfer Out a Specific Player")

squad_options = {
    f"{p['name']} ({p['position']}, {p['team']}, {cost_label(p['cost'])})": p
    for p in sorted(squad, key=lambda p: p["position"])
}
transfer_out_label = st.selectbox(
    "Which player do you want to transfer out?",
    options=list(squad_options.keys()),
)
player_out = squad_options[transfer_out_label]

st.caption(
    f"Selling **{player_out['name']}** raises **{cost_label(player_out['cost'])}**. "
    f"Total budget for replacement: **{cost_label(player_out['cost'] + extra_tenths)}**"
)

if st.button("Find Transfers for This Player", type="secondary"):
    if not selection_complete:
        st.warning("Please complete your full 15-player squad first.")
    else:
        recommendations = recommend_transfers(squad, player_out, extra_tenths)
        if not recommendations:
            st.info("No eligible transfers found. Try increasing your budget or checking squad data.")
        else:
            rows = []
            for i, p in enumerate(recommendations, start=1):
                rows.append({
                    "Rank": i,
                    "Player": p["name"],
                    "Club": p["team"],
                    "Cost": cost_label(p["cost"]),
                    "Avg Pts (last 3)": p["avg_points_last_3"],
                    "Next 3 FDR": fdr_label(p["avg_fixture_difficulty_next_3"]),
                    "Score": p["transfer_score"],
                })
            render_transfer_table(rows)
            st.caption(
                "Score = (avg pts × 0.5) + ((6 − FDR) × 0.3) + (pts/cost × 0.2). "
                "Filters: same position, within budget, ≤3 players per club, played recently."
            )
