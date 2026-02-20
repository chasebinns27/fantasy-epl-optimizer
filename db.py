import os
import sqlite3

DB_PATH = os.path.join("data", "fpl.db")


def get_conn():
    os.makedirs("data", exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY,
            name TEXT,
            full_name TEXT,
            team TEXT,
            team_id INTEGER,
            position TEXT,
            cost INTEGER,
            avg_points_last_3 REAL,
            avg_fixture_difficulty_next_3 REAL,
            total_points INTEGER,
            minutes INTEGER,
            recent_minutes INTEGER,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def upsert_players(players):
    conn = get_conn()
    conn.executemany("""
        INSERT INTO players (
            id, name, full_name, team, team_id, position, cost,
            avg_points_last_3, avg_fixture_difficulty_next_3,
            total_points, minutes, recent_minutes, updated_at
        )
        VALUES (
            :id, :name, :full_name, :team, :team_id, :position, :cost,
            :avg_points_last_3, :avg_fixture_difficulty_next_3,
            :total_points, :minutes, :recent_minutes, CURRENT_TIMESTAMP
        )
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            full_name = excluded.full_name,
            team = excluded.team,
            team_id = excluded.team_id,
            position = excluded.position,
            cost = excluded.cost,
            avg_points_last_3 = excluded.avg_points_last_3,
            avg_fixture_difficulty_next_3 = excluded.avg_fixture_difficulty_next_3,
            total_points = excluded.total_points,
            minutes = excluded.minutes,
            recent_minutes = excluded.recent_minutes,
            updated_at = CURRENT_TIMESTAMP
    """, players)
    conn.commit()
    conn.close()


def get_all_players():
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM players ORDER BY position, cost DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_players_by_position(position):
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM players WHERE position = ? ORDER BY avg_points_last_3 DESC",
        (position,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_last_updated():
    conn = get_conn()
    row = conn.execute(
        "SELECT MAX(updated_at) as last_updated FROM players"
    ).fetchone()
    conn.close()
    return row[0] if row else None
