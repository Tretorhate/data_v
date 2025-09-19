import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import os
from datetime import datetime
import re

# Db connection parameters
DB_CONFIG = {
    'host': 'localhost',
    'database': 'data_v',
    'user': 'postgres',  # Change to your PostgreSQL username
    'password': '0412',  # Change to your PostgreSQL password
    'port': '5432'
}

def clean_percentage(value):
    """Remove % and convert to int"""
    if pd.isna(value) or value == '':
        return None
    if isinstance(value, str):
        return int(value.replace('%', ''))
    return int(value)

def clean_decimal(value):
    """Clean decimals and convert to float"""
    if pd.isna(value) or value == '' or value == 'NaN':
        return None
    if isinstance(value, str):
        # Remove non-numeric chars except decimal point
        cleaned = re.sub(r'[^\d.-]', '', value)
        return float(cleaned) if cleaned else None
    return float(value)

def clean_string(value):
    """Clean strings and handle NaN"""
    if pd.isna(value) or value == '' or value == 'NaN':
        return None
    return str(value).strip()

def clean_date(date_str):
    """Convert date string to proper format"""
    if pd.isna(date_str) or date_str == '':
        return None
    
    # Handle different date formats
    if isinstance(date_str, str):
        try:
            # Try to common date formats
            for fmt in ['%Y-%m-%d', '%a, %B %d, %Y', '%Y-%m-%d %H:%M:%S']:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
            return None
        except:
            return None
    return date_str

