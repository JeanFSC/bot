import sqlite3
import pandas as pd

def summarize(db_path, label):
    print(f"\n--- {label} ({db_path}) ---")
    try:
        conn = sqlite3.connect(db_path)
        total_profit = pd.read_sql_query("SELECT SUM(profit) as total FROM deals", conn)
        print(f"Total Profit: {total_profit['total'][0]:.2f}")
        
        symbol_profit = pd.read_sql_query("SELECT symbol, SUM(profit) as total FROM deals GROUP BY symbol ORDER BY total DESC", conn)
        print("Profit by Symbol:")
        print(symbol_profit)
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

summarize(r"c:\Users\jean_\Desktop\mt5_trading_bot\data\pro_gbp.sqlite", "Pro GBP")
summarize(r"c:\Users\jean_\Desktop\mt5_trading_bot\data\pro_jpy.sqlite", "Pro JPY")
summarize(r"c:\Users\jean_\Desktop\mt5_trading_bot\data\pro_gold.sqlite", "Pro Gold")
summarize(r"c:\Users\jean_\Desktop\mt5_trading_bot\data\pro_aud.sqlite", "Pro AUD")
