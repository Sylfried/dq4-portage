@echo off
setlocal
cd /d "%~dp0"

rem --- 0. langue des messages de ce lanceur : francais si Windows est en francais, anglais sinon (le jeu lui-meme suit son reglage Affichage, Langue)
rem     chaque message existe en deux versions (etiquettes :m_xxx_fr et :m_xxx_en, en bas du fichier) ; on les appelle avec "call :m_xxx_%DQLANG%"
set "LOC="
for /f "tokens=3" %%L in ('reg query "HKCU\Control Panel\Desktop" /v PreferredUILanguages 2^>nul') do if not defined LOC set "LOC=%%L"
if not defined LOC for /f "tokens=3" %%L in ('reg query "HKCU\Control Panel\International" /v LocaleName 2^>nul') do set "LOC=%%L"
set "DQLANG=en"
if defined LOC if /i "%LOC:~0,2%"=="fr" set "DQLANG=fr"

call :m_titre_%DQLANG%
call :m_intro_%DQLANG%

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
  call :m_python_absent_%DQLANG%
  pause
  exit /b 1
)

rem --- 1b. un ".venv" copie depuis un autre PC ne marche pas (il pointe vers le Python de l'autre machine) : on le refait
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -c "import sys" >nul 2>nul
  if errorlevel 1 (
    call :m_venv_autre_pc_%DQLANG%
    rd /s /q ".venv"
  )
)

rem --- 1c. ancien environnement (dq4_pc\.venv, d'avant le rangement du projet) : repris tel quel au lieu d'etre refait
if not exist ".venv\Scripts\python.exe" if exist "dq4_pc\.venv\Scripts\python.exe" (
  call :m_venv_ancien_%DQLANG%
  move "dq4_pc\.venv" ".venv" >nul 2>nul
  if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import numpy, pyglet, unicorn" >nul 2>nul
    if errorlevel 1 if exist ".venv\modules_ok.txt" del ".venv\modules_ok.txt"
  )
)

rem --- 2. environnement isole + modules (une seule fois)
if not exist ".venv\Scripts\python.exe" (
  call :m_venv_creation_%DQLANG%
  %PY% -m venv .venv
  if errorlevel 1 ( call :m_venv_echec_%DQLANG% & pause & exit /b 1 )
)
if not exist ".venv\modules_ok.txt" (
  call :m_install_%DQLANG%
  ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check numpy pillow unicorn pyglet UnityPy capstone soundfile
  if errorlevel 1 (
    call :m_install_echec_%DQLANG%
    pause
    exit /b 1
  )
  echo ok> ".venv\modules_ok.txt"
)

rem --- 2a. son : module des musiques (ajoute apres coup ; une seule fois pour les environnements deja crees)
if not exist ".venv\sound_ok.txt" (
  ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check soundfile
  if errorlevel 1 ( call :m_son_echec_%DQLANG% ) else ( echo ok> ".venv\sound_ok.txt" )
)

rem --- 2ab. rangement : tes anciens fichiers (jeux\DQ4, dq4_pc\cache, dq4_pc\sauvegardes, dq4_pc\reglages.json...) sont COPIES dans "donnees" ; rien n'est supprime ni ecrase
".venv\Scripts\python.exe" -m dq4_pc.paths

