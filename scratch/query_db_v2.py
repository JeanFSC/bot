import sqlite3
import pandas as pd

def query_db(db_path, label):
    print(f"\n--- {label} ({db_path}) ---")
    try:
        conn = sqlite3.connect(db_path)
        tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table';", conn)
        t_list = tables['name'].tolist()
        print("Tables:", t_list)
        
        deal_table = 'deals' if 'deals' in t_list else ('history_deals' if 'history_deals' in t_list else None)
        if deal_table:
            deals = pd.read_sql_query(f"SELECT * FROM {deal_table} ORDER BY time DESC LIMIT 20", conn)
            # Find relevant columns
            cols = [c for c in ['time', 'symbol', 'type', 'volume', 'price', 'profit', 'comment'] if c in deals.columns]
            print(f"\nLast 20 {deal_table.capitalize()}:")
            print(deals[cols])
        
        order_table = 'orders' if 'orders' in t_list else ('order_results' if 'order_results' in t_list else None)
        if order_table:
            orders = pd.read_sql_query(f"SELECT * FROM {order_table} ORDER BY time DESC LIMIT 10", conn)
            cols = [c for c in ['time', 'symbol', 'retcode', 'comment', 'status'] if c in orders.columns]
            print(f"\nLast 10 {order_table.capitalize()}:")
            print(orders[cols])

        conn.close()
    except Exception as e:
        print(f"Error in {label}: {e}")

query_db(r"c:\Users\jean_\Desktop\mt5_trading_bot\data\trades.sqlite", "Trades DB")
query_db(r"c:\Users\jean_\Desktop\mt5_trading_bot\data\pro.sqlite", "Pro DB")
query_db(r"c:\Users\jean_\Desktop\mt5_trading_bot\data\demo_challenge.sqlite", "Demo Challenge DB")
