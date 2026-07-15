"""
Carga el dataset World Cup a Supabase.
"""

import os
import math
import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

DATA_DIR = "data/processed"
CHUNK_SIZE = 500

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

EXTRA_NA_VALUES = ["not available", "not applicable", "Not available", "Not applicable",
                    "NOT AVAILABLE", "NOT APPLICABLE"]

# columnas válidas por tabla según tu schema propio -> cualquier columna del
# CSV que no esté acá se descarta automáticamente
SCHEMA_COLUMNS = {
    "tournaments": {"tournament_id", "tournament_name", "year", "start_date", "end_date",
                     "host_country", "winner", "host_won", "count_teams", "group_stage",
                     "second_group_stage", "final_round", "round_of_16", "quarter_finals",
                     "semi_finals", "third_place_match", "final"},
    "confederations": {"confederation_id", "confederation_name", "confederation_code"},
    "teams": {"team_id", "team_name", "team_code", "federation_name", "region_name",
              "confederation_id"},
    "players": {"player_id", "family_name", "given_name", "birth_date", "goal_keeper",
                "defender", "midfielder", "forward", "count_tournaments", "list_tournaments"},
    "managers": {"manager_id", "family_name", "given_name", "female", "country_name"},
    "referees": {"referee_id", "family_name", "given_name", "female", "country_name",
                 "confederation_id"},
    "stadiums": {"stadium_id", "stadium_name", "city_name", "country_name", "stadium_capacity"},
    "groups": {"group_id", "tournament_id", "stage_number", "stage_name", "group_name",
               "count_teams"},
    "matches": {"match_id", "tournament_id", "group_id", "match_name", "stage_name",
                "replay", "match_date", "match_time", "stadium_id", "home_team_id",
                "away_team_id", "home_team_score", "away_team_score", "extra_time",
                "penalty_shootout", "home_team_score_penalties", "away_team_score_penalties"},
    "awards": {"award_id", "award_name", "award_description", "year_introduced"},
    "team_performances": {"team_performance_id", "tournament_id", "team_id", "count_matches",
                           "performance"},
    "player_appointments": {"player_appointment_id", "tournament_id", "team_id", "player_id",
                             "shirt_number"},
    "manager_appointments": {"manager_appointment_id", "tournament_id", "team_id", "manager_id"},
    "referee_appointments": {"referee_appointment_id", "tournament_id", "referee_id"},
    "player_appearances": {"player_appearance_id", "match_id", "team_id", "player_id",
                            "starter", "substitute", "shirt_number"},
    "manager_appearances": {"manager_appearance_id", "match_id", "team_id", "manager_id"},
    "referee_appearances": {"referee_appearance_id", "match_id", "referee_id"},
    "goals": {"goal_id", "match_id", "team_id", "player_id", "minute_label",
              "minute_regulation", "minute_stoppage", "match_period", "own_goal", "penalty"},
    "penalty_kicks": {"penalty_kick_id", "match_id", "team_id", "player_id", "converted"},
    "bookings": {"booking_id", "match_id", "team_id", "player_id", "minute_label",
                 "minute_regulation", "minute_stoppage", "match_period", "yellow_card",
                 "red_card", "second_yellow_card", "sending_off"},
    "substitutions": {"substitution_id", "match_id", "team_id", "player_id", "minute_label",
                       "minute_regulation", "minute_stoppage", "match_period", "going_off",
                       "coming_on"},
    "host_countries": {"host_country_id", "tournament_id", "team_id", "performance"},
    "group_standings": {"group_standing_id", "group_id", "position", "team_id", "played",
                         "wins", "draws", "losses", "goals_for", "goals_against",
                         "goal_difference", "points", "advanced"},
    "tournament_standings": {"tournament_standing_id", "tournament_id", "team_id", "position"},
    "award_winners": {"award_winner_id", "tournament_id", "award_id", "shared", "player_id",
                       "team_id"},
    "match_balls": {"ball_id", "tournament_id", "ball_name", "manufacturer"},
}

