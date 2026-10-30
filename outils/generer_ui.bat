@echo off
setlocal
cd /d "%~dp0"
title Mise en page d'origine des fenetres de menu
echo.
echo  Lecture de la mise en page EXACTE des fenetres de menu du jeu
echo  -------------------------------------------------------------
echo  Execute le code d'origine (Make_*) du jeu sous emulation et ecrit
echo  ..\dq4_pc\cache\ui_layout.json  (reste sur ton PC, pas envoye sur GitHub).
echo  Prerequis : outils\dump_il2cpp.bat deja lance. Quelques minutes, une seule fois.
echo.
if not exist "..\dq4_pc\.venv\Scripts\python.exe" (
  echo  Lance d'abord dq4_pc\lancer_dq4.bat une fois pour creer l'environnement Python.
  pause
  exit /b 1
)
"..\dq4_pc\.venv\Scripts\python.exe" -c "import unicorn" >nul 2>nul
if errorlevel 1 "..\dq4_pc\.venv\Scripts\python.exe" -m pip install --quiet unicorn
"..\dq4_pc\.venv\Scripts\python.exe" ui_il2cpp\generer_ui.py %*
echo.
pause
