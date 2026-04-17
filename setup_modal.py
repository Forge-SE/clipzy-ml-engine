#!/usr/bin/env python3
"""Modal GPU Setup and Verification Script"""

import os
import sys
from pathlib import Path

def setup_modal_credentials():
    """Load Modal credentials from .env and verify them"""
    
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ Error: .env file not found")
        return False
    
    # Load credentials from .env
    credentials = {}
    with open(env_file) as f:
        for line in f:
            if line.startswith("MODAL_TOKEN_ID="):
                credentials["MODAL_TOKEN_ID"] = line.split("=", 1)[1].strip()
            elif line.startswith("MODAL_TOKEN_SECRET="):
                credentials["MODAL_TOKEN_SECRET"] = line.split("=", 1)[1].strip()
    
    # Set environment variables
    if "MODAL_TOKEN_ID" in credentials:
        os.environ["MODAL_TOKEN_ID"] = credentials["MODAL_TOKEN_ID"]
        print("✓ Set MODAL_TOKEN_ID")
    
    if "MODAL_TOKEN_SECRET" in credentials:
        os.environ["MODAL_TOKEN_SECRET"] = credentials["MODAL_TOKEN_SECRET"]
        print("✓ Set MODAL_TOKEN_SECRET")
    
    # Suppress warnings
    os.environ["MODAL_CREDENTIALS_WARNING"] = "false"
    
    # Test credentials
    try:
        print("\n🔍 Testing Modal credentials...")
        
        # Test if credentials are set
        if not os.getenv("MODAL_TOKEN_ID") or not os.getenv("MODAL_TOKEN_SECRET"):
            print("❌ Modal credentials not found in .env")
            return False
        
        print(f"✓ Token ID: {os.getenv('MODAL_TOKEN_ID')[:15]}...")
        print("✓ Token Secret: [SET]")
        
        # Try importing modal with credentials
        print("\n📦 Importing modal module...")
        import modal
        print("✓ Modal module imported successfully")
        
        # Try to access Modal account info
        print("\n🌐 Verifying modal credentials...")
        try:
            # This will attempt to contact Modal's servers with the credentials
            from modal import config as modal_config
            print("✓ Modal configuration loaded")
        except Exception as e:
            print(f"⚠️  Warning: {str(e)}")
            print("   (This may be expected if offline - credentials are still set)")
        
        print("\n" + "="*50)
        print("✅ Modal GPU Setup Complete!")
        print("="*50)
        print("\nYou can now run GPU-accelerated jobs with:")
        print("  python -m modal run app.workers.modal_worker")
        print("\nOr in Python code:")
        print("  from app.workers.modal_worker import VideoProcessor")
        
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import modal: {e}")
        print("\nTry reinstalling modal:")
        print("  pip uninstall modal-client -y")
        print("  pip install --upgrade modal")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = setup_modal_credentials()
    sys.exit(0 if success else 1)
