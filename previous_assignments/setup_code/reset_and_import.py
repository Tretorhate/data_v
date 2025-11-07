import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def reset_db():
    """Clear all data from db and re-import"""
    
    # Db connection parameters
    DB_CONFIG = {
        'host': 'localhost',
        'database': 'data_v',
        'user': 'postgres',
        'password': '0412',
        'port': '5432'
    }
    
    try:
        # Connect to db
        conn = psycopg2.connect(**DB_CONFIG)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("Clearing existing data...")
        
        # Disable foreign key checks temporarily
        cursor.execute("SET session_replication_role = replica;")
        
        # Clear all tables in reverse dependency order
        tables_to_clear = [
            'detailed_matches_player_stats',
            'detailed_matches_maps', 
            'detailed_matches_overview',
            'performance_data',
            'economy_data',
            'agents_stats',
            'maps_stats',
            'player_stats',
            'matches',
            'event_info'
        ]
        
        for table in tables_to_clear:
            try:
                cursor.execute(f"TRUNCATE TABLE {table} CASCADE;")
                print(f"  - Cleared {table}")
            except Exception as e:
                print(f"  - Warning: Could not clear {table}: {e}")
        
        # Re-enable foreign key checks
        cursor.execute("SET session_replication_role = DEFAULT;")
        
        cursor.close()
        conn.close()
        
        print("Db cleared successfully!")
        print("Now run: python import_csv.py")
        
    except Exception as e:
        print(f"Error clearing db: {e}")

if __name__ == "__main__":
    reset_db()
