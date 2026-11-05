@echo off
REM ============================================================================
REM  Build the Video 1 master on Windows. Double-click this file.
REM
REM  Why this exists: the documented commands are bash, and CMD breaks on the
REM  backslash line-continuations and on "python3" (which Windows resolves to a
REM  Microsoft Store stub). Everything here is one line, and uses "python".
REM
REM  If Python is missing, install it first:
REM    https://www.python.org/downloads/   (TICK "Add python.exe to PATH")
REM    or:  winget install Python.Python.3.12
REM ============================================================================
setlocal
cd /d "%~dp0"
title Video 1 build

where python >nul 2>&1
if errorlevel 1 goto nopython

echo.
echo [0/3] Installing dependencies...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
if errorlevel 1 goto faildeps

echo.
echo [1/3] Generating narration. This takes about 5 minutes and needs internet.
python tools\perform_script.py --spec specs\video1.json
if errorlevel 1 goto failtts

echo.
echo [2/3] Building the 1080p master. This takes about 3 minutes.
python tools\build_longform.py --spec specs\video1.json --audio out\perform\video-1-how-nokia-lost-everything\en-us-christopherneural.mp3 --chunks out\perform\video-1-how-nokia-lost-everything\en-us-christopherneural.chunks.json --out out\video\video1_master_1080p.mp4 --ken-burns
if errorlevel 1 goto failbuild

echo.
echo [3/3] Done. Opening the folder so you can double-click the MP4.
explorer "out\video"
echo.
echo   out\video\video1_master_1080p.mp4
pause
exit /b 0

:nopython
echo.
echo   Python was not found on this PC.
echo.
echo   1. Open https://www.python.org/downloads/
echo   2. Download Python 3.12 or newer
echo   3. IMPORTANT: tick "Add python.exe to PATH" on the first installer screen
echo   4. Close this window, open a NEW one, and double-click this file again
echo.
echo   If you already installed it, type:  python --version
echo   If that opens the Microsoft Store, disable the alias in
echo   Settings ^> Apps ^> Advanced app settings ^> App execution aliases.
echo.
pause
exit /b 1

:faildeps
echo.
echo   Dependency install failed. Check your internet connection and retry.
pause
exit /b 1

:failtts
echo.
echo   Narration failed. Most common causes:
echo     - no internet, or a firewall blocking the speech endpoint
echo     - a proxy that inspects TLS
echo   Paste the error above and it can be diagnosed.
pause
exit /b 1

:failbuild
echo.
echo   Video build failed. The likely cause is a missing narration file from step 1.
echo   Make sure step 1 printed an "OK" line before this step ran.
pause
exit /b 1
