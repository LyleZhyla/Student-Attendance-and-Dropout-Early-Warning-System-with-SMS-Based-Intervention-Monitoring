@echo off
setlocal
title TardyTrack Development Server

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Python virtual environment was not found.
    echo Run: py -3.14 -m venv .venv
    exit /b 1
)

set "NPM_CLI=%ProgramFiles%\nodejs\node_modules\npm\bin\npm-cli.js"

if not exist "react-ui\node_modules" (
    echo Installing frontend dependencies for the first run...
    if exist "%NPM_CLI%" (
        node "%NPM_CLI%" --prefix react-ui install --legacy-peer-deps
    ) else (
        call npm.cmd --prefix react-ui install --legacy-peer-deps
    )
    if errorlevel 1 exit /b 1
)

if not exist "react-ui\build\index.html" (
    echo Building the TardyTrack interface...
    set "NODE_OPTIONS=--openssl-legacy-provider"
    if exist "%NPM_CLI%" (
        node "%NPM_CLI%" --prefix react-ui run build
    ) else (
        call npm.cmd --prefix react-ui run build
    )
    if errorlevel 1 exit /b 1
)

echo Applying database migrations...
".venv\Scripts\python.exe" manage.py migrate
if errorlevel 1 exit /b 1

echo.
echo Starting TardyTrack...
echo Open: http://localhost:3000
echo Press Ctrl+C to stop the server.
echo.

".venv\Scripts\python.exe" manage.py runserver 127.0.0.1:3000
