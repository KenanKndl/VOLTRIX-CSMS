@echo off
setlocal enabledelayedexpansion

:: === CONFIG ===
set VENV_PATH=%~dp0.venv\Scripts\activate
set BACKEND_DIR=app\backend
set FRONTEND_FILE=app\frontend\src\index.html
set BACKEND_CMD=python -m uvicorn main:app --reload

:: === CHECK VENV ===
echo 🔍 Checking virtual environment...
if not exist "%VENV_PATH%" (
    echo ❌ ERROR: Virtual environment not found at %VENV_PATH%
    echo 💡 Make sure you've created one using: python -m venv .venv
    pause
    exit /b
)

:: === ACTIVATE VENV ===
echo ✅ Activating virtual environment...
call "%VENV_PATH%"

:: === START BACKEND ===
echo 🚀 Starting backend server...
cd %BACKEND_DIR%
start "FastAPI Backend" cmd /k %BACKEND_CMD%
cd ..\..

:: === WAIT ===
timeout /t 2 > nul

:: === OPEN FRONTEND ===
echo 🌐 Opening frontend page...
if exist "%FRONTEND_FILE%" (
    start "" "%cd%\%FRONTEND_FILE%"
) else (
    echo ⚠️ Frontend file not found: %FRONTEND_FILE%
)

:: === DONE ===
echo ✅ All systems started successfully.
exit
