import sqlite3
import pandas as pd
from datetime import datetime

db_path = r"c:\Users\jean_\Desktop\mt5_trading_bot\data\pro_jpy.sqlite"

try:
    conn = sqlite3.connect(db_path)
    # Get all deals
    deals = pd.read_sql_query("SELECT * FROM deals ORDER BY id ASC", conn)
    
    # Convert time_setup_msc to human readable if possible, but MT5 uses seconds or msc.
    # Usually it's seconds since 1970 for 'time'. Let's see if 'time' exists.
    # Based on previous check, it might be 'time_setup_msc'.
    
    # Let's just output the raw data for now.
    deals.to_csv(r"c:\Users\jean_\Desktop\mt5_trading_bot\scratch\usdjpy_deals.csv", index=False)
    
    # Calculate some stats
    total_profit = deals['profit'].sum()
    win_rate = (deals['profit'] > 0).mean() * 100
    avg_win = deals[deals['profit'] > 0]['profit'].mean()
    avg_loss = deals[deals['profit'] < 0]['profit'].mean()
    max_win = deals['profit'].max()
    max_loss = deals['profit'].min()
    
    print(f"Total Profit: {total_profit:.2f}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Average Win: {avg_win:.2f}")
    print(f"Average Loss: {avg_loss:.2f}")
    print(f"Max Win: {max_win:.2f}")
    print(f"Max Loss: {max_loss:.2f}")
    print(f"Total Trades: {len(deals)}")

    conn.close()
except Exception as e:
    print(f"Error: {e}")
