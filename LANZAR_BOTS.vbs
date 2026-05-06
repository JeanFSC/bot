' Lanzador de bots MT5 sin SmartScreen
Dim wsh, botDir
Set wsh = CreateObject("WScript.Shell")

botDir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))

wsh.Run "cmd /c start ""PRO EURUSD"" """ & botDir & "_restart_eurusd.bat"""
WScript.Sleep 3000
wsh.Run "cmd /c start ""PRO GBPUSD"" """ & botDir & "_restart_gbpusd.bat"""
WScript.Sleep 3000
wsh.Run "cmd /c start ""PRO USDJPY"" """ & botDir & "_restart_jpy.bat"""
WScript.Sleep 3000
wsh.Run "cmd /c start ""PRO XAUUSD"" """ & botDir & "_restart_gold.bat"""
WScript.Sleep 3000
wsh.Run "cmd /c start ""PRO AUDUSD"" """ & botDir & "_restart_aud.bat"""

MsgBox "5 bots lanzados con auto-restart.", 64, "MT5 Pro Suite"
