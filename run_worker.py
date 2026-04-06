"""Run a video processing worker."""

import argparse

from app.workers import run_worker


def main():
    """Entry point for running workers."""
    parser = argparse.ArgumentParser(description="Run a video processing worker")
    parser.add_argument(
        "--worker-id",
        default="worker-1",
        help="Unique identifier for this worker"
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=5,
        help="Seconds to wait between queue checks"
    )

    args = parser.parse_args()

    run_worker(
        worker_id=args.worker_id,
        poll_interval=args.poll_interval,
    )


if __name__ == "__main__":
    main()
