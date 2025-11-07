import psycopg2
import time
import random
import csv
import os
from datetime import datetime, timedelta
from faker import Faker
import re

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'database': 'data_v',
    'user': 'postgres',      
    'password': '0412',     
    'port': '5432'
}

# Refresh interval in seconds
REFRESH_INTERVAL = 20  

# Log file for generated data
LOG_FILE = 'generated_matches_log.csv'

# CSV export directory and files
EXPORTS_DIR = 'exports'
EXPORT_MATCHES_FILE = os.path.join(EXPORTS_DIR, 'generated_matches.csv')
EXPORT_PERF_FILE = os.path.join(EXPORTS_DIR, 'generated_performance_data.csv')
EXPORT_PLAYER_STATS_FILE = os.path.join(EXPORTS_DIR, 'generated_player_stats.csv')

fake = Faker()

def get_db_connection():
    """Create database connection"""
    return psycopg2.connect(**DB_CONFIG)

def ensure_exports_dir():
    """Ensure the exports directory exists"""
    try:
        os.makedirs(EXPORTS_DIR, exist_ok=True)
    except Exception:
        pass

def append_row_to_csv(file_path, header, row_values):
    """Append a row to CSV, writing header if file is new"""
    file_exists = os.path.isfile(file_path)
    with open(file_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(header)
        writer.writerow(row_values)

def log_generated_match(match_id, team1, team2, score, map_name, match_date, records_count):
    """Log generated match to CSV file for tracking"""
    file_exists = os.path.isfile(LOG_FILE)
    
    with open(LOG_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Write header if file is new
        if not file_exists:
            writer.writerow([
                'timestamp', 'match_id', 'team1', 'team2', 
                'score', 'map', 'match_date', 'player_records'
            ])
        
        # Write match data
        writer.writerow([
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            match_id, team1, team2, score, map_name, 
            match_date, records_count
        ])

def get_existing_data(conn):
    """Get existing players, teams, agents, and maps from database"""
    cursor = conn.cursor()
    
    # Get all players with their teams
    cursor.execute("""
        SELECT player_name, player_id, team 
        FROM player_stats 
        WHERE team IS NOT NULL
        ORDER BY team, player_name
    """)
    all_players = cursor.fetchall()
    
    # Group players by team
    team_players_dict = {}
    for player_name, player_id, team in all_players:
        if team not in team_players_dict:
            team_players_dict[team] = []
        team_players_dict[team].append((player_name, player_id, team))
    
    # Get real agents
    cursor.execute("SELECT DISTINCT agent_name FROM agents_stats")
    agents = [row[0] for row in cursor.fetchall()]
    
    # Get real maps
    cursor.execute("SELECT DISTINCT map_name FROM maps_stats")
    maps = [row[0] for row in cursor.fetchall()]
    
    # Get recent match IDs to continue the sequence (ensure integer)
    cursor.execute("SELECT MAX(match_id) FROM matches")
    raw_max_match_id = cursor.fetchone()[0]
    if raw_max_match_id is None:
        max_match_id = 0
    else:
        try:
            max_match_id = int(raw_max_match_id)
        except (ValueError, TypeError):
            # In case the DB column is TEXT and contains non-numeric prefix, extract trailing digits
            match = re.search(r"(\d+)$", str(raw_max_match_id))
            max_match_id = int(match.group(1)) if match else 0
    
    cursor.close()
    return team_players_dict, agents, maps, max_match_id

def generate_realistic_performance_data(match_id, map_name, player_name, team, agent):
    """Generate realistic performance statistics"""
    # Realistic kill distributions
    kills_2k = random.randint(0, 5)
    kills_3k = random.randint(0, 3)
    kills_4k = random.randint(0, 2)
    kills_5k = random.randint(0, 1)
    
    # Clutch situations (less common)
    clutch_1v1 = random.randint(0, 2)
    clutch_1v2 = random.randint(0, 1)
    clutch_1v3 = random.randint(0, 1)
    clutch_1v4 = 1 if random.random() > 0.9 else 0
    clutch_1v5 = 1 if random.random() > 0.95 else 0
    
    # Economy and objectives
    econ = random.randint(3500, 5000)  # Changed to integer to match database schema
    plants = random.randint(0, 5)
    defuses = random.randint(0, 3)
    
    return (match_id, map_name, player_name, team, agent,
            kills_2k, kills_3k, kills_4k, kills_5k,
            clutch_1v1, clutch_1v2, clutch_1v3, clutch_1v4, clutch_1v5,
            econ, plants, defuses)

def generate_detailed_player_stats(match_id, event_name, event_stage, match_date,
                                   team1, team2, score_overall, player_name, 
                                   player_id, player_team, agent, map_name, map_winner):
    """Generate realistic detailed player statistics"""
    # Core combat stats
    kills = random.randint(10, 30)
    deaths = random.randint(8, 25)
    assists = random.randint(2, 12)
    
    # Calculated stats
    kd_diff = kills - deaths
    rating = round(random.uniform(0.7, 1.3), 2)  # DECIMAL(3,2) - kept as float
    acs = random.randint(150, 350)  # Changed to integer to match database schema
    kast = random.randint(55, 85)   # Changed to integer to match database schema
    adr = random.randint(100, 200)  # Changed to integer to match database schema
    hs_percent = random.randint(15, 35)  # Changed to integer to match database schema
    
    # First kills/deaths
    fk = random.randint(0, 8)
    fd = random.randint(0, 8)
    fk_fd_diff = fk - fd
    
    return (match_id, event_name, event_stage, match_date,
            team1, team2, score_overall, player_name, player_id, player_team,
            'map', agent, rating, acs, kills, deaths, assists, kd_diff,
            kast, adr, hs_percent, fk, fd, fk_fd_diff, map_name, map_winner)

def insert_new_match_data(conn, team_players_dict, agents, maps, current_match_id):
    """Insert new match performance data"""
    cursor = conn.cursor()
    
    try:
        # Validate we have enough data
        if not maps:
            print("✗ No maps found in database")
            cursor.close()
            return current_match_id
        
        if not agents:
            print("✗ No agents found in database")
            cursor.close()
            return current_match_id
        
        # Filter teams that have at least 5 players
        valid_teams = [team for team, players_list in team_players_dict.items() if len(players_list) >= 5]
        
        if len(valid_teams) < 2:
            print(f"✗ Not enough teams with 5+ players (need at least 2 teams, have {len(valid_teams)})")
            cursor.close()
            return current_match_id
        
        # Generate a new match with DEMO prefix to distinguish from real data
        new_match_id = current_match_id + 1
        match_date = datetime.now().date()
        
        # Select two different teams that have enough players
        team1_name, team2_name = random.sample(valid_teams, 2)
        
        # Get 5 players from each team (respecting their actual team assignments)
        team1_players = random.sample(team_players_dict[team1_name], 5)
        team2_players = random.sample(team_players_dict[team2_name], 5)
        
        # Random score
        score1 = random.randint(0, 2)
        score2 = 2 if score1 < 2 else random.randint(0, 1)
        winner = team1_name if score1 > score2 else team2_name
        
        # Insert match
        cursor.execute("""
            INSERT INTO matches 
            (date, match_id, time, team1, score1, team2, score2, score, winner, status, week, stage)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (match_id) DO NOTHING
        """, (match_date, new_match_id, '20:00', team1_name, score1, 
              team2_name, score2, f"{score1}-{score2}", winner, 
              'Completed', 'Week 4', 'Group Stage'))
        # Export match row to CSV
        append_row_to_csv(
            EXPORT_MATCHES_FILE,
            ['date', 'match_id', 'time', 'team1', 'score1', 'team2', 'score2', 'score', 'winner', 'status', 'week', 'stage'],
            [match_date, new_match_id, '20:00', team1_name, score1, team2_name, score2, f"{score1}-{score2}", winner, 'Completed', 'Week 4', 'Group Stage']
        )
        
        # Select a map
        map_name = random.choice(maps)
        map_winner = winner
        
        records_inserted = 0
        
        # Insert performance data for both teams
        for team_players, team_name in [(team1_players, team1_name), 
                                        (team2_players, team2_name)]:
            for player_name, player_id, _ in team_players:
                agent = random.choice(agents)
                
                # Insert performance data
                perf_data = generate_realistic_performance_data(
                    new_match_id, map_name, player_name, team_name, agent
                )
                
                cursor.execute("""
                    INSERT INTO performance_data 
                    ("Match ID", "Map", "Player", "Team", "Agent",
                     "2K", "3K", "4K", "5K",
                     "1v1", "1v2", "1v3", "1v4", "1v5",
                     "ECON", "PL", "DE")
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, perf_data)
                # Export performance row to CSV
                append_row_to_csv(
                    EXPORT_PERF_FILE,
                    [
                        'Match ID', 'Map', 'Player', 'Team', 'Agent',
                        '2K', '3K', '4K', '5K',
                        '1v1', '1v2', '1v3', '1v4', '1v5',
                        'ECON', 'PL', 'DE'
                    ],
                    list(perf_data)
                )
                
                # Insert detailed player stats
                detailed_stats = generate_detailed_player_stats(
                    new_match_id, 'Valorant Champions 2024', 'Group Stage',
                    match_date, team1_name, team2_name, f"{score1}-{score2}",
                    player_name, player_id, team_name, agent, map_name, map_winner
                )
                
                cursor.execute("""
                    INSERT INTO detailed_matches_player_stats 
                    (match_id, event_name, event_stage, match_date,
                     team1, team2, score_overall, player_name, player_id, player_team,
                     stat_type, agent, rating, acs, k, d, a, kd_diff,
                     kast, adr, hs_percent, fk, fd, fk_fd_diff, map_name, map_winner)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, detailed_stats)
                # Export detailed player stats row to CSV
                append_row_to_csv(
                    EXPORT_PLAYER_STATS_FILE,
                    [
                        'match_id', 'event_name', 'event_stage', 'match_date',
                        'team1', 'team2', 'score_overall', 'player_name', 'player_id', 'player_team',
                        'stat_type', 'agent', 'rating', 'acs', 'k', 'd', 'a', 'kd_diff',
                        'kast', 'adr', 'hs_percent', 'fk', 'fd', 'fk_fd_diff', 'map_name', 'map_winner'
                    ],
                    list(detailed_stats)
                )
                
                records_inserted += 1
        
        conn.commit()
        
        # Log the generated match
        log_generated_match(
            new_match_id, team1_name, team2_name, 
            f"{score1}-{score2}", map_name, match_date, records_inserted
        )
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}]  Inserted Match #{str(new_match_id)}: {team1_name} vs {team2_name} ({score1}-{score2})")
        print(f"  → {str(records_inserted)} player records added (Map: {map_name})")
        print(f"  → Logged to {LOG_FILE}")
        
        cursor.close()
        return new_match_id
        
    except Exception as e:
        conn.rollback()
        print(f"✗ Error inserting data: {e}")
        cursor.close()
        return current_match_id

