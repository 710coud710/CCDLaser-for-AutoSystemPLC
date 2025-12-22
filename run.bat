@echo off
REM CCDLaser - Quick Run Script
REM Double-click this file to run the application

echo ========================================
echo CCDLaser - Camera Control System
echo ========================================
echo.

REM Change to script directory
cd /d "%~dp0"

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found!
    echo Please run: python -m venv venv
    echo Then run: venv\Scripts\activate
    echo Then run: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate

REM Check if dependencies installed
python -c "import PySide6" 2>nul
if errorlevel 1 (
    echo [ERROR] Dependencies not installed!
    echo Please run: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Run application
echo Starting CCDLaser...
echo.
python main.py

REM Deactivate on exit
deactivate

echo.
echo Application closed.
pause

