"""Progress tracking and display utilities."""

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Optional
import time


class StepStatus(Enum):
    """Status of a pipeline step."""
    PENDING = "⏳"
    IN_PROGRESS = "▶️ "
    COMPLETED = "✅"
    FAILED = "❌"
    SKIPPED = "⏭️ "


@dataclass
class StepMetrics:
    """Metrics for a pipeline step."""
    name: str
    status: StepStatus = StepStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    details: dict = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def duration(self) -> Optional[float]:
        """Get duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    def start(self):
        """Mark step as started."""
        self.status = StepStatus.IN_PROGRESS
        self.start_time = datetime.now()

    def complete(self, details: dict = None):
        """Mark step as completed."""
        self.status = StepStatus.COMPLETED
        self.end_time = datetime.now()
        if details:
            self.details.update(details)

    def skip(self):
        """Mark step as skipped."""
        self.status = StepStatus.SKIPPED
        self.end_time = datetime.now()

    def fail(self, error: str):
        """Mark step as failed."""
        self.status = StepStatus.FAILED
        self.end_time = datetime.now()
        self.error = error


class ProgressTracker:
    """Tracks progress of pipeline steps with nice terminal output."""

    def __init__(self, total_steps: int = 8):
        """
        Initialize progress tracker.

        Args:
            total_steps: Total number of steps in pipeline
        """
        self.total_steps = total_steps
        self.steps: list[StepMetrics] = []
        self.current_step_index = 0

    def add_step(self, name: str) -> StepMetrics:
        """
        Add a new step to track.

        Args:
            name: Name of the step

        Returns:
            StepMetrics object
        """
        step = StepMetrics(name=name)
        self.steps.append(step)
        return step

    def print_header(self, title: str = "Video Analysis Pipeline"):
        """Print header."""
        print(f"\n{'='*70}")
        print(f"{title:^70}")
        print(f"{'='*70}\n")

    def print_step_header(self, step_num: int, step_name: str):
        """Print step header."""
        print(f"\n[{step_num}/{self.total_steps}] {step_name}")
        print("-" * 70)

    def print_detail(self, key: str, value: str, padding: int = 20):
        """Print detail line."""
        print(f"  {key:<{padding}} {value}")

    def print_summary(self):
        """Print summary table."""
        print(f"\n{'='*70}")
        print(f"Analysis Summary")
        print(f"{'='*70}\n")

        # Header
        print(
            f"{'Step':<30} {'Status':<15} {'Duration':<15}"
        )
        print("-" * 70)

        # Rows
        for i, step in enumerate(self.steps, 1):
            duration_str = (
                f"{step.duration:.2f}s" if step.duration else "N/A"
            )
            status_str = f"{step.status.value} {step.status.name}"

            print(
                f"{step.name:<30} {status_str:<15} {duration_str:<15}"
            )

            # Print details if available
            if step.details:
                for key, value in step.details.items():
                    print(f"    ├─ {key}: {value}")

            # Print error if failed
            if step.error:
                print(f"    └─ Error: {step.error}")

        # Total time
        total_duration = sum(
            step.duration for step in self.steps if step.duration
        )
        print("-" * 70)
        print(f"{'Total Duration':<30} {total_duration:.2f}s" if total_duration else "")
        print(f"{'='*70}\n")

    def print_current_step(self):
        """Print status of current step."""
        if self.current_step_index < len(self.steps):
            step = self.steps[self.current_step_index]
            print(f"\n{step.status.value} {step.name}")
            if step.error:
                print(f"   Error: {step.error}")

    def get_step(self, index: int) -> Optional[StepMetrics]:
        """Get step by index."""
        if 0 <= index < len(self.steps):
            return self.steps[index]
        return None

    def get_step_by_name(self, name: str) -> Optional[StepMetrics]:
        """Get step by name."""
        for step in self.steps:
            if step.name == name:
                return step
        return None
