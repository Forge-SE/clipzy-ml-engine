@echo off
REM setup-modal-infrastructure.bat - Automated setup for Modal, S3, and RabbitMQ (Windows)

setlocal enabledelayedexpansion

echo.
echo ========================================
echo Clipzy Modal Infrastructure Setup
echo ========================================
echo.

REM 1. Check Python version
echo [1/7] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.9+
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python !PYTHON_VERSION! found
echo.

REM 2. Install dependencies
echo [2/7] Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    exit /b 1
)
echo [OK] Dependencies installed
echo.

REM 3. Install Modal CLI
echo [3/7] Installing Modal CLI...
pip install modal
if errorlevel 1 (
    echo ERROR: Failed to install Modal CLI
    exit /b 1
)
echo [OK] Modal CLI installed
echo.

REM 4. Setup Modal authentication
echo [4/7] Setting up Modal authentication...
echo Opening browser for Modal authentication...
python -m modal setup
if errorlevel 1 (
    echo ERROR: Modal setup failed
    exit /b 1
)
echo [OK] Modal authentication configured
echo.

REM 5. Start Docker services
echo [5/7] Starting RabbitMQ and Redis with Docker...
where docker >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker not found. Please install Docker Desktop for Windows.
    exit /b 1
)

docker-compose up -d
if errorlevel 1 (
    echo ERROR: Failed to start Docker services
    exit /b 1
)
echo [OK] RabbitMQ and Redis started
echo.

REM 6. Wait for services to be ready
echo [6/7] Waiting for services to be ready...
timeout /t 5 /nobreak
echo [OK] Services ready
echo.

REM 7. Display next steps
echo [7/7] Configuration Complete
echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Update .env with your AWS credentials:
echo    - AWS_ACCESS_KEY_ID
echo    - AWS_SECRET_ACCESS_KEY
echo    - S3_BUCKET_NAME
echo.
echo 2. Start the API server:
echo    python main.py
echo.
echo 3. Access services:
echo    - RabbitMQ: http://localhost:15672 (guest/guest)
echo    - Redis: http://localhost:8081
echo.
echo 4. Process a video using Modal GPU:
echo    python -m modal run app.workers.modal_worker::process_job
echo.
echo For detailed documentation, see: MODAL_SETUP.md
echo.

endlocal
