"""
Import Team Headquarters data and clean up legacy geo data

This script:
- Drops legacy geo tables created by previous geo imports
- Ensures a `teams` dimension table and populates it from existing data
- Ensures `team_headquarters` with FK to `teams(team_name)`
- Imports `exports/teams_headquarters.csv` (team, latitude, longitude), or auto-generates it if missing
"""

import os
import unicodedata
from datetime import datetime

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values


TEAM_HEADQUARTERS = {
    # Americas
    "SEN": {
        "full_name": "Sentinels",
        "city": "Los Angeles",
        "country": "United States",
        "lat": 34.0522,
        "lng": -118.2437
    },
    "LEV": {
        "full_name": "Leviatán",
        "city": "Buenos Aires",
        "country": "Argentina",
        "lat": -34.6037,
        "lng": -58.3816
    },
    "KRÜ": {
        "full_name": "KRÜ Esports",
        "city": "Buenos Aires",  # Costa Rica 6019, Buenos Aires
        "country": "Argentina",
        "lat": -34.6037,
        "lng": -58.3816
    },
    "G2": {
        "full_name": "G2 Esports",
        "city": "Berlin",
        "country": "Germany",
        "lat": 52.5200,
        "lng": 13.4050
    },
    
    # EMEA
    "TH": {
        "full_name": "Team Heretics",
        "city": "Barcelona",
        "country": "Spain",
        "lat": 41.3851,
        "lng": 2.1734
    },
    "FNC": {
        "full_name": "Fnatic",
        "city": "London",
        "country": "United Kingdom",
        "lat": 51.5074,
        "lng": -0.1278
    },
    "VIT": {
        "full_name": "Team Vitality",
        "city": "Paris",
        "country": "France",
        "lat": 48.8566,
        "lng": 2.3522
    },
    "FUT": {
        "full_name": "FUT Esports",
        "city": "Istanbul",  # Besiktas, Istanbul
        "country": "Turkey",
        "lat": 41.0082,
        "lng": 28.9784
    },
    
    # Pacific
    "GEN": {
        "full_name": "Gen.G",
        "city": "Seoul",
        "country": "South Korea",
        "lat": 37.5665,
        "lng": 126.9780
    },
    "PRX": {
        "full_name": "Paper Rex",
        "city": "Singapore",
        "country": "Singapore",
        "lat": 1.3521,
        "lng": 103.8198
    },
    "DRX": {
        "full_name": "DRX",
        "city": "Seoul",
        "country": "South Korea",
        "lat": 37.5665,
        "lng": 126.9780
    },
    "TLN": {
        "full_name": "Talon Esports",
        "city": "Bangkok",
        "country": "Thailand",
        "lat": 13.7563,
        "lng": 100.5018
    },
    
    # China
    "EDG": {
        "full_name": "EDward Gaming",
        "city": "Shanghai",
        "country": "China",
        "lat": 31.2304,
        "lng": 121.4737
    },
    "FPX": {
        "full_name": "FunPlus Phoenix",
        "city": "Shanghai",
        "country": "China",
        "lat": 31.2304,
        "lng": 121.4737
    },
    "BLG": {
        "full_name": "Bilibili Gaming",
        "city": "Shanghai",
        "country": "China",
        "lat": 31.2304,
        "lng": 121.4737
    },
    "TE": {
        "full_name": "Trace Esports",
        "city": "Chengdu",
        "country": "China",
        "lat": 30.5728,
        "lng": 104.0668
    }
}


def connect_to_database():
    """Connect to PostgreSQL database"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="data_v",
            user="postgres",
            password="0412",
        )
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None


def drop_old_geo_tables(conn):
    """Drop legacy geo tables if they exist."""
    print("Dropping legacy geo tables if they exist...")
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            DROP TABLE IF EXISTS
                team_geo_performance,
                regional_heatmap,
                player_geo_data,
                tournament_venues,
                map_performance_geo,
                geo_scatter_data
            CASCADE;
            """
        )
        conn.commit()
        print("✓ Dropped legacy geo tables (if any)")
    except Exception as e:
        conn.rollback()
        print(f"❌ Error dropping legacy geo tables: {e}")
    finally:
        cursor.close()