# columnas INTEGER que pueden tener nulos (FKs opcionales, scores, etc.)
# se castean a Int64 nullable de pandas para no perder el tipo entero
NULLABLE_INT_COLUMNS = {
    "matches": {"home_team_score", "away_team_score",
                "home_team_score_penalties", "away_team_score_penalties"},
    "stadiums": {"stadium_capacity"},
    "tournaments": {"count_teams"},
    "players": {"count_tournaments"},
    "groups": {"stage_number", "count_teams"},
    "player_appointments": {"shirt_number"},
    "player_appearances": {"shirt_number"},
    "goals": {"minute_regulation", "minute_stoppage"},
    "bookings": {"minute_regulation", "minute_stoppage"},
    "substitutions": {"minute_regulation", "minute_stoppage"},
    "team_performances": {"count_matches"},
    "group_standings": {"position", "played", "wins", "draws", "losses", "goals_for",
                         "goals_against", "goal_difference", "points"},
    "tournament_standings": {"position"},
    "awards": {"year_introduced"},
}
TABLES = [
    ("tournaments", "tournament_id", ["start_date", "end_date"]),
    ("confederations", "confederation_id", []),
    ("teams", "team_id", []),
    ("players", "player_id", ["birth_date"]),
    ("managers", "manager_id", []),
    ("referees", "referee_id", []),
    ("stadiums", "stadium_id", []),
    ("groups", "group_id", []),
    ("matches", "match_id", []),
    ("awards", "award_id", []),
    ("match_balls", "ball_id", []),
    ("team_performances", "team_performance_id", []),
    ("player_appointments", "player_appointment_id", []),
    ("manager_appointments", "manager_appointment_id", []),
    ("referee_appointments", "referee_appointment_id", []),
    ("player_appearances", "player_appearance_id", []),
    ("manager_appearances", "manager_appearance_id", []),
    ("referee_appearances", "referee_appearance_id", []),
    ("goals", "goal_id", []),
    ("penalty_kicks", "penalty_kick_id", []),
    ("bookings", "booking_id", []),
    ("substitutions", "substitution_id", []),
    ("host_countries", "host_country_id", []),
    ("group_standings", "group_standing_id", []),
    ("tournament_standings", "tournament_standing_id", []),
    ("award_winners", "award_winner_id", []),
]


# ─────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────

def clean(df: pd.DataFrame) -> list[dict]:
    def to_none(v):
        if v is pd.NA:
            return None
        if isinstance(v, float) and math.isnan(v):
            return None
        return v

    return [
        {k: to_none(v) for k, v in row.items()}
        for row in df.to_dict(orient="records")
    ]


def upsert_chunks(table: str, records: list[dict], on_conflict: str) -> None:
    total = len(records)
    if total == 0:
        print(f"  [{table}] sin registros, salteando")
        return
    for i in range(0, total, CHUNK_SIZE):
        chunk = records[i: i + CHUNK_SIZE]
        supabase.table(table).upsert(chunk, on_conflict=on_conflict).execute()
        pct = min(i + CHUNK_SIZE, total)
        print(f"  [{table}] {pct}/{total}")
    print(f"  [{table}] ✓ {total} registros cargados")


def load_table(table: str, pk: str, date_cols: list[str]) -> None:
    print(f"\n→ {table}")
    csv_path = f"{DATA_DIR}/{table}.csv"
    if not os.path.exists(csv_path):
        print(f"  ⚠️  {csv_path} no encontrado, salteando")
        return

    df = pd.read_csv(csv_path, parse_dates=date_cols if date_cols else None,
                      na_values=EXTRA_NA_VALUES)

    valid_cols = SCHEMA_COLUMNS.get(table)
    if valid_cols is not None:
        extra = set(df.columns) - valid_cols
        missing = valid_cols - set(df.columns)
        if extra:
            print(f"  ℹ️  columnas descartadas: {sorted(extra)}")
        if missing:
            print(f"  ⚠️  columnas del schema ausentes en el CSV: {sorted(missing)}")
        df = df[[c for c in df.columns if c in valid_cols]]

    for col in date_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).replace("NaT", None)

    for col in NULLABLE_INT_COLUMNS.get(table, set()):
        if col in df.columns:
            df[col] = df[col].apply(lambda x: int(x) if pd.notna(x) else None)

    upsert_chunks(table, clean(df), pk)


# ─────────────────────────────────────────────
# main
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Carga World Cup Dataset (schema propio) → Supabase ===")
    for table, pk, date_cols in TABLES:
        load_table(table, pk, date_cols)
    print("\n✓ Carga completa")