import sqlite3
import pandas as pd

db_path_scalper = r"c:\Users\jean_\Desktop\mt5_trading_bot\data\scalper.sqlite"

try:
    conn = sqlite3.connect(db_path_scalper)
    total_profit = pd.read_sql_query("SELECT SUM(profit) as total FROM deals", conn)
    print(f"Total Profit in Scalper DB: {total_profit['total'][0]:.2f}")
    
    symbol_profit = pd.read_sql_query("SELECT symbol, SUM(profit) as total FROM deals GROUP BY symbol ORDER BY total DESC", conn)
    print("\nProfit by Symbol:")
    print(symbol_profit)
    
    # Last 10 profitable trades
    last_wins = pd.read_sql_query("SELECT * FROM deals WHERE profit > 0 ORDER BY id DESC LIMIT 10", conn)
    print("\nLast 10 Wins:")
    print(last_wins[['symbol', 'volume', 'price', 'profit', 'comment']])

    conn.close()
except Exception as e:
    print(f"Error: {e}")