def ensure_teams_table(conn):
    """Create teams dimension table if it does not exist."""
    print("Ensuring teams table exists...")
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS teams (
                team_name VARCHAR(255) PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.commit()
        print("✓ Ensured teams table exists")
    except Exception as e:
        conn.rollback()
        print(f"❌ Error ensuring teams table: {e}")
    finally:
        cursor.close()


def populate_teams_from_existing(conn):
    """Populate teams table from existing schema sources."""
    print("Populating teams table from existing data...")
    cursor = conn.cursor()
    try:
        team_names = set()

        # Collect teams from various tables; many identifiers are quoted in schema
        sources = [
            ("SELECT DISTINCT team1 AS team FROM \"matches\" WHERE team1 IS NOT NULL", []),
            ("SELECT DISTINCT team2 AS team FROM \"matches\" WHERE team2 IS NOT NULL", []),
            ("SELECT DISTINCT \"winner\" AS team FROM \"matches\" WHERE \"winner\" IS NOT NULL", []),
            ("SELECT DISTINCT team AS team FROM \"player_stats\" WHERE team IS NOT NULL", []),
            ("SELECT DISTINCT \"Team\" AS team FROM \"performance_data\" WHERE \"Team\" IS NOT NULL", []),
            ("SELECT DISTINCT \"Team\" AS team FROM \"economy_data\" WHERE \"Team\" IS NOT NULL", []),
            ("SELECT DISTINCT player_team AS team FROM \"detailed_matches_player_stats\" WHERE player_team IS NOT NULL", []),
            ("SELECT DISTINCT team1 AS team FROM \"detailed_matches_player_stats\" WHERE team1 IS NOT NULL", []),
            ("SELECT DISTINCT team2 AS team FROM \"detailed_matches_player_stats\" WHERE team2 IS NOT NULL", []),
            ("SELECT DISTINCT map_winner AS team FROM \"detailed_matches_player_stats\" WHERE map_winner IS NOT NULL", []),
            ("SELECT DISTINCT \"winner\" AS team FROM \"detailed_matches_maps\" WHERE \"winner\" IS NOT NULL", []),
        ]

        for sql, params in sources:
            try:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                for (name,) in rows:
                    if name and isinstance(name, str):
                        cleaned = name.strip()
                        if cleaned:
                            team_names.add(cleaned)
            except Exception:
                # If some tables are missing in a given environment, skip gracefully
                conn.rollback()
                cursor = conn.cursor()
                continue

        if not team_names:
            print("⚠️  Warning: No teams discovered from existing data")

        rows = [(t,) for t in sorted(team_names)]
        if rows:
            insert_sql = (
                "INSERT INTO teams (team_name) VALUES %s ON CONFLICT (team_name) DO NOTHING"
            )
            execute_values(cursor, insert_sql, rows, template="(%s)")
            conn.commit()
        print(f"✓ Teams discovered/inserted: {len(rows)}")
    except Exception as e:
        conn.rollback()
        print(f"❌ Error populating teams table: {e}")
    finally:
        cursor.close()


def ensure_team_headquarters_table(conn):
    """Create team_headquarters table and ensure FK to teams."""
    print("Ensuring team_headquarters table and FK exist...")
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS team_headquarters (
                team VARCHAR(255) PRIMARY KEY,
                latitude DECIMAL(10, 6) NOT NULL,
                longitude DECIMAL(10, 6) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.commit()

        # Add FK if missing
        cursor.execute(
            """
            SELECT 1 FROM pg_constraint
            WHERE conname = 'fk_team_headquarters_team'
        """
        )
        exists = cursor.fetchone() is not None
        if not exists:
            try:
                cursor.execute(
                    """
                    ALTER TABLE team_headquarters
                    ADD CONSTRAINT fk_team_headquarters_team
                    FOREIGN KEY (team)
                    REFERENCES teams (team_name)
                    ON UPDATE CASCADE
                    ON DELETE RESTRICT;
                    """
                )
                conn.commit()
                print("✓ Added FK team_headquarters.team -> teams.team_name")
            except Exception as fk_e:
                conn.rollback()
                print(f"⚠️  Warning: Unable to add FK (may already exist or data mismatch): {fk_e}")

        print("✓ Ensured team_headquarters table exists")
    except Exception as e:
        conn.rollback()
        print(f"❌ Error ensuring team_headquarters table: {e}")
    finally:
        cursor.close()


def import_team_headquarters(conn, csv_path: str):
    """Import team headquarters data from CSV.

    Expected columns: team, latitude, longitude
    """
    print(f"Importing {csv_path} into team_headquarters...")

    if not os.path.exists(csv_path):
        print(f"⚠️  Warning: File {csv_path} not found")
        return

    try:
        df = pd.read_csv(csv_path)

        required_cols = ["team", "latitude", "longitude"]
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns in CSV: {missing_cols}")

        # Clean data: drop rows without team or coordinates, coerce coords to numeric
        df["team"] = df["team"].astype(str).str.strip()
        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
        df = df.dropna(subset=["team", "latitude", "longitude"]).copy()

        # Ensure teams exist to satisfy FK
        team_rows = [(t,) for t in df["team"].dropna().astype(str).str.strip().unique()]

        cursor = conn.cursor()
        if team_rows:
            execute_values(
                cursor,
                "INSERT INTO teams (team_name) VALUES %s ON CONFLICT (team_name) DO NOTHING",
                team_rows,
                template="(%s)",
            )

        # Prepare tuples
        rows = [
            (row["team"], float(row["latitude"]), float(row["longitude"]))
            for _, row in df.iterrows()
        ]


        # Upsert so repeated imports refresh coordinates
        insert_sql = (
            "INSERT INTO team_headquarters (team, latitude, longitude) VALUES %s "
            "ON CONFLICT (team) DO UPDATE SET "
            "latitude = EXCLUDED.latitude, "
            "longitude = EXCLUDED.longitude, "
            "updated_at = CURRENT_TIMESTAMP"
        )

        execute_values(cursor, insert_sql, rows, template="(%s,%s,%s)")
        conn.commit()
        print(f"✓ Imported/updated {len(rows)} team headquarters records")
    except Exception as e:
        conn.rollback()
        print(f"❌ Error importing team headquarters: {e}")
    finally:
        try:
            cursor.close()
        except Exception:
            pass


def _normalize_name(value: str) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = ''.join(ch for ch in unicodedata.normalize('NFKD', text) if not unicodedata.combining(ch))
    return text


def generate_headquarters_csv(conn, csv_path: str):
    """Generate a headquarters CSV from discovered teams using TEAM_HEADQUARTERS mapping."""
    print("Generating headquarters CSV from teams using TEAM_HEADQUARTERS mapping...")
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT team_name FROM teams ORDER BY team_name")
        teams = [row[0] for row in cursor.fetchall()]
        cursor.close()

        if not teams:
            print("⚠️  Warning: No teams in teams table; nothing to generate")
            return False
        
        # Build mappings from TEAM_HEADQUARTERS
        full_name_to_coords = {}
        code_to_coords = {}
        for code, meta in TEAM_HEADQUARTERS.items():
            try:
                lat = float(meta.get("lat"))
                lng = float(meta.get("lng"))
            except Exception:
                continue
            code_to_coords[_normalize_name(code)] = (lat, lng)
            full_name = str(meta.get("full_name", "")).strip()
            if full_name:
                full_name_to_coords[_normalize_name(full_name)] = (lat, lng)

        rows = []
        missing = []
        for t in teams:
            key = _normalize_name(t)
            coords = full_name_to_coords.get(key)
            if coords is None:
                coords = code_to_coords.get(key)
            if coords is None:
                missing.append(t)
                continue
            lat, lng = coords
            rows.append({"team": t, "latitude": lat, "longitude": lng})

        if not rows:
            print("⚠️  Warning: No matching teams found in mapping; CSV not generated")
            return False

        df = pd.DataFrame(rows, columns=["team", "latitude", "longitude"])
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        df.to_csv(csv_path, index=False)
        print(f"✓ Wrote generated headquarters CSV: {csv_path} ({len(df)} mapped teams)")
        if missing:
            print(f"⚠️  Teams without mapping: {len(missing)} (e.g., {missing[:5]})")
        return True
    except Exception as e:
        print(f"❌ Error generating headquarters CSV: {e}")
        return False


def main():
    print("Starting Team Headquarters import...")

    conn = connect_to_database()
    if not conn:
        print(" Failed to connect to database")
        return

    try:
        # Remove legacy data structures
        drop_old_geo_tables(conn)

        # Ensure dimension and populate
        ensure_teams_table(conn)
        populate_teams_from_existing(conn)

        # Ensure new target table with FK
        ensure_team_headquarters_table(conn)

        # Import headquarters or generate if missing
        csv_path = "exports/teams_headquarters.csv"
        if not os.path.exists(csv_path):
            generated = generate_headquarters_csv(conn, csv_path)
            if not generated:
                print(" Skipping import: unable to generate headquarters CSV")
            else:
                import_team_headquarters(conn, csv_path)
        else:
            import_team_headquarters(conn, csv_path)

        # Smoke test
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM team_headquarters")
        count = cursor.fetchone()[0]
        print(f"✓ team_headquarters rows: {count}")
        cursor.close()

        print("\nTeam Headquarters import complete.")
        print("Next: Verify coordinates in your BI tool or quick SQL queries.")
    except Exception as e:
        print(f"❌ Error during import: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    main()


