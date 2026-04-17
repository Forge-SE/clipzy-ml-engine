"""
Integration module for sending Colab analysis results to Render Watch dashboard.

Usage:
    1. Run analysis in Colab
    2. Download the JSON results
    3. Upload to dashboard using this script
    4. Or configure webhook for automatic updates
"""

import json
import requests
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class DashboardIntegration:
    """Send analysis results to Render Watch dashboard."""

    def __init__(self, dashboard_url: str = "http://localhost:8000/api/v1"):
        """
        Initialize dashboard integration.

        Args:
            dashboard_url: Base URL of the Render Watch API
        """
        self.dashboard_url = dashboard_url.rstrip("/")
        self.session = requests.Session()

    def send_analysis_results(
        self,
        analysis_json: Dict[str, Any],
        job_id: Optional[str] = None,
        source: str = "colab-gpu",
    ) -> Dict[str, Any]:
        """
        Send analysis results to dashboard.

        Args:
            analysis_json: Analysis results dictionary (from StyleDNA.to_dict())
            job_id: Optional job ID (defaults to timestamp)
            source: Source identifier (e.g., "colab-gpu", "local-cpu")

        Returns:
            Dashboard response with status
        """
        if not job_id:
            job_id = f"{source}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        try:
            # Prepare payload
            payload = {
                "job_id": job_id,
                "status": "complete",
                "stage": "complete",
                "analysis": analysis_json,
                "metadata": {
                    "source": source,
                    "completed_at": datetime.now().isoformat(),
                },
            }

            # Send to dashboard
            endpoint = f"{self.dashboard_url}/jobs/{job_id}"
            logger.info(f"Sending analysis to dashboard: {endpoint}")

            response = self.session.post(
                endpoint,
                json=payload,
                timeout=30,
            )

            if response.status_code in (200, 201, 202):
                logger.info(f"✅ Successfully sent to dashboard (Job: {job_id})")
                return {
                    "success": True,
                    "job_id": job_id,
                    "status_code": response.status_code,
                    "message": f"Results sent to {self.dashboard_url}",
                }
            else:
                logger.warning(f"Dashboard returned: {response.status_code}")
                return {
                    "success": False,
                    "job_id": job_id,
                    "status_code": response.status_code,
                    "error": response.text,
                }

        except requests.exceptions.ConnectionError:
            logger.warning(f"Cannot connect to dashboard at {self.dashboard_url}")
            return {
                "success": False,
                "error": f"Connection refused: {self.dashboard_url}",
                "suggestion": "Ensure your FastAPI server is running",
            }
        except Exception as e:
            logger.error(f"Failed to send to dashboard: {str(e)}")
            return {
                "success": False,
                "error": str(e),
            }

    def load_colab_json(self, json_file: Path) -> Dict[str, Any]:
        """
        Load analysis results from Colab JSON export.

        Args:
            json_file: Path to JSON file from Colab

        Returns:
            Parsed analysis dictionary
        """
        with open(json_file, "r") as f:
            return json.load(f)

    def import_colab_results(
        self,
        json_file: Path,
        dashboard_url: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Import analysis results from Colab JSON and send to dashboard.

        Args:
            json_file: Path to JSON file from Colab
            dashboard_url: Optional custom dashboard URL
            job_id: Optional job ID for dashboard

        Returns:
            Result status dictionary
        """
        if dashboard_url:
            self.dashboard_url = dashboard_url

        logger.info(f"Importing Colab results from: {json_file}")

        if not json_file.exists():
            return {
                "success": False,
                "error": f"File not found: {json_file}",
            }

        try:
            analysis = self.load_colab_json(json_file)
            logger.info(f"Loaded analysis: {len(json.dumps(analysis))} bytes")

            result = self.send_analysis_results(
                analysis,
                job_id=job_id,
                source="colab-gpu",
            )

            if result["success"]:
                print(f"\n✅ Successfully imported Colab results to dashboard!")
                print(f"   Job ID: {result['job_id']}")
                print(f"   Dashboard: {self.dashboard_url}")
            else:
                print(f"\n⚠️  Could not reach dashboard: {result.get('error')}")
                print(f"   You can still view the JSON file locally")

            return result

        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Invalid JSON file: {str(e)}",
            }


def import_colab_analysis(
    json_file: str | Path,
    dashboard_url: str = "http://localhost:8000/api/v1",
) -> Dict[str, Any]:
    """
    Convenience function to import Colab results.

    Usage:
        result = import_colab_analysis("video_analysis.json")
        print(result)

    Args:
        json_file: Path to analysis JSON from Colab
        dashboard_url: Dashboard base URL

    Returns:
        Import result status
    """
    json_path = Path(json_file)
    integrator = DashboardIntegration(dashboard_url)
    return integrator.import_colab_results(json_path)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        json_path = sys.argv[1]
        dashboard = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8000/api/v1"
        result = import_colab_analysis(json_path, dashboard)
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python -m app.integrations.dashboard_integration <json_file> [dashboard_url]")
        print("Example: python -m app.integrations.dashboard_integration video_analysis.json")
