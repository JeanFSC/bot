import sqlite3
import pandas as pd

db_path = r"c:\Users\jean_\Desktop\mt5_trading_bot\data\trades.sqlite"

try:
    conn = sqlite3.connect(db_path)
    # Check tables
    tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table';", conn)
    print("Tables:", tables['name'].tolist())
    
    if 'history_deals' in tables['name'].values:
        deals = pd.read_sql_query("SELECT * FROM history_deals ORDER BY time DESC LIMIT 20", conn)
        print("\nLast 20 Deals:")
        print(deals[['time', 'symbol', 'type', 'volume', 'price', 'profit', 'comment']])
    
    if 'order_results' in tables['name'].values:
        results = pd.read_sql_query("SELECT * FROM order_results ORDER BY time DESC LIMIT 10", conn)
        print("\nLast 10 Order Results:")
        print(results[['time', 'symbol', 'retcode', 'comment']])

    conn.close()
except Exception as e:
    print(f"Error: {e}")
