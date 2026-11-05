@echo off
setlocal
cd /d "%~dp0"
title Extracting the game's C# code (research)
echo.
echo  Extracting the structure of the DQ4 C# code (classes, fields, methods)
echo  ------------------------------------------------------------------------
echo  Reads your APK files in ..\data\apk (never modified).
echo  Result: ..\data\cache\il2cpp\dump.cs  (stays on your PC, not sent to GitHub).
echo  Needs internet the first time (Il2CppDumper, and .NET if missing).
echo.
if not exist "..\.venv\Scripts\python.exe" (
  echo  First run launch_dq4.bat ^(at the project root^) once to create the Python environment.
  pause
  exit /b 1
)

rem --- .NET est necessaire a Il2CppDumper : installation automatique s'il manque
set "DOTNET="
where dotnet >nul 2>nul && set "DOTNET=1"
if exist "%ProgramFiles%\dotnet\dotnet.exe" set "DOTNET=1"
if not defined DOTNET (
  echo  .NET is missing: automatic installation, one time only.
  echo  Accept the Windows prompt that may appear ^(authorization^).
  echo.
  winget install --id Microsoft.DotNet.Runtime.8 -e --accept-package-agreements --accept-source-agreements
  if errorlevel 1 (
    echo.
    echo  The automatic installation failed. Install it by hand:
    echo     https://dotnet.microsoft.com/download/dotnet/8.0  ^(".NET Runtime", Windows x64^)
    echo  then run this file again.
    pause
    exit /b 1
  )
  echo.
  echo  .NET installed.
)

"..\.venv\Scripts\python.exe" dump_il2cpp.py %*
echo.
pause
