import sqlite3
import pandas as pd
import json
from datetime import datetime

db_path = r"c:\Users\jean_\Desktop\mt5_trading_bot\data\pro_jpy.sqlite"

try:
    conn = sqlite3.connect(db_path)
    deals = pd.read_sql_query("SELECT id, ticket, symbol, type, volume, price, profit, raw_json FROM deals", conn)
    
    for i, row in deals.iterrows():
        js = json.loads(row['raw_json'])
        print(f"Deal ID: {row['id']}")
        print(f"  Ticket: {row['ticket']}")
        print(f"  Symbol: {row['symbol']}")
        print(f"  Type: {'BUY' if row['type'] == 0 else 'SELL'}")
        print(f"  Volume: {row['volume']}")
        print(f"  Price: {row['price']}")
        print(f"  Profit: {row['profit']}")
        print(f"  Time: {datetime.fromtimestamp(js.get('time', 0)) if 'time' in js else 'N/A'}")
        print(f"  Entry: {js.get('entry', 'N/A')} (0=In, 1=Out)")
        print("-" * 20)
    conn.close()
except Exception as e:
    print(f"Error: {e}")
