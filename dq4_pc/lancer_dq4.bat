@echo off
setlocal
cd /d "%~dp0"
title Dragon Quest IV - portage PC (essai 16/9)
echo.
echo  Dragon Quest IV - portage PC (essai)
echo  ------------------------------------
echo  Lit tes APK francais et ta derniere sauvegarde dans le dossier "jeux\DQ4"
echo  ^(trouve tout seul a cote du projet ; sinon : set DQ4_JEUX=chemin\vers\jeux\DQ4^)
echo  (tes fichiers ne sont jamais modifies ; les nouvelles sauvegardes vont dans le dossier "sauvegardes" ici)
echo.

rem --- 1. Python : on prefere une version stable ayant des paquets precompiles
set "PY="
for %%V in (3.13 3.12 3.11 3.14 3.10) do (
  if not defined PY (
    py -%%V -c "import sys" >nul 2>nul && set "PY=py -%%V"
  )
)
if not defined PY (
  python -c "import sys" >nul 2>nul && set "PY=python"
)
if not defined PY (
  echo  Python est introuvable. Installe Python 3.12 depuis https://www.python.org/downloads/
  echo  ^(coche "Add python.exe to PATH"^), puis relance ce fichier.
  pause
  exit /b 1
)

rem --- 1b. un ".venv" copie depuis un autre PC ne marche pas (il pointe vers le Python de l'autre machine) : on le refait
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -c "import sys" >nul 2>nul
  if errorlevel 1 (
    echo  L'environnement Python ^(.venv^) vient d'un autre PC : il est refait ^(une seule fois^)...
    rd /s /q ".venv"
  )
)

rem --- 2. environnement isole + modules (une seule fois)
if not exist ".venv\Scripts\python.exe" (
  echo  Creation de l'environnement Python ^(une seule fois^)...
  %PY% -m venv .venv
  if errorlevel 1 ( echo  Echec de la creation de l'environnement. & pause & exit /b 1 )
)
if not exist ".venv\modules_ok.txt" (
  echo  Installation des modules ^(une seule fois, 1 a 3 minutes^)...
  ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check numpy pillow unicorn pyglet UnityPy capstone soundfile
  if errorlevel 1 (
    echo.
    echo  L'installation a echoue. Si ton Python est tres recent, installe Python 3.12 :
    echo     winget install Python.Python.3.12
    echo  puis supprime le dossier ".venv" ici et relance ce fichier.
    pause
    exit /b 1
  )
  echo ok> ".venv\modules_ok.txt"
)

rem --- 2a. son : module des musiques (ajoute apres coup ; une seule fois pour les environnements deja crees)
if not exist ".venv\sound_ok.txt" (
  ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check soundfile
  if errorlevel 1 ( echo  Module "soundfile" non installe : les musiques seront absentes ^(les bruitages fonctionnent^). ) else ( echo ok> ".venv\sound_ok.txt" )
)

rem --- 2b. fenetres de menu d'origine : mise en page lue dans le code du jeu (une seule fois, si le dump du code existe)
rem     un ancien fichier sans la fenetre de message est refait
if exist "cache\ui_layout.json" (
  ".venv\Scripts\python.exe" -c "import json,sys; sys.exit(0 if 'message' in json.load(open('cache/ui_layout.json', encoding='utf-8')) else 1)" >nul 2>nul
  if errorlevel 1 del "cache\ui_layout.json"
)
if not exist "cache\ui_layout.json" (
  if exist "cache\il2cpp\dump.cs" (
    echo  Lecture de la mise en page d'origine des fenetres ^(une seule fois, quelques minutes^)...
    ".venv\Scripts\python.exe" "..\outils\ui_il2cpp\generer_ui.py"
    if errorlevel 1 (
      echo.
      echo  La lecture a echoue : details dans cache\ui_generation.log ^(menus simples pour cette fois^).
      pause
    )
  ) else (
    echo  Menus simples ^(pour les fenetres d'origine : lance d'abord ..\outils\dump_il2cpp.bat^).
  )
)

rem --- 3. lancement
".venv\Scripts\python.exe" fenetre.py %*
echo.
echo  Fin du programme.
pause
