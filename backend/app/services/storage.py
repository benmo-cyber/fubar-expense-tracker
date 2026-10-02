import os
import uuid
import shutil
from pathlib import Path
from typing import BinaryIO
from app.core.config import settings


class LocalStorageService:
    def __init__(self):
        self.storage_path = Path(settings.LOCAL_STORAGE_PATH)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def upload_file(self, file: BinaryIO, filename: str, content_type: str) -> str:
        try:
            file_extension = os.path.splitext(filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = self.storage_path / unique_filename
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file, buffer)
            
            return f"/uploads/receipts/{unique_filename}"
        except Exception as e:
            raise Exception(f"Failed to upload file: {str(e)}")
    
    def delete_file(self, url: str) -> bool:
        try:
            filename = url.split("/")[-1]
            file_path = self.storage_path / filename
            if file_path.exists():
                file_path.unlink()
            return True
        except Exception:
            return False
    
    def get_file_path(self, url: str) -> Path:
        filename = url.split("/")[-1]
        return self.storage_path / filename


class S3StorageService:
    def __init__(self):
        import boto3
        from botocore.exceptions import ClientError
        self.ClientError = ClientError
        
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
            endpoint_url=settings.S3_ENDPOINT_URL or None
        )
        self.bucket_name = settings.S3_BUCKET_NAME
    
    def upload_file(self, file: BinaryIO, filename: str, content_type: str) -> str:
        try:
            file_extension = os.path.splitext(filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            key = f"receipts/{unique_filename}"
            
            self.s3_client.upload_fileobj(
                file,
                self.bucket_name,
                key,
                ExtraArgs={'ContentType': content_type}
            )
            
            if settings.S3_ENDPOINT_URL:
                url = f"{settings.S3_ENDPOINT_URL}/{self.bucket_name}/{key}"
            else:
                url = f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"
            
            return url
        except self.ClientError as e:
            raise Exception(f"Failed to upload file to S3: {str(e)}")
    
    def delete_file(self, url: str) -> bool:
        try:
            key = url.split(f"{self.bucket_name}/")[-1]
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except self.ClientError:
            return False


# Use local or S3 storage based on configuration
if settings.USE_S3_STORAGE:
    storage_service = S3StorageService()
else:
    storage_service = LocalStorageService()
