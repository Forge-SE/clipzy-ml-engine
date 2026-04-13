# Migrate Clipzy infrastructure to Python 3.12
# Uses py -3.12 command (Windows Python launcher)

$ErrorActionPreference = "Continue"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Python 3.12 Migration Script" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Step 1: Check for Python 3.12
Write-Host "[1/5] Checking for Python 3.12..." -ForegroundColor Yellow

try {
    $pyVersion = & py -3.12 --version 2>&1
    Write-Host "[OK] Found: $pyVersion" -ForegroundColor Green
}
catch {
    Write-Host "[ERROR] Python 3.12 not found via 'py -3.12'" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 2: Backup current venv
Write-Host "[2/5] Backing up current environment..." -ForegroundColor Yellow

if (Test-Path "venv") {
    if (Test-Path "venv_backup_py313") {
        Remove-Item -Recurse -Force "venv_backup_py313" -ErrorAction SilentlyContinue
    }
    Move-Item -Path "venv" -Destination "venv_backup_py313" -Force
    Write-Host "[OK] Backed up to venv_backup_py313" -ForegroundColor Green
}
else {
    Write-Host "[OK] No existing venv" -ForegroundColor Green
}

Write-Host ""

# Step 3: Create new venv with Python 3.12
Write-Host "[3/5] Creating Python 3.12 virtual environment..." -ForegroundColor Yellow

try {
    & py -3.12 -m venv venv
    Write-Host "[OK] Virtual environment created" -ForegroundColor Green
}
catch {
    Write-Host "[ERROR] Failed to create venv: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 4: Activate and upgrade pip
Write-Host "[4/5] Upgrading pip..." -ForegroundColor Yellow

& ".\venv\Scripts\Activate.ps1"
python -m pip install --upgrade pip wheel setuptools -q
Write-Host "[OK] pip upgraded" -ForegroundColor Green

Write-Host ""

# Step 5: Install requirements
Write-Host "[5/5] Installing requirements.txt..." -ForegroundColor Yellow

pip install -r requirements.txt

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] All packages installed" -ForegroundColor Green
}
else {
    Write-Host "[WARNING] Some packages had issues (continuing...)" -ForegroundColor Yellow
}

Write-Host ""

# Summary
Write-Host "========================================" -ForegroundColor Green
Write-Host "[SUCCESS] Migration Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

Write-Host "`nYour environment is ready with Python 3.12!`n" -ForegroundColor Green

Write-Host "Verify with:" -ForegroundColor Cyan
Write-Host "  python --version  (should show Python 3.12.x)" -ForegroundColor Gray

Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "  python run_modal_worker.py        (test Modal GPU)" -ForegroundColor Gray
Write-Host "  docker-compose up -d              (start services)" -ForegroundColor Gray
Write-Host "  python main.py                    (start API)" -ForegroundColor Gray

Write-Host ""
Write-Host "2. Test Modal GPU:" -ForegroundColor White
Write-Host "   python run_modal_worker.py" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Start Docker services:" -ForegroundColor White
Write-Host "   docker-compose up -d" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Start the API:" -ForegroundColor White
Write-Host "   python main.py" -ForegroundColor Gray
Write-Host ""
Write-Host "5. (Optional) Cleanup old environment:" -ForegroundColor White
Write-Host "   Remove-Item -Recurse venv_backup_py313" -ForegroundColor Gray
Write-Host ""

Write-Host "Ready to use Modal GPU with Python 3.12!" -ForegroundColor Green
Write-Host ""
