@echo off
setlocal
cd /d "%~dp0"
title Extraction du code C# du jeu (recherche)
echo.
echo  Extraction de la structure du code C# de DQ4 (classes, champs, methodes)
echo  ------------------------------------------------------------------------
echo  Lit tes APK dans ..\..\jeux\DQ4\patched_apks (jamais modifies).
echo  Resultat : ..\dq4_pc\cache\il2cpp\dump.cs  (reste sur ton PC, pas envoye sur GitHub).
echo  Necessite internet la premiere fois (telechargement de Il2CppDumper).
echo.
if not exist "..\dq4_pc\.venv\Scripts\python.exe" (
  echo  Lance d'abord dq4_pc\lancer_dq4.bat une fois pour creer l'environnement Python.
  pause
  exit /b 1
)
"..\dq4_pc\.venv\Scripts\python.exe" dump_il2cpp.py %*
echo.
pause
