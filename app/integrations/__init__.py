"""Integration modules for Clipzy."""

from app.integrations.dashboard_integration import (
    DashboardIntegration,
    import_colab_analysis,
)

__all__ = [
    "DashboardIntegration",
    "import_colab_analysis",
]
