"""Storage service for managing video and output files."""

import shutil
from pathlib import Path
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.exceptions import StorageError
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class S3StorageService:
    """Handles S3 storage operations via AWS boto3."""

    def __init__(self):
        """Initialize S3 storage service."""
        try:
            self.s3_client = boto3.client(
                's3',
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )
            self.bucket_name = settings.S3_BUCKET_NAME
            self.prefix = settings.S3_UPLOADS_PREFIX
            
            # Verify bucket exists
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Connected to S3 bucket: {self.bucket_name}")
        except ClientError as e:
            logger.error(f"Failed to connect to S3: {str(e)}")
            raise StorageError(f"Failed to connect to S3: {str(e)}")

    def _get_s3_key(self, destination_folder: str, filename: str) -> str:
        """Generate S3 key for the file."""
        return f"{self.prefix}/{destination_folder}/{filename}"

    def save_file(self, file_path: Path, destination_folder: str) -> str:
        """
        Save a file to S3 storage.

        Args:
            file_path: Path to the source file
            destination_folder: Destination folder name (e.g., job_id)

        Returns:
            S3 URI of the saved file
        """
        try:
            s3_key = self._get_s3_key(destination_folder, file_path.name)
            
            self.s3_client.upload_file(
                str(file_path),
                self.bucket_name,
                s3_key,
                ExtraArgs={'ContentType': 'application/octet-stream'}
            )

            s3_uri = f"s3://{self.bucket_name}/{s3_key}"
            logger.info(
                f"File saved to S3",
                extra={"source": str(file_path), "s3_uri": s3_uri}
            )

            return s3_uri

        except Exception as e:
            logger.error(f"Failed to save file to S3: {str(e)}")
            raise StorageError(f"Failed to save file to S3: {str(e)}")

    def read_file(self, storage_path: str) -> bytes:
        """Read file from S3 storage."""
        try:
            if storage_path.startswith("s3://"):
                # Parse S3 URI
                parts = storage_path.replace("s3://", "").split("/", 1)
                bucket = parts[0]
                key = parts[1]
            else:
                bucket = self.bucket_name
                key = storage_path

            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            return response['Body'].read()

        except ClientError as e:
            logger.error(f"Failed to read file from S3: {str(e)}")
            raise StorageError(f"Failed to read file from S3: {str(e)}")

    def delete_file(self, storage_path: str) -> bool:
        """Delete file from S3 storage."""
        try:
            if storage_path.startswith("s3://"):
                parts = storage_path.replace("s3://", "").split("/", 1)
                bucket = parts[0]
                key = parts[1]
            else:
                bucket = self.bucket_name
                key = storage_path

            self.s3_client.delete_object(Bucket=bucket, Key=key)
            logger.info(f"File deleted from S3: {storage_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete file from S3: {str(e)}")
            raise StorageError(f"Failed to delete file from S3: {str(e)}")

    def delete_folder(self, destination_folder: str) -> bool:
        """Delete a folder and all its contents from S3."""
        try:
            prefix = self._get_s3_key(destination_folder, "")
            
            # List all objects with this prefix
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )

            if 'Contents' not in response:
                return False

            # Delete all objects
            for obj in response['Contents']:
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=obj['Key'])

            logger.info(f"Folder deleted from S3: {destination_folder}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete folder from S3: {str(e)}")
            raise StorageError(f"Failed to delete folder from S3: {str(e)}")

    def get_file_size(self, storage_path: str) -> int:
        """Get file size in bytes from S3."""
        try:
            if storage_path.startswith("s3://"):
                parts = storage_path.replace("s3://", "").split("/", 1)
                bucket = parts[0]
                key = parts[1]
            else:
                bucket = self.bucket_name
                key = storage_path

            response = self.s3_client.head_object(Bucket=bucket, Key=key)
            return response['ContentLength']

        except Exception as e:
            logger.error(f"Failed to get file size from S3: {str(e)}")
            raise StorageError(f"Failed to get file size from S3: {str(e)}")

    def get_download_url(self, storage_path: str, expiration: int = 3600) -> str:
        """Generate a presigned URL for downloading a file."""
        try:
            if storage_path.startswith("s3://"):
                parts = storage_path.replace("s3://", "").split("/", 1)
                bucket = parts[0]
                key = parts[1]
            else:
                bucket = self.bucket_name
                key = storage_path

            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=expiration
            )
            return url

        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {str(e)}")
            raise StorageError(f"Failed to generate presigned URL: {str(e)}")

    def upload(self, file_content: bytes, destination_folder: str, filename: str) -> str:
        """
        Upload file content directly to S3.

        Args:
            file_content: File content as bytes
            destination_folder: Destination folder name
            filename: Filename to save as

        Returns:
            S3 URI of the uploaded file
        """
        try:
            s3_key = self._get_s3_key(destination_folder, filename)
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType='application/octet-stream'
            )

            s3_uri = f"s3://{self.bucket_name}/{s3_key}"
            logger.info(
                f"File uploaded to S3",
                extra={"filename": filename, "s3_uri": s3_uri, "size": len(file_content)}
            )

            return s3_uri

        except Exception as e:
            logger.error(f"Failed to upload file to S3: {str(e)}")
            raise StorageError(f"Failed to upload file to S3: {str(e)}")


