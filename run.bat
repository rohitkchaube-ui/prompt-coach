@echo off
rem Double-click this file to start Prompt Coach on Windows.
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 launch.py %*
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo Python 3.10 or newer is required. Download it from https://www.python.org/downloads/
        echo During install, tick "Add python.exe to PATH".
        pause
        exit /b 1
    )
    python launch.py %*
)

rem Keep the window open if something went wrong, so the error can be read.
if errorlevel 1 pause
