import sqlite3
import pandas as pd

db_path = r"c:\Users\jean_\Desktop\mt5_trading_bot\data\pro_jpy.sqlite"

try:
    conn = sqlite3.connect(db_path)
    deals = pd.read_sql_query("SELECT * FROM deals", conn)
    print(deals)
    conn.close()
except Exception as e:
    print(f"Error: {e}")
