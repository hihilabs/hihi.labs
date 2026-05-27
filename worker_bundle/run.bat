@echo off
title HiHi Agent Worker
cd /d "%~dp0"

echo.
echo  ==========================================
echo   HiHi Agent Worker — Setup ^& Launch
echo  ==========================================
echo.

:: Remove stale .env from old installs (config.env takes precedence)
if exist ".env" del /f ".env"

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found.
    echo.
    echo  Install Python 3.11 from: https://www.python.org/downloads/
    echo  Check "Add Python to PATH" during install, then re-run this.
    echo.
    pause
    exit /b 1
)

:: Create venv if it doesn't exist
if not exist "venv\" (
    echo  Setting up for the first time...
    echo  ^(this takes a minute, only happens once^)
    echo.
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -q -r requirements-windows.txt
    echo.
    echo  Done! Launching worker...
) else (
    call venv\Scripts\activate.bat
)

:: Local job/photo dirs — no admin needed
if not exist "jobs\" mkdir jobs
if not exist "photos\" mkdir photos

echo.
python worker.py

pause
