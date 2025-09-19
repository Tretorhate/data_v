import pandas as pd
import psycopg2

# Db connection parameters
DB_CONFIG = {
    'host': 'localhost',
    'database': 'data_v',
    'user': 'postgres',
    'password': '0412',
    'port': '5432'
}

def debug_data():
    """Debug the data mismatch issue"""
    
    try:
        # Connect to db
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Check what's in maps_stats
        print("=== MAPS_STATS TABLE ===")
        cursor.execute('SELECT "map_name" FROM "maps_stats" ORDER BY "map_name"')
        maps = cursor.fetchall()
        for map_name in maps:
            print(f"'{map_name[0]}'")
        
        # Check economy_data CSV
        print("\n=== ECONOMY_DATA CSV ===")
        df = pd.read_csv('all_csv/economy_data.csv')
        unique_maps = df['map'].unique()
        for map_name in sorted(unique_maps):
            print(f"'{map_name}'")
        
        # Check for case differences
        print("\n=== CASE COMPARISON ===")
        db_maps = [m[0] for m in maps]
        csv_maps = df['map'].unique()
        
        for csv_map in csv_maps:
            if csv_map not in db_maps:
                print(f"CSV has '{csv_map}' but not in DB")
                # Check if it exists with different case
                for db_map in db_maps:
                    if csv_map.lower() == db_map.lower():
                        print(f"  -> Similar to DB: '{db_map}'")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_data()
