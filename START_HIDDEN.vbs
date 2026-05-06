' START_HIDDEN.vbs — Lanza los 5 bots MT5 SIN ventana CMD visible
' Usa pythonw.exe para que el proceso corra en fondo sin consola
' El proceso NO muere si cierras una ventana accidentalmente
Dim wsh, fso, botDir, ts
Set wsh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

botDir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))

' Log de inicio
If Not fso.FolderExists(botDir & "logs") Then
    fso.CreateFolder(botDir & "logs")
End If
Set ts = fso.OpenTextFile(botDir & "logs\start_hidden.log", 8, True)
ts.WriteLine Now() & " START_HIDDEN.vbs ejecutado"
ts.Close

' Lanzar con pythonw.exe (sin ventana), modo oculto (0), no esperar (False)
Dim cmd
cmd = """" & botDir & ".venv\Scripts\pythonw.exe"" """ & botDir & "LAUNCHER_DIRECT.py"""
Set ts = fso.OpenTextFile(botDir & "logs\start_hidden.log", 8, True)
ts.WriteLine Now() & " Ejecutando: " & cmd
ts.Close

wsh.Run cmd, 0, False

Set ts = fso.OpenTextFile(botDir & "logs\start_hidden.log", 8, True)
ts.WriteLine Now() & " wsh.Run completado — bots corriendo en background"
ts.Close

MsgBox "5 bots lanzados en background." & Chr(13) & Chr(10) & _
       "Corren sin ventana visible — no pueden cerrarse accidentalmente." & Chr(13) & Chr(10) & _
       "Para detener: usa el Administrador de Tareas (pythonw.exe).", _
       64, "MT5 Pro Suite — Iniciado"
