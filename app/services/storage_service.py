"""Storage service for managing video and output files."""

import shutil
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.core.exceptions import StorageError
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class StorageService:
    """Handles file storage operations."""

    def __init__(self, storage_type: str = "local"):
        """Initialize storage service."""
        self.storage_type = storage_type
        if storage_type == "local":
            self.storage_path = settings.storage_path
            self.storage_path.mkdir(parents=True, exist_ok=True)

    def save_file(self, file_path: Path, destination_folder: str) -> str:
        """
        Save a file to storage.

        Args:
            file_path: Path to the source file
            destination_folder: Destination folder name (e.g., job_id)

        Returns:
            Storage path/URL of the saved file
        """
        try:
            dest_dir = self.storage_path / destination_folder
            dest_dir.mkdir(parents=True, exist_ok=True)

            dest_path = dest_dir / file_path.name
            shutil.copy2(file_path, dest_path)

            logger.info(
                f"File saved to storage",
                extra={"source": str(file_path), "destination": str(dest_path)}
            )

            return self._get_storage_url(dest_path)

        except Exception as e:
            logger.error(f"Failed to save file: {str(e)}")
            raise StorageError(f"Failed to save file: {str(e)}")

    def read_file(self, storage_path: str) -> bytes:
        """Read file from storage."""
        try:
            # Convert storage URL back to path
            path = Path(storage_path.replace("file:///", "").replace("file://", ""))
            if not path.exists():
                raise FileNotFoundError(f"File not found: {path}")

            return path.read_bytes()

        except Exception as e:
            logger.error(f"Failed to read file: {str(e)}")
            raise StorageError(f"Failed to read file: {str(e)}")

    def delete_file(self, storage_path: str) -> bool:
        """Delete file from storage."""
        try:
            path = Path(storage_path.replace("file:///", "").replace("file://", ""))
            if path.exists():
                path.unlink()
                logger.info(f"File deleted: {storage_path}")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to delete file: {str(e)}")
            raise StorageError(f"Failed to delete file: {str(e)}")

    def delete_folder(self, destination_folder: str) -> bool:
        """Delete a folder and all its contents."""
        try:
            folder_path = self.storage_path / destination_folder
            if folder_path.exists():
                shutil.rmtree(folder_path)
                logger.info(f"Folder deleted: {destination_folder}")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to delete folder: {str(e)}")
            raise StorageError(f"Failed to delete folder: {str(e)}")

    def get_file_size(self, storage_path: str) -> int:
        """Get file size in bytes."""
        try:
            path = Path(storage_path.replace("file:///", "").replace("file://", ""))
            return path.stat().st_size

        except Exception as e:
            logger.error(f"Failed to get file size: {str(e)}")
            raise StorageError(f"Failed to get file size: {str(e)}")

    def _get_storage_url(self, path: Path) -> str:
        """Convert a local path to a storage URL."""
        # For local storage, use file:// URL
        return f"file:///{path.as_posix()}"


# Global storage service instance
_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Get or create the storage service instance."""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService(storage_type=settings.STORAGE_TYPE)
    return _storage_service
