#!/usr/bin/env python3

import psycopg2
import pandas as pd

# Db connection parameters
DB_CONFIG = {
    'host': 'localhost',
    'database': 'data_v',
    'user': 'postgres',
    'password': '0412',
    'port': '5432'
}

def connect_to_db():
    """Establish db connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Error connecting to db: {e}")
        return None

def execute_query(conn, query, description):
    """Execute a query and display results in a formatted table"""
    try:
        print(f"\n{'='*60}")
        print(f"QUERY: {description}")
        print(f"{'='*60}")
        
        df = pd.read_sql_query(query, conn)
        
        if df.empty:
            print("No results found.")
            return
        
        # Display results in a nice table format
        print(df.to_string(index=False))
        print(f"\nRows returned: {len(df)}")
        
    except Exception as e:
        print(f"Error executing query: {e}")

def execute_sql_file(conn, file_path):
    """Execute all SQL commands from a file and display results."""
    try:
        with open(file_path, 'r') as file:
            sql_commands = file.read()
        
        with conn.cursor() as cursor:
            queries = sql_commands.split(';')  
            for query in queries:
                query = query.strip()
                if query:  
                    print(f"\nExecuting query: {query[:50]}...")  
                    cursor.execute(query)
                    conn.commit()

             
                    if cursor.description:  
                        columns = [desc[0] for desc in cursor.description]
                        rows = cursor.fetchall()
                        df = pd.DataFrame(rows, columns=columns)
                        print(df.to_string(index=False))
                    else:
                        print("Query executed successfully, no results to display.")

            print(f"\nSuccessfully executed all queries in file: {file_path}")
    except Exception as e:
        print(f"Error executing SQL file {file_path}: {e}")

def main():
    """Main function to run all analysis queries"""
    print("VALORANT CHAMPIONS 2024 DATA ANALYSIS")
    print("="*50)
    
    conn = connect_to_db()
    if not conn:
        return
    
    try:
        # Execute queries.sql file
        execute_sql_file(conn, 'queries.sql')
        
        # 1. Basic Data Exploration
        print("\n1. BASIC DATA EXPLORATION")
        print("-" * 30)
        
        # Check table structures
        execute_query(conn, 
            "SELECT * FROM player_stats LIMIT 5", 
            "Player Stats Sample")
        
        execute_query(conn, 
            "SELECT * FROM matches LIMIT 5", 
            "Matches Sample")
        
        # 2. Filtering, Aggregation, and Sorting
        print("\n2. FILTERING, AGGREGATION, AND SORTING")
        print("-" * 40)
        
        execute_query(conn, """
            SELECT 
                player_name, 
                team, 
                rating, 
                acs, 
                kd_ratio, 
                rounds
            FROM player_stats 
            WHERE rounds > 100 
            ORDER BY rating DESC 
            LIMIT 10
        """, "Top Players by Rating")
        
        execute_query(conn, """
            SELECT 
                team,
                COUNT(*) as player_count,
                ROUND(AVG(rating), 2) as avg_rating,
                ROUND(AVG(acs), 2) as avg_acs,
                ROUND(MIN(rating), 2) as min_rating,
                ROUND(MAX(rating), 2) as max_rating
            FROM player_stats 
            GROUP BY team 
            ORDER BY avg_rating DESC
        """, "Team Stats")
        
        # 3. JOIN Operations
        print("\n3. JOIN OPERATIONS")
        print("-" * 20)
        
        execute_query(conn, """
            SELECT 
                ps.player_name,
                ps.team,
                ps.rating as overall_rating,
                dmps.rating as match_rating,
                dmps.acs as match_acs,
                dmps.map_name
            FROM player_stats ps
            INNER JOIN detailed_matches_player_stats dmps 
                ON ps.player_id = dmps.player_id
            WHERE dmps.stat_type = 'map'
            ORDER BY ps.rating DESC
            LIMIT 10
        """, "Players with Match Stats")
        
        execute_query(conn, """
            SELECT 
                ag.agent_name,
                ag.total_utilization,
                COUNT(dmps.player_id) as times_picked,
                ROUND(AVG(dmps.rating), 2) as avg_rating_when_picked
            FROM agents_stats ag
            LEFT JOIN detailed_matches_player_stats dmps 
                ON ag.agent_name = dmps.agent
            GROUP BY ag.agent_name, ag.total_utilization
            ORDER BY ag.total_utilization DESC
            LIMIT 10
        """, "Agent Performance")
        
        # 4. Analytical Topics
        print("\n4. ANALYTICAL TOPICS")
        print("-" * 20)
        
        execute_query(conn, """
            SELECT 
                map_name,
                times_played,
                attack_win_percent,
                defense_win_percent,
                CASE 
                    WHEN attack_win_percent > defense_win_percent THEN 'Attack Favored'
                    WHEN defense_win_percent > attack_win_percent THEN 'Defense Favored'
                    ELSE 'Balanced'
                END as map_balance
            FROM maps_stats 
            ORDER BY times_played DESC
        """, "Map Balance")
        
        execute_query(conn, """
            SELECT 
                player_name,
                team,
                hs_percent,
                rating,
                acs,
                kills,
                deaths
            FROM player_stats 
            WHERE hs_percent IS NOT NULL
            ORDER BY hs_percent DESC
            LIMIT 10
        """, "Best Headshots")
        
        execute_query(conn, """
            SELECT 
                player_name,
                team,
                first_kills,
                first_deaths,
                (first_kills - first_deaths) as fk_fd_diff,
                CAST((first_kills::float / NULLIF(first_kills + first_deaths, 0)) * 100 AS DECIMAL(5,2)) as fk_percentage,
                rating
            FROM player_stats 
            WHERE first_kills > 0 OR first_deaths > 0
            ORDER BY fk_fd_diff DESC
            LIMIT 10
        """, "First Kill Impact")
        
        execute_query(conn, """
            SELECT 
                'Total Matches' as metric,
                COUNT(*)::text as value
            FROM matches
            UNION ALL
            SELECT 
                'Total Players',
                COUNT(DISTINCT player_id)::text
            FROM player_stats
            UNION ALL
            SELECT 
                'Total Maps Played',
                COUNT(DISTINCT map_name)::text
            FROM maps_stats
            UNION ALL
            SELECT 
                'Average Player Rating',
                ROUND(AVG(rating), 2)::text
            FROM player_stats
        """, "Tournament Stats")
        
        print(f"\n{'='*60}")
        print("ANALYSIS COMPLETE!")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"Error during analysis: {e}")
    
    finally:
        conn.close()
        print("\nDb connection closed.")

if __name__ == "__main__":
    main()
