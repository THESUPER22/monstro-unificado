' Wrapper silencioso para tarefas de segundo plano (Frente 1 / 23.50).
' Uso: wscript.exe hidden.vbs <arquivo_de_log> "<comando>"
' Roda o comando em cmd /c com janela 0 (oculta) e telemetria no log.
Option Explicit
Dim sh, logPath, cmd
If WScript.Arguments.Count < 2 Then WScript.Quit 2
logPath = WScript.Arguments(0)
cmd = WScript.Arguments(1)
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = "C:\AIOFEN"
sh.Run "cmd /c " & cmd & " >> """ & logPath & """ 2>&1", 0, False
