"""Quick direct EURUSD BUY 0.01 lot — bypasses strategy, for DEMO testing only."""
from __future__ import annotations
import os, sys
from pathlib import Path

# Load .env
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

LOGIN   = int(os.environ["MT5_LOGIN"])
PASSWD  = os.environ["MT5_PASSWORD"]
SERVER  = os.environ["MT5_SERVER"]
SYMBOL  = "EURUSD"
LOT     = 0.01
MAGIC   = 260430
DEVIATION = 20

try:
    import MetaTrader5 as mt5
except ImportError:
    sys.exit("MetaTrader5 not installed.")

print(f"Connecting to {SERVER} as {LOGIN} ...")
if not mt5.initialize():
    sys.exit(f"initialize() failed: {mt5.last_error()}")

if not mt5.login(LOGIN, password=PASSWD, server=SERVER):
    mt5.shutdown()
    sys.exit(f"login() failed: {mt5.last_error()}")

info = mt5.account_info()
print(f"Account: {info.name} | Balance: {info.balance} {info.currency}")

# Get tick
mt5.symbol_select(SYMBOL, True)
tick = mt5.symbol_info_tick(SYMBOL)
if tick is None:
    mt5.shutdown()
    sys.exit(f"No tick for {SYMBOL}")

sym = mt5.symbol_info(SYMBOL)
filling = mt5.ORDER_FILLING_IOC
if sym.filling_mode & 1:    # FOK supported
    filling = mt5.ORDER_FILLING_FOK
elif sym.filling_mode & 2:  # IOC supported
    filling = mt5.ORDER_FILLING_IOC
else:
    filling = mt5.ORDER_FILLING_RETURN

request = {
    "action":    mt5.TRADE_ACTION_DEAL,
    "symbol":    SYMBOL,
    "volume":    LOT,
    "type":      mt5.ORDER_TYPE_BUY,
    "price":     tick.ask,
    "deviation": DEVIATION,
    "magic":     MAGIC,
    "comment":   "force_demo_test",
    "type_time": mt5.ORDER_TIME_GTC,
    "type_filling": filling,
}

print(f"\nSending BUY {LOT} {SYMBOL} @ {tick.ask:.5f} ...")
check = mt5.order_check(request)
print(f"Check: retcode={check.retcode} margin={check.margin:.2f} profit={check.profit:.2f}")

result = mt5.order_send(request)
print(f"\n=== RESULT ===")
print(f"retcode  : {result.retcode}")
print(f"deal     : {result.deal}")
print(f"order    : {result.order}")
print(f"volume   : {result.volume}")
print(f"price    : {result.price}")
print(f"comment  : {result.comment}")

if result.retcode == 10009:
    print("\n✓ ORDER ACCEPTED — deal placed on DEMO!")
else:
    print(f"\n✗ ORDER FAILED (retcode={result.retcode})")

mt5.shutdown()
input("\nPress Enter to close...")