class LocalStorageService:
    """Handles local file storage operations."""

    def __init__(self):
        """Initialize storage service."""
        self.storage_path = settings.storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def save_file(self, file_path: Path, destination_folder: str) -> str:
        """
        Save a file to local storage.

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
                f"File saved to local storage",
                extra={"source": str(file_path), "destination": str(dest_path)}
            )

            return self._get_storage_url(dest_path)

        except Exception as e:
            logger.error(f"Failed to save file: {str(e)}")
            raise StorageError(f"Failed to save file: {str(e)}")

    def read_file(self, storage_path: str) -> bytes:
        """Read file from local storage."""
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
        """Delete file from local storage."""
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

    @staticmethod
    def _get_storage_url(file_path: Path) -> str:
        """Convert file path to storage URL."""
        return f"file:///{file_path.absolute()}"

    def upload(self, file_content: bytes, destination_folder: str, filename: str) -> str:
        """
        Upload file content to local storage.

        Args:
            file_content: File content as bytes
            destination_folder: Destination folder name
            filename: Filename to save as

        Returns:
            Local file path (storage URL)
        """
        try:
            dest_path = self.storage_path / destination_folder
            dest_path.mkdir(parents=True, exist_ok=True)
            
            file_path = dest_path / filename
            file_path.write_bytes(file_content)
            
            storage_url = self._get_storage_url(file_path)
            logger.info(
                f"File uploaded locally",
                extra={"filename": filename, "storage_url": storage_url, "size": len(file_content)}
            )
            
            return storage_url

        except Exception as e:
            logger.error(f"Failed to upload file locally: {str(e)}")
            raise StorageError(f"Failed to upload file locally: {str(e)}")


class StorageService:
    """Factory service for storage operations."""

    def __init__(self, storage_type: str = None):
        """Initialize storage service with appropriate backend."""
        storage_type = storage_type or settings.STORAGE_TYPE
        
        if storage_type == "s3":
            self._service = S3StorageService()
        else:
            self._service = LocalStorageService()

    def save_file(self, file_path: Path, destination_folder: str) -> str:
        """Save a file to storage."""
        return self._service.save_file(file_path, destination_folder)

    def read_file(self, storage_path: str) -> bytes:
        """Read file from storage."""
        return self._service.read_file(storage_path)

    def delete_file(self, storage_path: str) -> bool:
        """Delete file from storage."""
        return self._service.delete_file(storage_path)

    def delete_folder(self, destination_folder: str) -> bool:
        """Delete a folder and all its contents."""
        return self._service.delete_folder(destination_folder)

    def get_file_size(self, storage_path: str) -> int:
        """Get file size in bytes."""
        return self._service.get_file_size(storage_path)

    def upload(self, file_content: bytes, destination_folder: str, filename: str) -> str:
        """Upload file content to storage."""
        return self._service.upload(file_content, destination_folder, filename)

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
