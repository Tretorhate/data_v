import psycopg2
import csv
import os

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'database': 'data_v',
    'user': 'postgres',      
    'password': '0412',     
    'port': '5432'
}

# Log file path (same as in refresh_data.py)
LOG_FILE = 'generated_matches_log.csv'

def cleanup_generated_data():
    """Clean up auto-generated match data"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    print("=" * 60)
    print("Cleanup Generated Match Data")
    print("=" * 60)
    
    try:
        # Show current data statistics
        cursor.execute("SELECT COUNT(*), MIN(match_id), MAX(match_id) FROM matches")
        total_matches, min_id, max_id = cursor.fetchone()
        print(f"\nCurrent Statistics:")
        print(f"  Total Matches: {total_matches}")
        print(f"  Match ID Range: {min_id} to {max_id}")
        
        # Ask user for the starting match_id to delete
        print(f"\n⚠️  WARNING: This will delete all matches >= the specified ID")
        start_id = input(f"\nEnter the starting match_id to delete from (or 'cancel' to abort): ")
        
        if start_id.lower() == 'cancel':
            print("Cleanup cancelled.")
            return
        
        try:
            start_id = int(start_id)
        except ValueError:
            print("Invalid match ID. Cleanup cancelled.")
            return
        
        # Count what will be deleted
        cursor.execute("""
            SELECT COUNT(*) FROM matches WHERE match_id >= %s
        """, (start_id,))
        matches_to_delete = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM performance_data WHERE "Match ID" >= %s
        """, (start_id,))
        perf_to_delete = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM detailed_matches_player_stats WHERE match_id >= %s
        """, (start_id,))
        stats_to_delete = cursor.fetchone()[0]
        
        print(f"\nRecords to be deleted:")
        print(f"  Matches: {matches_to_delete}")
        print(f"  Performance Data: {perf_to_delete}")
        print(f"  Player Stats: {stats_to_delete}")
        
        confirm = input(f"\nAre you sure you want to delete these records? (yes/no): ")
        
        if confirm.lower() != 'yes':
            print("Cleanup cancelled.")
            return
        
        # Delete the data
        print("\nDeleting data...")
        
        cursor.execute("""
            DELETE FROM detailed_matches_player_stats WHERE match_id >= %s
        """, (start_id,))
        print(f"   Deleted {cursor.rowcount} player stats records")
        
        cursor.execute("""
            DELETE FROM performance_data WHERE "Match ID" >= %s
        """, (start_id,))
        print(f"   Deleted {cursor.rowcount} performance records")
        
        cursor.execute("""
            DELETE FROM matches WHERE match_id >= %s
        """, (start_id,))
        print(f"   Deleted {cursor.rowcount} match records")
        
        conn.commit()
        print("\n Cleanup completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n✗ Error during cleanup: {e}")
    finally:
        cursor.close()
        conn.close()

def cleanup_by_date():
    """Clean up matches by date (useful for deleting today's generated data)"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    print("=" * 60)
    print("Cleanup Generated Data by Date")
    print("=" * 60)
    
    try:
        # Show dates with match counts
        cursor.execute("""
            SELECT date, COUNT(*) as count 
            FROM matches 
            GROUP BY date 
            ORDER BY date DESC 
            LIMIT 10
        """)
        
        print("\nRecent match dates:")
        for date, count in cursor.fetchall():
            print(f"  {date}: {count} matches")
        
        delete_date = input(f"\nEnter date to delete (YYYY-MM-DD) or 'cancel': ")
        
        if delete_date.lower() == 'cancel':
            print("Cleanup cancelled.")
            return
        
        # Count what will be deleted
        cursor.execute("""
            SELECT match_id FROM matches WHERE date = %s
        """, (delete_date,))
        match_ids = [row[0] for row in cursor.fetchall()]
        
        if not match_ids:
            print(f"No matches found for date {delete_date}")
            return
        
        print(f"\nFound {len(match_ids)} matches to delete for {delete_date}")
        print(f"Match IDs: {match_ids}")
        
        confirm = input(f"\nAre you sure? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cleanup cancelled.")
            return
        
        # Delete the data
        print("\nDeleting data...")
        
        cursor.execute("""
            DELETE FROM detailed_matches_player_stats WHERE match_id = ANY(%s)
        """, (match_ids,))
        print(f"   Deleted {cursor.rowcount} player stats records")
        
        cursor.execute("""
            DELETE FROM performance_data WHERE "Match ID" = ANY(%s)
        """, (match_ids,))
        print(f"   Deleted {cursor.rowcount} performance records")
        
        cursor.execute("""
            DELETE FROM matches WHERE match_id = ANY(%s)
        """, (match_ids,))
        print(f"   Deleted {cursor.rowcount} match records")
        
        conn.commit()
        print("\n Cleanup completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n✗ Error during cleanup: {e}")
    finally:
        cursor.close()
        conn.close()

def cleanup_from_log():
    """Clean up matches using the generated_matches_log.csv file"""
    if not os.path.exists(LOG_FILE):
        print(f"✗ Log file not found: {LOG_FILE}")
        print("  This file is created when refresh_data.py generates matches.")
        return
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    print("=" * 60)
    print("Cleanup Generated Data from Log File")
    print("=" * 60)
    
    try:
        # Read the log file
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            logged_matches = list(reader)
        
        if not logged_matches:
            print("\n✗ No matches found in log file.")
            return
        
        print(f"\nFound {len(logged_matches)} generated matches in log file:\n")
        
        # Display all logged matches
        print(f"{'#':<4} {'Match ID':<10} {'Teams':<40} {'Score':<8} {'Date':<12} {'Timestamp':<20}")
        print("-" * 110)
        
        for idx, match in enumerate(logged_matches, 1):
            teams = f"{match['team1']} vs {match['team2']}"
            print(f"{idx:<4} {match['match_id']:<10} {teams:<40} {match['score']:<8} {match['match_date']:<12} {match['timestamp']:<20}")
        
        # Get list of match IDs as text (we'll compare via ::text to avoid type issues)
        match_ids_text = [match['match_id'] for match in logged_matches]
        
        print(f"\n{'='*60}")
        print("Cleanup Options:")
        print("1. Delete ALL matches from log file")
        print("2. Delete specific match IDs")
        print("3. Delete matches from a date range")
        print("4. Cancel")
        
        choice = input("\nEnter choice (1-4): ")
        
        if choice == "1":
            # Delete all
            ids_to_delete_text = match_ids_text
        elif choice == "2":
            # Delete specific IDs
            ids_input = input("\nEnter match IDs to delete (comma-separated): ")
            try:
                ids_parsed = [x.strip() for x in ids_input.split(',') if x.strip()]
                # Use string membership against log (robust regardless of column type)
                ids_to_delete_text = [x for x in ids_parsed if x in match_ids_text]
            except ValueError:
                print("Invalid input. Cleanup cancelled.")
                return
        elif choice == "3":
            # Delete by date range
            start_date = input("Enter start date (YYYY-MM-DD) or press Enter for earliest: ").strip()
            end_date = input("Enter end date (YYYY-MM-DD) or press Enter for latest: ").strip()
            
            ids_to_delete_text = []
            for match in logged_matches:
                match_date = match['match_date']
                if (not start_date or match_date >= start_date) and \
                   (not end_date or match_date <= end_date):
                    ids_to_delete_text.append(match['match_id'])
        else:
            print("Cleanup cancelled.")
            return
        
        if not ids_to_delete_text:
            print("No matches selected. Cleanup cancelled.")
            return
        
        # Count what will be deleted
        cursor.execute("""
            SELECT COUNT(*) FROM matches WHERE match_id::text = ANY(%s)
        """, (ids_to_delete_text,))
        matches_to_delete = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM performance_data WHERE "Match ID"::text = ANY(%s)
        """, (ids_to_delete_text,))
        perf_to_delete = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM detailed_matches_player_stats WHERE match_id::text = ANY(%s)
        """, (ids_to_delete_text,))
        stats_to_delete = cursor.fetchone()[0]
        
        print(f"\nRecords to be deleted:")
        try:
            ids_preview = sorted(ids_to_delete_text, key=lambda x: (len(x), x))
        except Exception:
            ids_preview = ids_to_delete_text
        print(f"  Match IDs: {ids_preview}")
        print(f"  Matches: {matches_to_delete}")
        print(f"  Performance Data: {perf_to_delete}")
        print(f"  Player Stats: {stats_to_delete}")
        
        confirm = input(f"\n  Are you sure you want to delete these records? (yes/no): ")
        
        if confirm.lower() != 'yes':
            print("Cleanup cancelled.")
            return
        
        # Delete the data
        print("\nDeleting data from database...")
        
        cursor.execute("""
            DELETE FROM detailed_matches_player_stats WHERE match_id::text = ANY(%s)
        """, (ids_to_delete_text,))
        print(f"   Deleted {cursor.rowcount} player stats records")
        
        cursor.execute("""
            DELETE FROM performance_data WHERE "Match ID"::text = ANY(%s)
        """, (ids_to_delete_text,))
        print(f"   Deleted {cursor.rowcount} performance records")
        
        cursor.execute("""
            DELETE FROM matches WHERE match_id::text = ANY(%s)
        """, (ids_to_delete_text,))
        print(f"   Deleted {cursor.rowcount} match records")
        
        conn.commit()
        
        # Remove deleted matches from log file
        remove_from_log = input(f"\nRemove deleted matches from {LOG_FILE}? (yes/no): ")
        if remove_from_log.lower() == 'yes':
            remaining_matches = [m for m in logged_matches if m['match_id'] not in ids_to_delete_text]
            
            with open(LOG_FILE, 'w', newline='', encoding='utf-8') as f:
                if remaining_matches:
                    writer = csv.DictWriter(f, fieldnames=remaining_matches[0].keys())
                    writer.writeheader()
                    writer.writerows(remaining_matches)
                else:
                    # Write empty file with just headers
                    writer = csv.writer(f)
                    writer.writerow(['timestamp', 'match_id', 'team1', 'team2', 
                                   'score', 'map', 'match_date', 'player_records'])
            
            print(f"   Updated {LOG_FILE} ({len(remaining_matches)} matches remaining)")
        
        print("\n Cleanup completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n✗ Error during cleanup: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    print("\nSelect cleanup method:")
    print("1. Delete using log file (RECOMMENDED)")
    print("2. Delete by Match ID range")
    print("3. Delete by date")
    choice = input("\nEnter choice (1-3): ")
    
    if choice == "1":
        cleanup_from_log()
    elif choice == "2":
        cleanup_generated_data()
    elif choice == "3":
        cleanup_by_date()
    else:
        print("Invalid choice.")

