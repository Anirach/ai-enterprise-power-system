"""
AI Power System - MinIO Object Storage Service
Handles file upload, download, and deletion in MinIO
"""
import os
import io
import uuid
from typing import Optional, BinaryIO
from datetime import timedelta
import logging

from minio import Minio
from minio.error import S3Error

logger = logging.getLogger(__name__)


class MinIOService:
    """Service for interacting with MinIO object storage"""
    
    def __init__(
        self,
        endpoint: str = None,
        access_key: str = None,
        secret_key: str = None,
        bucket_name: str = None,
        secure: bool = False
    ):
        self.endpoint = endpoint or os.getenv("MINIO_ENDPOINT", "minio:9000")
        self.access_key = access_key or os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.secret_key = secret_key or os.getenv("MINIO_SECRET_KEY", "minioadmin123")
        self.bucket_name = bucket_name or os.getenv("MINIO_BUCKET", "documents")
        self.secure = secure
        
        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )
        
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created bucket: {self.bucket_name}")
            else:
                logger.info(f"Bucket exists: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"Failed to create/check bucket: {e}")
            raise
    
    def upload_file(
        self,
        file_data: BinaryIO,
        original_filename: str,
        content_type: str = "application/octet-stream",
        metadata: dict = None
    ) -> dict:
        """
        Upload a file to MinIO
        
        Args:
            file_data: File-like object containing the data
            original_filename: Original name of the file
            content_type: MIME type of the file
            metadata: Additional metadata to store with the file
            
        Returns:
            dict with object_key, bucket, size, etag
        """
        # Generate unique object key
        ext = os.path.splitext(original_filename)[1].lower()
        object_key = f"{uuid.uuid4()}{ext}"
        
        # Get file size
        file_data.seek(0, 2)  # Seek to end
        file_size = file_data.tell()
        file_data.seek(0)  # Reset to beginning
        
        # Prepare metadata
        minio_metadata = metadata or {}
        minio_metadata["original_filename"] = original_filename
        
        try:
            result = self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_key,
                data=file_data,
                length=file_size,
                content_type=content_type,
                metadata=minio_metadata
            )
            
            logger.info(f"Uploaded file: {object_key} ({file_size} bytes)")
            
            return {
                "object_key": object_key,
                "bucket": self.bucket_name,
                "size": file_size,
                "etag": result.etag,
                "content_type": content_type
            }
        except S3Error as e:
            logger.error(f"Failed to upload file: {e}")
            raise
    
    def upload_bytes(
        self,
        data: bytes,
        original_filename: str,
        content_type: str = "application/octet-stream",
        metadata: dict = None
    ) -> dict:
        """Upload bytes data to MinIO"""
        file_data = io.BytesIO(data)
        return self.upload_file(file_data, original_filename, content_type, metadata)
    
    def download_file(self, object_key: str) -> bytes:
        """
        Download a file from MinIO
        
        Args:
            object_key: The object key in MinIO
            
        Returns:
            File content as bytes
        """
        try:
            response = self.client.get_object(self.bucket_name, object_key)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            logger.error(f"Failed to download file {object_key}: {e}")
            raise
    
    def get_presigned_url(
        self,
        object_key: str,
        expires: timedelta = timedelta(hours=1)
    ) -> str:
        """
        Generate a presigned URL for downloading a file
        
        Args:
            object_key: The object key in MinIO
            expires: URL expiration time
            
        Returns:
            Presigned URL string
        """
        try:
            url = self.client.presigned_get_object(
                self.bucket_name,
                object_key,
                expires=expires
            )
            return url
        except S3Error as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise
    
    def delete_file(self, object_key: str) -> bool:
        """
        Delete a file from MinIO
        
        Args:
            object_key: The object key to delete
            
        Returns:
            True if successful
        """
        try:
            self.client.remove_object(self.bucket_name, object_key)
            logger.info(f"Deleted file: {object_key}")
            return True
        except S3Error as e:
            logger.error(f"Failed to delete file {object_key}: {e}")
            raise
    
    def file_exists(self, object_key: str) -> bool:
        """Check if a file exists in MinIO"""
        try:
            self.client.stat_object(self.bucket_name, object_key)
            return True
        except S3Error:
            return False
    
    def get_file_info(self, object_key: str) -> dict:
        """Get metadata about a file"""
        try:
            stat = self.client.stat_object(self.bucket_name, object_key)
            return {
                "object_key": object_key,
                "bucket": self.bucket_name,
                "size": stat.size,
                "content_type": stat.content_type,
                "last_modified": stat.last_modified,
                "etag": stat.etag,
                "metadata": stat.metadata
            }
        except S3Error as e:
            logger.error(f"Failed to get file info {object_key}: {e}")
            raise
    
    def list_files(self, prefix: str = "", recursive: bool = True) -> list:
        """List all files in the bucket"""
        try:
            objects = self.client.list_objects(
                self.bucket_name,
                prefix=prefix,
                recursive=recursive
            )
            return [
                {
                    "object_key": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified
                }
                for obj in objects
            ]
        except S3Error as e:
            logger.error(f"Failed to list files: {e}")
            raise
    
    def health_check(self) -> bool:
        """Check if MinIO is accessible"""
        try:
            self.client.bucket_exists(self.bucket_name)
            return True
        except Exception:
            return False



