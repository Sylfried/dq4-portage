@echo off
setlocal
cd /d "%~dp0"

call :m_titre
call :m_intro

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
  call :m_python_absent
  pause
  exit /b 1
)

rem --- 1b. un ".venv" copie depuis un autre PC ne marche pas (il pointe vers le Python de l'autre machine) : on le refait
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -c "import sys" >nul 2>nul
  if errorlevel 1 (
    call :m_venv_autre_pc
    rd /s /q ".venv"
  )
)

rem --- 1c. ancien environnement (dq4_pc\.venv, d'avant le rangement du projet) : repris tel quel au lieu d'etre refait
if not exist ".venv\Scripts\python.exe" if exist "dq4_pc\.venv\Scripts\python.exe" (
  call :m_venv_ancien
  move "dq4_pc\.venv" ".venv" >nul 2>nul
  if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import numpy, pyglet, unicorn" >nul 2>nul
    if errorlevel 1 if exist ".venv\modules_ok.txt" del ".venv\modules_ok.txt"
  )
)

rem --- 2. environnement isole + modules (une seule fois)
if not exist ".venv\Scripts\python.exe" (
  call :m_venv_creation
  %PY% -m venv .venv
  if errorlevel 1 ( call :m_venv_echec & pause & exit /b 1 )
)
if not exist ".venv\modules_ok.txt" (
  call :m_install
  ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check numpy pillow unicorn pyglet UnityPy capstone soundfile
  if errorlevel 1 (
    call :m_install_echec
    pause
    exit /b 1
  )
  echo ok> ".venv\modules_ok.txt"
)

rem --- 2a. son : module des musiques (ajoute apres coup ; une seule fois pour les environnements deja crees)
if not exist ".venv\sound_ok.txt" (
  ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check soundfile
  if errorlevel 1 ( call :m_son_echec ) else ( echo ok> ".venv\sound_ok.txt" )
)

rem --- 2ab. rangement : tes anciens fichiers (jeux\DQ4, dq4_pc\cache, dq4_pc\sauvegardes, dq4_pc\reglages.json...) sont COPIES dans "data" ; le dossier "donnees" des versions d'avant (et ses sous-dossiers : sauvegardes, reglages, journaux, etats...) est RENOMME en anglais ; rien n'est supprime ni ecrase
".venv\Scripts\python.exe" -m dq4_pc.paths

rem --- 2b. fenetres de menu d'origine : mise en page lue dans le code du jeu (une seule fois, si le dump du code existe)
rem     un ancien fichier (sans la fenetre de message, d'avant le reglage de la langue ou d'avant l'argument des Make_* par groupe : textes mal places, bouton Mode de la carte absent) est refait
if exist "data\cache\ui_layout.json" (
  ".venv\Scripts\python.exe" -c "import json,sys; d=json.load(open('data/cache/ui_layout.json', encoding='utf-8')); sys.exit(0 if 'message' in d and d['header'].get('gen', 1) >= 3 else 1)" >nul 2>nul
  if errorlevel 1 del "data\cache\ui_layout.json"
)
if not exist "data\cache\ui_layout.json" (
  if exist "data\cache\il2cpp\dump.cs" (
    call :m_ui_lecture
    ".venv\Scripts\python.exe" "tools\ui_il2cpp\generate_ui.py"
    if errorlevel 1 (
      call :m_ui_echec
      pause
    )
  ) else (
    call :m_ui_simple
  )
)

rem --- 3. lancement : la console se ferme toute seule quand la fenetre du jeu se ferme ; elle reste ouverte seulement si le jeu s'arrete sur une erreur (pour lire le message)
".venv\Scripts\python.exe" -m dq4_pc %*
set "CODE=%errorlevel%"
if not "%CODE%"=="0" (
  call :m_jeu_erreur %CODE%
  pause
)
exit /b %CODE%

rem ============================================================================================================================
rem Messages (une etiquette par message et par langue ; "exit /b" rend la main a la ligne "call"). Texte ASCII seulement : la console Windows n'affiche pas les accents sans reglage.
rem ============================================================================================================================

:m_titre
title Dragon Quest IV - PC port (16:9 trial)
exit /b

:m_intro
echo.
echo  Dragon Quest IV - PC port ^(trial^)
echo  ---------------------------------
echo  Reads your APK files in "data\apk" and your saves in "data\saves" ^(data1.dat... copied from the phone^)
echo  ^(other data location: set DQ4_DATA=path\to\data^)
echo  ^(the game reads and writes its saves there; savestates are in "data\saves\savestates"^)
echo.
exit /b

:m_python_absent
echo  Python was not found. Install Python 3.12 from https://www.python.org/downloads/
echo  ^(tick "Add python.exe to PATH"^), then run this file again.
exit /b

:m_venv_autre_pc
echo  The Python environment ^(.venv^) comes from another PC: it is being rebuilt ^(once only^)...
exit /b

:m_venv_ancien
echo  Reusing the old Python environment ^(dq4_pc\.venv^)...
exit /b

:m_venv_creation
echo  Creating the Python environment ^(once only^)...
exit /b

:m_venv_echec
echo  Could not create the Python environment.
exit /b

:m_install
echo  Installing the modules ^(once only, 1 to 3 minutes^)...
exit /b

:m_install_echec
echo.
echo  The installation failed. If your Python is very recent, install Python 3.12:
echo     winget install Python.Python.3.12
echo  then delete the ".venv" folder here and run this file again.
exit /b

:m_son_echec
echo  The "soundfile" module could not be installed: music will be missing ^(sound effects still work^).
exit /b

:m_ui_lecture
echo  Reading the original window layout ^(once only, a few minutes^)...
exit /b

:m_ui_echec
echo.
echo  Reading failed: details in data\cache\ui_generation.log ^(plain menus this time^).
exit /b

:m_ui_simple
echo  Plain menus ^(for the original windows: run tools\dump_il2cpp.bat first^).
exit /b

:m_jeu_erreur
echo.
echo  The game stopped on an error ^(code %1^): read the lines above ^(details in data\logs^).
exit /b
