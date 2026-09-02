@echo off
setlocal
title TardyTrack Development Server

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Python virtual environment was not found.
    echo Run: py -3.14 -m venv .venv
    exit /b 1
)

if not exist "react-ui\node_modules" (
    echo Installing frontend dependencies for the first run...
    call npm.cmd --prefix react-ui install --legacy-peer-deps
    if errorlevel 1 exit /b 1
)

echo Applying database migrations...
".venv\Scripts\python.exe" manage.py migrate
if errorlevel 1 exit /b 1

set "NODE_OPTIONS=--openssl-legacy-provider"
echo.
echo Starting TardyTrack...
echo Backend:  http://127.0.0.1:8000
echo Frontend: http://localhost:3000
echo Press Ctrl+C once to stop both servers.
echo.

call npm.cmd --prefix react-ui run system
