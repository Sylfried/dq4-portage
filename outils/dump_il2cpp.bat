@echo off
setlocal
cd /d "%~dp0"
title Extraction du code C# du jeu (recherche)
echo.
echo  Extraction de la structure du code C# de DQ4 (classes, champs, methodes)
echo  ------------------------------------------------------------------------
echo  Lit tes APK dans ..\..\jeux\DQ4\patched_apks (jamais modifies).
echo  Resultat : ..\dq4_pc\cache\il2cpp\dump.cs  (reste sur ton PC, pas envoye sur GitHub).
echo  Necessite internet la premiere fois (Il2CppDumper, et .NET s'il manque).
echo.
if not exist "..\dq4_pc\.venv\Scripts\python.exe" (
  echo  Lance d'abord dq4_pc\lancer_dq4.bat une fois pour creer l'environnement Python.
  pause
  exit /b 1
)

rem --- .NET est necessaire a Il2CppDumper : installation automatique s'il manque
set "DOTNET="
where dotnet >nul 2>nul && set "DOTNET=1"
if exist "%ProgramFiles%\dotnet\dotnet.exe" set "DOTNET=1"
if not defined DOTNET (
  echo  .NET est absent : installation automatique, une seule fois.
  echo  Accepte la fenetre Windows qui peut s'afficher ^(autorisation^).
  echo.
  winget install --id Microsoft.DotNet.Runtime.8 -e --accept-package-agreements --accept-source-agreements
  if errorlevel 1 (
    echo.
    echo  L'installation automatique a echoue. Installe-le a la main :
    echo     https://dotnet.microsoft.com/download/dotnet/8.0  ^(".NET Runtime", Windows x64^)
    echo  puis relance ce fichier.
    pause
    exit /b 1
  )
  echo.
  echo  .NET installe.
)

"..\dq4_pc\.venv\Scripts\python.exe" dump_il2cpp.py %*
echo.
pause
