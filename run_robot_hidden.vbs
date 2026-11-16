' Inicia o robo WDO 100% oculto (Frente 1 / 23.50).
' O console do cmd fica invisivel; a janela PyWebView do Dashboard continua
' aparecendo normalmente, pois e uma janela GUI criada pelo proprio robo.
Option Explicit
Dim sh
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = "C:\AIOFEN"
sh.Run "cmd /c ""C:\AIOFEN\run_robot_hidden.bat""", 0, False