def connect_to_db():
    """Connect db"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Error connecting to db: {e}")
        return None

def import_csv_to_table(conn, csv_file, table_name, column_mapping=None, data_cleaners=None):
    """Import CSV to PostgreSQL table"""
    try:
        print(f"Importing {csv_file} to {table_name}...")
        
        # Read CSV
        df = pd.read_csv(f'all_csv/{csv_file}')
        print(f"  - Found {len(df)} rows")
        
        # Apply data cleaners if provided
        if data_cleaners:
            for column, cleaner in data_cleaners.items():
                if column in df.columns:
                    df[column] = df[column].apply(cleaner)
        
        # Rename columns if mapping provided
        if column_mapping:
            df = df.rename(columns=column_mapping)
        
        # Clean all string columns to handle NaN values
        for col in df.columns:
            if df[col].dtype == 'object':  # String columns
                df[col] = df[col].apply(clean_string)
        
        # Filter out rows with null map_name for detailed_matches_player_stats
        if table_name == 'detailed_matches_player_stats':
            df = df.dropna(subset=['map_name'])
            print(f"  - Filtered to {len(df)} rows after removing null map_name")
        
        # Clean and validate map names for economy_data
        if table_name == 'economy_data':
            # Add "All Maps" to maps_stats table
            try:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO "maps_stats" ("map_name", "times_played", "attack_win_percent", "defense_win_percent") 
                    VALUES ('All Maps', 0, 0, 0) 
                    ON CONFLICT ("map_name") DO NOTHING
                ''')
                conn.commit()
                cursor.close()
                print("  - Added 'All Maps' entry to maps_stats table")
            except Exception as e:
                print(f"  - Warning: Could not add 'All Maps' to maps_stats: {e}")
            
            # Get valid map names from maps_stats
            cursor = conn.cursor()
            cursor.execute('SELECT "map_name" FROM "maps_stats"')
            valid_maps = {row[0].lower(): row[0] for row in cursor.fetchall()}
            cursor.close()
            
            # Clean map names and filter invalid ones
            original_count = len(df)
            df['map'] = df['map'].apply(lambda x: valid_maps.get(x.lower(), x) if pd.notna(x) else x)
            df = df[df['map'].isin(valid_maps.values())]
            filtered_count = len(df)
            
            if original_count != filtered_count:
                print(f"  - Filtered out {original_count - filtered_count} rows with invalid map names")
                print(f"  - Remaining {filtered_count} rows with valid map names")
        
        # Prepare data for insertion
        columns = list(df.columns)
        values = [tuple(row) for row in df.values]
        
        # Create INSERT query with properly quoted column names
        quoted_columns = [f'"{col}"' for col in columns]
        placeholders = ','.join(['%s'] * len(columns))
        
        # Use ON CONFLICT DO NOTHING for tables with primary keys to handle duplicates
        if table_name in ['economy_data', 'performance_data', 'detailed_matches_player_stats', 'detailed_matches_maps']:
            query = f"INSERT INTO {table_name} ({','.join(quoted_columns)}) VALUES %s ON CONFLICT DO NOTHING"
        else:
            query = f"INSERT INTO {table_name} ({','.join(quoted_columns)}) VALUES %s"
        
        # Execute insert
        cursor = conn.cursor()
        execute_values(cursor, query, values, template=f"({placeholders})", page_size=1000)
        conn.commit()
        cursor.close()
        
        print(f"  - Successfully imported {len(df)} rows to {table_name}")
        return True
        
    except Exception as e:
        print(f"  - Error importing {csv_file}: {e}")
        conn.rollback()
        return False

def main():
    """Main import function"""
    print("Starting CSV import to PostgreSQL db 'data_v'...")
    
    # Connect to db
    conn = connect_to_db()
    if not conn:
        return
    
    try:
        # Import configurations for each table
        import_configs = [
            {
                'csv_file': 'event_info.csv',
                'table_name': 'event_info',
                'data_cleaners': {}
            },
            {
                'csv_file': 'matches.csv',
                'table_name': 'matches',
                'data_cleaners': {
                    'date': clean_date
                }
            },
            {
                'csv_file': 'player_stats.csv',
                'table_name': 'player_stats',
                'data_cleaners': {
                    'rating': clean_decimal,
                    'acs': clean_decimal,
                    'kd_ratio': clean_decimal,
                    'kast': clean_percentage,
                    'adr': clean_decimal,
                    'kpr': clean_decimal,
                    'apr': clean_decimal,
                    'fkpr': clean_decimal,
                    'fdpr': clean_decimal,
                    'hs_percent': clean_percentage,
                    'cl_percent': clean_percentage
                }
            },
            {
                'csv_file': 'maps_stats.csv',
                'table_name': 'maps_stats',
                'data_cleaners': {
                    'attack_win_percent': clean_percentage,
                    'defense_win_percent': clean_percentage
                }
            },
            {
                'csv_file': 'agents_stats.csv',
                'table_name': 'agents_stats',
                'data_cleaners': {
                    'total_utilization': clean_decimal
                }
            },
            {
                'csv_file': 'economy_data.csv',
                'table_name': 'economy_data',
                'column_mapping': {
                    'Pistol Won': 'Pistol Won',
                    'Eco (won)': 'Eco (won)',
                    'Semi-eco (won)': 'Semi-eco (won)',
                    'Semi-buy (won)': 'Semi-buy (won)',
                    'Full buy(won)': 'Full buy(won)'
                },
                'data_cleaners': {}
            },
            {
                'csv_file': 'performance_data.csv',
                'table_name': 'performance_data',
                'column_mapping': {
                    'Match ID': 'Match ID',
                    '2K': '2K',
                    '3K': '3K',
                    '4K': '4K',
                    '5K': '5K',
                    '1v1': '1v1',
                    '1v2': '1v2',
                    '1v3': '1v3',
                    '1v4': '1v4',
                    '1v5': '1v5'
                },
                'data_cleaners': {
                    'ECON': clean_decimal
                }
            },
            {
                'csv_file': 'detailed_matches_overview.csv',
                'table_name': 'detailed_matches_overview',
                'data_cleaners': {
                    'date': clean_date
                }
            },
            {
                'csv_file': 'detailed_matches_player_stats.csv',
                'table_name': 'detailed_matches_player_stats',
                'data_cleaners': {
                    'match_date': clean_date,
                    'rating': clean_decimal,
                    'acs': clean_decimal,
                    'kast': clean_percentage,
                    'adr': clean_decimal,
                    'hs_percent': clean_percentage,
                    'map_name': clean_string,
                    'map_winner': clean_string
                }
            },
            {
                'csv_file': 'detailed_matches_maps.csv',
                'table_name': 'detailed_matches_maps',
                'data_cleaners': {}
            }
        ]
        
        # Import each CSV file
        success_count = 0
        total_count = len(import_configs)
        
        for config in import_configs:
            if import_csv_to_table(conn, **config):
                success_count += 1
        
        print(f"\nImport completed: {success_count}/{total_count} files imported successfully")
        
    except Exception as e:
        print(f"Error during import: {e}")
        conn.rollback()
    
    finally:
        conn.close()
        print("Db connection closed.")

if __name__ == "__main__":
    main()