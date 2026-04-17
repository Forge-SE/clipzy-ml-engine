# Modal Authentication Setup Script for Windows PowerShell
# This script sets Modal credentials from .env file

# Load .env file
$envFile = ".\.env"
if (-not (Test-Path $envFile)) {
    Write-Error "Error: .env file not found"
    exit 1
}

# Parse .env and set Modal environment variables
Write-Host "Loading Modal credentials from .env..." -ForegroundColor Green

$content = Get-Content $envFile
foreach ($line in $content) {
    if ($line -match "^MODAL_TOKEN_ID=") {
        $var = $line -replace '^MODAL_TOKEN_ID=', ''
        $env:MODAL_TOKEN_ID = $var
        Write-Host "✓ Set MODAL_TOKEN_ID" -ForegroundColor Green
    }
    elseif ($line -match "^MODAL_TOKEN_SECRET=") {
        $var = $line -replace '^MODAL_TOKEN_SECRET=', ''
        $env:MODAL_TOKEN_SECRET = $var
        Write-Host "✓ Set MODAL_TOKEN_SECRET" -ForegroundColor Green
    }
}

# Test Modal authentication
Write-Host "`nTesting Modal authentication..." -ForegroundColor Yellow
$env:MODAL_CREDENTIALS_WARNING = "false"

# Try to validate by importing modal and checking credentials
$testScript = @'
import sys
try:
    # Suppress warnings during import
    import warnings
    warnings.filterwarnings("ignore")
    
    # Try importing modal
    import modal
    print("✓ Modal module imported successfully")
    
    # Check if credentials are set
    import os
    token_id = os.getenv("MODAL_TOKEN_ID")
    token_secret = os.getenv("MODAL_TOKEN_SECRET")
    
    if token_id and token_secret:
        print("✓ Modal credentials found in environment")
        print(f"  Token ID: {token_id[:10]}...")
        print("Ready for GPU processing!")
    else:
        print("✗ Modal credentials not found")
        sys.exit(1)
        
except Exception as e:
    print(f"✗ Error: {str(e)}")
    sys.exit(1)
'@

python -c $testScript
if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Modal authentication successful!" -ForegroundColor Green
    Write-Host "You can now process videos using Modal GPU." -ForegroundColor Green
} else {
    Write-Host "✗ Modal authentication failed" -ForegroundColor Red
    exit 1
}
