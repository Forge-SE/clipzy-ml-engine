#!/usr/bin/env python3
"""
Import Colab analysis results to Render Watch dashboard.

Usage:
    python import_from_colab.py video_analysis.json
    python import_from_colab.py video_analysis.json http://localhost:8000/api/v1
"""

import sys
import json
from pathlib import Path
from typing import Optional

from app.integrations.dashboard_integration import DashboardIntegration
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def main():
    """Import Colab results to dashboard."""
    
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    json_file = Path(sys.argv[1])
    dashboard_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8000/api/v1"

    # Validate file
    if not json_file.exists():
        print(f"❌ File not found: {json_file}")
        return 1

    if not json_file.suffix == ".json":
        print(f"❌ Not a JSON file: {json_file}")
        return 1

    print(f"\n{'='*70}")
    print(f"Importing Colab Analysis Results")
    print(f"{'='*70}")
    print(f"File: {json_file.name} ({json_file.stat().st_size / 1024:.1f} KB)")
    print(f"Dashboard: {dashboard_url}")
    print(f"{'='*70}\n")

    # Load and validate JSON
    try:
        with open(json_file, "r") as f:
            analysis = json.load(f)
        
        print(f"✓ Loaded JSON analysis")
        
        # Show preview
        if "metadata" in analysis:
            meta = analysis["metadata"]
            print(f"  • Duration: {meta.get('duration', 'N/A'):.1f}s")
            print(f"  • Resolution: {meta.get('resolution', 'N/A')}")
        
        if "cuts" in analysis:
            print(f"  • Shots: {len(analysis.get('cuts', []))}")
        
        if "pacing" in analysis:
            pacing = analysis.get("pacing", {})
            print(f"  • Pacing: {pacing.get('type', 'N/A')} ({pacing.get('avg_shot_duration', 0):.1f}s avg)")
        
        print()

    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {str(e)}")
        return 1
    except Exception as e:
        print(f"❌ Error reading file: {str(e)}")
        return 1

    # Send to dashboard
    print("Sending to dashboard...")
    integrator = DashboardIntegration(dashboard_url)
    
    try:
        result = integrator.send_analysis_results(
            analysis,
            source="colab-gpu",
        )

        if result["success"]:
            print(f"\n✅ SUCCESS!")
            print(f"   Job ID: {result['job_id']}")
            print(f"   Dashboard: {dashboard_url}")
            print(f"\n📊 Open your dashboard to view results:")
            print(f"   {dashboard_url.rsplit('/api', 1)[0]}")
            print()
            return 0
        else:
            print(f"\n⚠️  Could not reach dashboard")
            print(f"   Error: {result.get('error', 'Unknown error')}")
            print(f"\n💡 Make sure your server is running:")
            print(f"   python app/main.py")
            print()
            return 1

    except Exception as e:
        print(f"\n❌ Failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
