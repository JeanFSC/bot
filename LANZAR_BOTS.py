"""Script lanzador de bots MT5 - ejecutar con doble clic"""
import subprocess, os, sys, time

# Directorio del script
bot_dir = os.path.dirname(os.path.abspath(__file__))

bots = [
    ("PRO EURUSD", "_restart_eurusd.bat"),
    ("PRO GBPUSD", "_restart_gbpusd.bat"),
    ("PRO USDJPY", "_restart_jpy.bat"),
    ("PRO XAUUSD", "_restart_gold.bat"),
    ("PRO AUDUSD", "_restart_aud.bat"),
]

print("=" * 60)
print("  MT5 PRO SUITE - Lanzando 5 bots...")
print("=" * 60)

for title, bat in bots:
    bat_path = os.path.join(bot_dir, bat)
    subprocess.Popen(
        ["cmd.exe", "/c", "start", f'"{title}"', bat_path],
        cwd=bot_dir,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
        shell=True
    )
    print(f"  Lanzado: {title}")
    time.sleep(3)

print()
print("5 bots lanzados. Esta ventana puede cerrarse.")
input("Presiona Enter para cerrar...")
