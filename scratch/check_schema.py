import sqlite3
import pandas as pd

def get_schema(db_path, table):
    try:
        conn = sqlite3.connect(db_path)
        info = pd.read_sql_query(f"PRAGMA table_info({table});", conn)
        print(f"\nSchema for {table} in {db_path}:")
        print(info)
        
        data = pd.read_sql_query(f"SELECT * FROM {table} LIMIT 5", conn)
        print("\nSample Data:")
        print(data)
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

get_schema(r"c:\Users\jean_\Desktop\mt5_trading_bot\data\trades.sqlite", "deals")
get_schema(r"c:\Users\jean_\Desktop\mt5_trading_bot\data\trades.sqlite", "orders")
