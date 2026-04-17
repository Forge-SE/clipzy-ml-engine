@echo off
REM Migrate Clipzy infrastructure from Python 3.13 to Python 3.12
REM This script helps set up a new Python 3.12 virtual environment

setlocal enabledelayedexpansion

echo.
echo ========================================
echo Python 3.12 Migration Script
echo ========================================
echo.

REM Check if Python 3.12 is installed globally
echo [1/5] Checking for Python 3.12...
python3.12 --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ❌ Python 3.12 not found!
    echo.
    echo Please download and install Python 3.12 from:
    echo   https://www.python.org/downloads/release/python-3123/
    echo.
    echo During installation, make sure to:
    echo   - Check "Add Python to PATH"
    echo   - Check "Install pip"
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python3.12 --version') do set PY_VERSION=%%i
echo ✓ Found: !PY_VERSION!
echo.

REM Step 2: Backup current venv
echo [2/5] Backing up current environment...
if exist venv (
    if exist venv_backup_py313 (
        rmdir /s /q venv_backup_py313 >nul 2>&1
    )
    move venv venv_backup_py313 >nul 2>&1
    echo ✓ Current venv backed up to venv_backup_py313
) else (
    echo ⚠ No existing venv found, skipping backup
)
echo.

REM Step 3: Create new Python 3.12 venv
echo [3/5] Creating Python 3.12 virtual environment...
python3.12 -m venv venv
if errorlevel 1 (
    echo ❌ Failed to create venv
    exit /b 1
)
echo ✓ Virtual environment created
echo.

REM Step 4: Activate and upgrade pip
echo [4/5] Upgrading pip and installing dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip wheel setuptools >nul 2>&1
echo ✓ pip upgraded
echo.

REM Step 5: Install requirements
echo [5/5] Installing requirements.txt...
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ❌ Some packages failed to install
    echo    This may be expected for some packages
    echo    Continue anyway? (Y/N)
    set /p choice=
    if /i not "!choice!"=="Y" exit /b 1
)
echo.
echo ✓ Requirements installed
echo.

REM Summary
echo.
echo ========================================
echo ✅ Migration Complete!
echo ========================================
echo.
echo Your environment is now running Python 3.12
echo.
echo Next steps:
echo.
echo 1. Verify the setup:
echo    python --version
echo.
echo 2. Test Modal GPU:
echo    python run_modal_worker.py
echo.
echo 3. Start the API:
echo    python main.py
echo.
echo 4. (Optional) Cleanup old environment:
echo    rmdir /s venv_backup_py313
echo.

echo.
echo ✨ Ready to use Modal GPU with Python 3.12!
echo.
pause
