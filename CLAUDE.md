# Fantasy EPL Optimizer

## Goal
Identify opportunities to improve my Fantasy Premier League (FPL) lineup by recommending the 5 best available transfers based on player cost, recent form, and upcoming fixture difficulty.

## Tech Stack
- **Language**: Python 3.11+
- **UI**: Streamlit (browser-based)
- **Database**: SQLite (local file: `data/fpl.db`)
- **HTTP**: `requests` library for FPL API calls
- **Dependencies**: managed via `requirements.txt`

## Commands
```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py

# Refresh player data from FPL API
python fetch_data.py
```

## Project Structure
```
fantasy_epl/
├── app.py              # Streamlit UI entrypoint
├── fetch_data.py       # Pulls data from FPL API and writes to SQLite
├── optimizer.py        # Transfer recommendation logic
├── db.py               # SQLite read/write helpers
├── data/
│   └── fpl.db          # SQLite database (gitignored)
├── requirements.txt
└── CLAUDE.md
```

## Data Source — FPL Official API
Base URL: `https://fantasy.premierleague.com/api/`

Key endpoints:
- `bootstrap-static/` — all players, teams, and current gameweek metadata
- `fixtures/` — all fixtures with difficulty ratings (1–5)
- `element-summary/{player_id}/` — per-player history and upcoming fixtures

No authentication required. Fetch fresh data each session via `fetch_data.py`.

## Data Model
Store the following per player in SQLite:

| Field | Description |
|---|---|
| `id` | FPL player ID |
| `name` | Full name |
| `team` | Club name |
| `position` | GKP / DEF / MID / FWD |
| `cost` | Price in tenths of £m (e.g., 65 = £6.5m) |
| `avg_points_last_3` | Average points scored in last 3 gameweeks |
| `avg_fixture_difficulty_next_3` | Average FDR of next 3 fixtures (1=easy, 5=hard) |
| `total_points` | Season total points |
| `minutes` | Total minutes played (filter out non-playing players) |

## FPL Domain Rules
- **Squad**: 15 players — 2 GKP, 5 DEF, 5 MID, 3 FWD (plus subs)
- **Starting XI**: must include valid formation (min 1 GKP, 3 DEF, 2 MID, 1 FWD)
- **Budget**: stored in tenths of £m; display as £X.Xm in the UI
- **Club limit**: max 3 players from the same club
- **Free transfers**: 1 per week; each additional costs 4 points
- **Transfer**: swap 1 player out for 1 player in of same position; budget delta must be ≥ 0

## Transfer Recommendation Logic (`optimizer.py`)
Score each candidate transfer using a weighted formula:

```
transfer_score = (avg_points_last_3 * 0.5)
              + ((6 - avg_fixture_difficulty_next_3) * 0.3)
              + (value_score * 0.2)

value_score = avg_points_last_3 / (cost / 10)
```

Filter candidates by:
1. Same position as the player being replaced
2. Within available budget (current player sale price + remaining budget)
3. Club limit not exceeded after transfer
4. Minimum 45 minutes played in last 3 gameweeks (not injured/benched)

Return top 5 candidates sorted by `transfer_score` descending.

## UI Flow (`app.py`)
1. User selects their 15 current players from a searchable dropdown (filtered by position)
2. User enters available transfer budget (£m)
3. User optionally selects which player(s) they want to transfer out
4. App displays a ranked table of 5 recommended transfers with: player name, club, cost, avg pts (last 3), next 3 fixture difficulty, and transfer score
5. Show a "Refresh Data" button that re-runs `fetch_data.py`

## Conventions
- All costs displayed to user as `£X.Xm` (divide raw value by 10)
- Fixture difficulty displayed as colored indicators: 1–2 = green, 3 = amber, 4–5 = red
- Filter out players with 0 minutes in the last 3 gameweeks from recommendations
- Do not recommend players already in the user's squad