def main():
    """Main function to run auto-refresh"""
    print("=" * 60)
    print("Valorant Champions 2024 - Auto Data Refresh Script")
    print("=" * 60)
    print(f"Refresh Interval: {REFRESH_INTERVAL} seconds")
    print(f"Database: {DB_CONFIG['database']} @ {DB_CONFIG['host']}")
    print("=" * 60)
    
    try:
        ensure_exports_dir()
        # Test connection
        conn = get_db_connection()
        print(" Database connection successful")
        
        # Get existing data
        team_players_dict, agents, maps, current_match_id = get_existing_data(conn)
        
        # Count total players and teams
        total_players = sum(len(players) for players in team_players_dict.values())
        valid_teams = [team for team, players in team_players_dict.items() if len(players) >= 5]
        
        print(f" Loaded {total_players} players from {len(team_players_dict)} teams")
        print(f" Teams with 5+ players: {len(valid_teams)}")
        print(f" Loaded {len(agents)} agents, {len(maps)} maps")
        print(f" Starting from Match ID: {str(current_match_id + 1)}")
        print("=" * 60)
        print("\nStarting auto-refresh loop... (Press Ctrl+C to stop)\n")
        
        iteration = 1
        while True:
            print(f"\n--- Iteration #{str(iteration)} ---")
            current_match_id = insert_new_match_data(
                conn, team_players_dict, agents, maps, current_match_id
            )
            
            print(f"Next refresh in {REFRESH_INTERVAL} seconds...\n")
            time.sleep(REFRESH_INTERVAL)
            iteration += 1
            
    except KeyboardInterrupt:
        print("\n\n Auto-refresh stopped by user")
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()
            print("Database connection closed")

if __name__ == "__main__":
    main()