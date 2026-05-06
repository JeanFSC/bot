Dim wsh, botDir, fso
Set wsh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
botDir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))

' Write debug marker to confirm VBS is running
Dim ts
Set ts = fso.OpenTextFile(botDir & "logs\vbs_debug.txt", 8, True)
ts.WriteLine Now() & " VBS started, botDir=" & botDir
ts.Close

Dim batFile
batFile = botDir & "START_BOTS.bat"

' Write what we're about to run
Set ts = fso.OpenTextFile(botDir & "logs\vbs_debug.txt", 8, True)
ts.WriteLine Now() & " About to run: cmd.exe /k " & Chr(34) & batFile & Chr(34)
ts.Close

wsh.Run "cmd.exe /k " & Chr(34) & batFile & Chr(34), 1, False

Set ts = fso.OpenTextFile(botDir & "logs\vbs_debug.txt", 8, True)
ts.WriteLine Now() & " wsh.Run called"
ts.Close
