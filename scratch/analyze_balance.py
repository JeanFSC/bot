import os
import re
from datetime import datetime

log_dir = r"c:\Users\jean_\Desktop\mt5_trading_bot\logs"
balance_pattern = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) INFO mt5_bot - Balance=([\d.]+) Equity=([\d.]+)")

history = []

for filename in sorted(os.listdir(log_dir)):
    if filename.startswith("bot_2026") and filename.endswith(".log"):
        with open(os.path.join(log_dir, filename), "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                match = balance_pattern.search(line)
                if match:
                    dt_str, balance, equity = match.groups()
                    history.append((dt_str, float(balance), float(equity)))

# Keep only changes
if not history:
    print("No balance logs found.")
else:
    print(f"Total entries: {len(history)}")
    last_balance = None
    for dt, bal, eq in history:
        if last_balance is None or bal != last_balance:
            print(f"{dt} | Balance: {bal:.2f} | Equity: {eq:.2f}")
            last_balance = bal
