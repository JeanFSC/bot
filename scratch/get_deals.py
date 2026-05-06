import sqlite3
import pandas as pd

db_path = r"c:\Users\jean_\Desktop\mt5_trading_bot\data\trades.sqlite"
db_path_pro = r"c:\Users\jean_\Desktop\mt5_trading_bot\data\pro.sqlite"

def get_last_deals(path, label):
    print(f"\n--- {label} ---")
    try:
        conn = sqlite3.connect(path)
        deals = pd.read_sql_query("SELECT * FROM deals ORDER BY id DESC LIMIT 20", conn)
        print(deals)
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

get_last_deals(db_path, "Trades DB")
get_last_deals(db_path_pro, "Pro DB")
