Set sh = CreateObject("WScript.Shell")
sh.Run "cmd /c ""C:\AIOFEN\subir_atualizacao_auto.bat"" >> ""C:\AIOFEN\backup_auto.log"" 2>&1", 0, False
