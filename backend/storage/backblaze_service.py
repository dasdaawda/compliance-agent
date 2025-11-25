import logging
import os
from urllib.parse import urljoin, urlparse

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from django.conf import settings

logger = logging.getLogger(__name__)

class BackblazeService:
    def __init__(self):
        self.config = settings.BACKBLAZE_CONFIG or {}
        self.bucket_name = self.config.get('BUCKET_NAME')
        if not self.bucket_name:
            raise ValueError("BACKBLAZE_CONFIG['BUCKET_NAME'] must be set")
        self.endpoint_url = self.config.get('ENDPOINT_URL')
        self.s3_client = self._create_s3_client()
    
    def _create_s3_client(self):
        access_key = self.config.get('APPLICATION_KEY_ID')
        secret = self.config.get('APPLICATION_KEY')
        if not access_key or not secret:
            raise ValueError("Backblaze credentials missing in BACKBLAZE_CONFIG")
        client_kwargs = dict(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret,
            config=Config(signature_version='s3v4')
        )
        if self.endpoint_url:
            client_kwargs['endpoint_url'] = self.endpoint_url
        return boto3.client('s3', **client_kwargs)
    
    def upload_file(self, file_path: str, b2_file_path: str) -> str:
        if not os.path.exists(file_path):
            logger.error("File not found for upload: %s", file_path)
            raise FileNotFoundError(f"File not found: {file_path}")
        try:
            with open(file_path, 'rb') as file_data:
                self.s3_client.upload_fileobj(
                    file_data,
                    self.bucket_name,
                    b2_file_path
                )
            url = self._get_cdn_url(b2_file_path)
            logger.info("Uploaded %s to bucket %s as %s", file_path, self.bucket_name, b2_file_path)
            return url
        except ClientError as e:
            logger.exception("S3 ClientError during upload: %s", e)
            raise
        except Exception as e:
            logger.exception("Unexpected error during upload: %s", e)
            raise

    def generate_presigned_url(self, b2_file_path: str, expiration: int = 3600) -> str:
        try:
            params = {'Bucket': self.bucket_name, 'Key': b2_file_path}
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params=params,
                ExpiresIn=expiration
            )
            cdn = self.config.get('CLOUDFLARE_CDN_URL')
            if cdn:
                return urljoin(cdn.rstrip('/') + '/', b2_file_path.lstrip('/'))
            return url
        except ClientError as e:
            logger.exception("Failed to generate presigned URL: %s", e)
            raise
        except Exception as e:
            logger.exception("Unexpected error generating presigned URL: %s", e)
            raise
    
    def _get_cdn_url(self, b2_file_path: str) -> str:
        cdn_base_url = self.config.get('CLOUDFLARE_CDN_URL')
        if cdn_base_url:
            return urljoin(cdn_base_url.rstrip('/') + '/', b2_file_path.lstrip('/'))
        if self.endpoint_url:
            parsed = urlparse(self.endpoint_url)
            netloc = parsed.netloc or parsed.path
            return f"https://{self.bucket_name}.{netloc.rstrip('/')}/{b2_file_path.lstrip('/')}"
        return f"https://{self.bucket_name}.s3.amazonaws.com/{b2_file_path.lstrip('/')}"