rem --- 2b. fenetres de menu d'origine : mise en page lue dans le code du jeu (une seule fois, si le dump du code existe)
rem     un ancien fichier (sans la fenetre de message, d'avant le reglage de la langue ou d'avant l'argument des Make_* par groupe : textes mal places, bouton Mode de la carte absent) est refait
if exist "donnees\cache\ui_layout.json" (
  ".venv\Scripts\python.exe" -c "import json,sys; d=json.load(open('donnees/cache/ui_layout.json', encoding='utf-8')); sys.exit(0 if 'message' in d and d['header'].get('gen', 1) >= 3 else 1)" >nul 2>nul
  if errorlevel 1 del "donnees\cache\ui_layout.json"
)
if not exist "donnees\cache\ui_layout.json" (
  if exist "donnees\cache\il2cpp\dump.cs" (
    call :m_ui_lecture_%DQLANG%
    ".venv\Scripts\python.exe" "tools\ui_il2cpp\generate_ui.py"
    if errorlevel 1 (
      call :m_ui_echec_%DQLANG%
      pause
    )
  ) else (
    call :m_ui_simple_%DQLANG%
  )
)

rem --- 3. lancement : la console se ferme toute seule quand la fenetre du jeu se ferme ; elle reste ouverte seulement si le jeu s'arrete sur une erreur (pour lire le message)
".venv\Scripts\python.exe" -m dq4_pc %*
set "CODE=%errorlevel%"
if not "%CODE%"=="0" (
  call :m_jeu_erreur_%DQLANG% %CODE%
  pause
)
exit /b %CODE%

rem ============================================================================================================================
rem Messages (une etiquette par message et par langue ; "exit /b" rend la main a la ligne "call"). Texte ASCII seulement : la console Windows n'affiche pas les accents sans reglage.
rem ============================================================================================================================

:m_titre_fr
title Dragon Quest IV - portage PC (essai 16/9)
exit /b
:m_titre_en
title Dragon Quest IV - PC port (16:9 trial)
exit /b

:m_intro_fr
echo.
echo  Dragon Quest IV - portage PC (essai)
echo  ------------------------------------
echo  Lit tes APK francais dans "donnees\apk" et tes sauvegardes dans "donnees\sauvegardes" ^(data1.dat... copies du telephone^)
echo  ^(autre emplacement des donnees : set DQ4_DONNEES=chemin\vers\donnees^)
echo  ^(le jeu y lit et y ecrit ses sauvegardes ; les etats instantanes sont dans "donnees\sauvegardes\etats"^)
echo.
exit /b
:m_intro_en
echo.
echo  Dragon Quest IV - PC port ^(trial^)
echo  ---------------------------------
echo  Reads your APK files in "donnees\apk" and your saves in "donnees\sauvegardes" ^(data1.dat... copied from the phone^)
echo  ^(other data location: set DQ4_DONNEES=path\to\donnees^)
echo  ^(the game reads and writes its saves there; save states are in "donnees\sauvegardes\etats"^)
echo.
exit /b

:m_python_absent_fr
echo  Python est introuvable. Installe Python 3.12 depuis https://www.python.org/downloads/
echo  ^(coche "Add python.exe to PATH"^), puis relance ce fichier.
exit /b
:m_python_absent_en
echo  Python was not found. Install Python 3.12 from https://www.python.org/downloads/
echo  ^(tick "Add python.exe to PATH"^), then run this file again.
exit /b

:m_venv_autre_pc_fr
echo  L'environnement Python ^(.venv^) vient d'un autre PC : il est refait ^(une seule fois^)...
exit /b
:m_venv_autre_pc_en
echo  The Python environment ^(.venv^) comes from another PC: it is being rebuilt ^(once only^)...
exit /b

:m_venv_ancien_fr
echo  Reprise de l'ancien environnement Python ^(dq4_pc\.venv^)...
exit /b
:m_venv_ancien_en
echo  Reusing the old Python environment ^(dq4_pc\.venv^)...
exit /b

:m_venv_creation_fr
echo  Creation de l'environnement Python ^(une seule fois^)...
exit /b
:m_venv_creation_en
echo  Creating the Python environment ^(once only^)...
exit /b

:m_venv_echec_fr
echo  Echec de la creation de l'environnement.
exit /b
:m_venv_echec_en
echo  Could not create the Python environment.
exit /b

:m_install_fr
echo  Installation des modules ^(une seule fois, 1 a 3 minutes^)...
exit /b
:m_install_en
echo  Installing the modules ^(once only, 1 to 3 minutes^)...
exit /b

:m_install_echec_fr
echo.
echo  L'installation a echoue. Si ton Python est tres recent, installe Python 3.12 :
echo     winget install Python.Python.3.12
echo  puis supprime le dossier ".venv" ici et relance ce fichier.
exit /b
:m_install_echec_en
echo.
echo  The installation failed. If your Python is very recent, install Python 3.12:
echo     winget install Python.Python.3.12
echo  then delete the ".venv" folder here and run this file again.
exit /b

:m_son_echec_fr
echo  Module "soundfile" non installe : les musiques seront absentes ^(les bruitages fonctionnent^).
exit /b
:m_son_echec_en
echo  The "soundfile" module could not be installed: music will be missing ^(sound effects still work^).
exit /b

:m_ui_lecture_fr
echo  Lecture de la mise en page d'origine des fenetres ^(une seule fois, quelques minutes^)...
exit /b
:m_ui_lecture_en
echo  Reading the original window layout ^(once only, a few minutes^)...
exit /b

:m_ui_echec_fr
echo.
echo  La lecture a echoue : details dans donnees\cache\ui_generation.log ^(menus simples pour cette fois^).
exit /b
:m_ui_echec_en
echo.
echo  Reading failed: details in donnees\cache\ui_generation.log ^(plain menus this time^).
exit /b

:m_ui_simple_fr
echo  Menus simples ^(pour les fenetres d'origine : lance d'abord tools\dump_il2cpp.bat^).
exit /b
:m_ui_simple_en
echo  Plain menus ^(for the original windows: run tools\dump_il2cpp.bat first^).
exit /b

:m_jeu_erreur_fr
echo.
echo  Le jeu s'est arrete sur une erreur ^(code %1^) : lis les lignes ci-dessus ^(details dans donnees\journaux^).
exit /b
:m_jeu_erreur_en
echo.
echo  The game stopped on an error ^(code %1^): read the lines above ^(details in donnees\journaux^).
exit /b
