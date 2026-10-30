@echo off
setlocal
cd /d "%~dp0"
title Dragon Quest IV - portage PC (essai 16/9)
echo.
echo  Dragon Quest IV - portage PC (essai)
echo  ------------------------------------
echo  Lit tes APK francais dans ..\..\jeux\DQ4\patched_apks
echo  et ta derniere sauvegarde dans ..\..\jeux\DQ4\saves
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

rem --- 2. environnement isole + modules (une seule fois)
if not exist ".venv\Scripts\python.exe" (
  echo  Creation de l'environnement Python ^(une seule fois^)...
  %PY% -m venv .venv
  if errorlevel 1 ( echo  Echec de la creation de l'environnement. & pause & exit /b 1 )
)
if not exist ".venv\modules_ok.txt" (
  echo  Installation des modules ^(une seule fois, 1 a 3 minutes^)...
  ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check numpy pillow unicorn pyglet UnityPy
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

rem --- 3. lancement
".venv\Scripts\python.exe" fenetre.py %*
echo.
echo  Fin du programme.
pause
