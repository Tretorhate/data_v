#!/usr/bin/env python3

import psycopg2
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

# Database connection parameters
DB_CONFIG = {
    'host': 'localhost',
    'database': 'data_v',
    'user': 'postgres',
    'password': '0412',
    'port': '5432'
}

def connect_to_db():
    """Establish database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def add_demo_player(conn):
    """Add a demo player to the database for demonstration"""
    try:
        cursor = conn.cursor()
        demo_player_query = """
        INSERT INTO player_stats (
            player_id, player, player_name, team, agents_count, agents,
            rounds, rating, acs, kd_ratio, kast, adr, kpr, apr, fkpr, fdpr,
            hs_percent, cl_percent, clutches, k_max, kills, deaths, assists,
            first_kills, first_deaths
        ) VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s
        )
        """
        demo_player_id = f"demo_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        params = (
            demo_player_id, 'demo_player', 'Demo Player', 'DEMO', 2, '["Jett", "Raze"]',
            150, 1.35, 280, 1.45, 75, 180, 0.95, 0.20, 0.20, 0.15,
            30, 20, '5/25', 30, 145, 100, 60,
            30, 20
        )
        cursor.execute(demo_player_query, params)
        conn.commit()
        print("  Added demo player to database")
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error adding demo player: {e}")
        return False

def remove_demo_player(conn):
    """Remove the demo player from the database"""
    try:
        # Ensure we are not in a failed transaction state
        try:
            conn.rollback()
        except Exception:
            pass
        cursor = conn.cursor()
        cursor.execute("DELETE FROM player_stats WHERE player_name = 'Demo Player'")
        conn.commit()
        print("  Removed demo player from database")
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error removing demo player: {e}")
        return False

def create_demo_scatter_plot(conn, title_suffix=""):
    """Create scatter plot: ACS vs Rating correlation with team colors"""
    query = """
    SELECT 
        ps.player_name,
        ps.team,
        ps.acs,
        ps.rating,
        ps.kd_ratio,
        ps.rounds
    FROM player_stats ps
    WHERE ps.rounds > 100
    ORDER BY ps.rating DESC
    """
    
    df = pd.read_sql_query(query, conn)
    if df is None or df.empty:
        return 0, "no_file"
    
    # Create scatter plot
    plt.figure(figsize=(14, 10))
    
    # Get unique teams and assign colors
    teams = df['team'].unique()
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', 
              '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9', 
              '#F8C471', '#82E0AA', '#F1948A', '#85C1E9', '#D7BDE2']
    team_colors = dict(zip(teams, colors[:len(teams)]))
    
    # Create scatter plot with team colors
    for team in teams:
        team_data = df[df['team'] == team]
        plt.scatter(team_data['acs'], team_data['rating'], 
                   c=team_colors[team], label=team, alpha=0.7, s=100, edgecolors='black', linewidth=0.5)
    
    plt.xlabel('Average Combat Score (ACS)', fontsize=12, fontweight='bold')
    plt.ylabel('Rating', fontsize=12, fontweight='bold')
    plt.title(f'ACS vs Rating Correlation by Team{title_suffix}\n(Valorant Champions 2024)', 
              fontsize=16, fontweight='bold', pad=20)
    
    # Add trend line
    z = np.polyfit(df['acs'], df['rating'], 1)
    p = np.poly1d(z)
    plt.plot(df['acs'], p(df['acs']), "r--", alpha=0.8, linewidth=2, label='Trend Line')
    
    # Add correlation coefficient
    correlation = df['acs'].corr(df['rating'])
    plt.text(0.05, 0.95, f'Correlation: {correlation:.3f}', 
             transform=plt.gca().transAxes, fontsize=12, 
             bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
    
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    # Highlight demo player if present
    if 'Demo Player' in df['player_name'].values:
        demo_data = df[df['player_name'] == 'Demo Player']
        print(f"  Found Demo Player in chart data: rows={len(demo_data)}, acs={float(demo_data['acs'].values[0]):.2f}, rating={float(demo_data['rating'].values[0]):.2f}")
        plt.scatter(demo_data['acs'], demo_data['rating'],
                   c='red', s=260, marker='*', edgecolors='black', linewidth=2,
                   label='Demo Player (NEW)', zorder=10)
        # Annotate for visibility
        plt.annotate('Demo Player',
                     (float(demo_data['acs'].values[0]), float(demo_data['rating'].values[0])),
                     xytext=(8, 8), textcoords='offset points', color='red', fontsize=11, weight='bold', zorder=11)
    else:
        print("  Demo Player NOT found in chart dataset")

    # Save with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f'charts/demo_scatter_plot_{timestamp}.png'
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"[OK] Scatter Plot: ACS vs Rating correlation - {len(df)} players")
    print(f"  Saved as: {filename}")
    return len(df), filename

def demonstrate_chart_regeneration():
    """Demonstrate adding demo data and regenerating chart (before/after)"""
    print("DEMONSTRATION: Chart Regeneration with Demo Player")
    print("=" * 60)
    
    conn = connect_to_db()
    if not conn:
        return
    
    try:
        # Step 1: Create initial chart
        print("\nStep 1: Creating initial scatter plot...")
        initial_count, initial_file = create_demo_scatter_plot(conn, " (BEFORE)")
        
        # Step 2: Add new data
        print("\nStep 2: Adding Demo Player to database...")
        if add_demo_player(conn):
            # Step 3: Regenerate chart (after)
            print("\nStep 3: Regenerating scatter plot with new data...")
            new_count, new_file = create_demo_scatter_plot(conn, " (AFTER)")
        
            # Step 4: Show comparison
            print(f"\nStep 4: Comparison Results:")
            print(f"  - Initial chart: {initial_count} players")
            print(f"  - Updated chart: {new_count} players")
            print(f"  - Initial file: {initial_file}")
            print(f"  - Updated file: {new_file}")
        
        # Step 5: Clean up
        print("\nStep 5: Cleaning up demo data...")
        remove_demo_player(conn)
        
        print(f"\n{'='*60}")
        print("DEMONSTRATION COMPLETE!")
        print("[OK] Successfully demonstrated chart regeneration concept")
        print("[OK] Charts show how data updates would affect visualizations")
        print("[OK] This demonstrates the dynamic nature of our system")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"Error during demonstration: {e}")
    
    finally:
        conn.close()
        print("\nDatabase connection closed.")

if __name__ == "__main__":
    demonstrate_chart_regeneration()
