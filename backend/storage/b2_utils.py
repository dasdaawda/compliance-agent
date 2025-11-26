import logging
import os
import time
from functools import wraps
from django.conf import settings
from django.core.cache import cache
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from botocore.exceptions import ClientError

from .backblaze_service import BackblazeService

logger = logging.getLogger(__name__)

# Cache settings
SIGNED_URL_CACHE_TTL = 3600  # 1 hour
SIGNED_URL_CACHE_KEY_PREFIX = 'b2_signed_url:'


class B2RetryableError(Exception):
    """Base exception for B2 retryable errors."""
    pass


class B2Utils:
    """
    Wrapper around BackblazeService with tenacity-based retries,
    exponential backoff, and signed URL caching.
    """

    def __init__(self):
        self.service = BackblazeService()
        self.max_retries = getattr(settings, 'B2_MAX_RETRIES', 3)
        self.retry_backoff_factor = getattr(settings, 'B2_RETRY_BACKOFF', 2)
        self.retry_backoff_max = getattr(settings, 'B2_RETRY_BACKOFF_MAX', 60)

    def _get_retry_decorator(self):
        """Returns a retry decorator with exponential backoff."""
        return retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(
                multiplier=self.retry_backoff_factor,
                max=self.retry_backoff_max,
            ),
            retry=retry_if_exception_type((ClientError, OSError, B2RetryableError)),
            before_sleep=self._log_retry,
        )

    @staticmethod
    def _log_retry(retry_state):
        """Log retry attempts."""
        logger.warning(
            f"Retrying B2 operation (attempt {retry_state.attempt_number}): {retry_state.outcome}"
        )

    def upload_video(self, file_path: str, b2_file_path: str) -> str:
        """
        Upload a video file to B2 with retries.
        Returns the CDN URL.
        """
        @self._get_retry_decorator()
        def _upload():
            try:
                if not os.path.exists(file_path):
                    logger.error(f"Video file not found: {file_path}")
                    raise FileNotFoundError(f"Video file not found: {file_path}")
                
                logger.info(f"Uploading video {file_path} to B2 as {b2_file_path}")
                url = self.service.upload_file(file_path, b2_file_path)
                logger.info(f"Successfully uploaded video to {url}")
                return url
            except ClientError as e:
                logger.error(f"B2 ClientError during video upload: {e}")
                raise B2RetryableError(f"B2 upload failed: {e}") from e
            except Exception as e:
                logger.error(f"Unexpected error during video upload: {e}")
                raise

        return _upload()

    def upload_frame(self, file_path: str, b2_file_path: str) -> str:
        """
        Upload a frame image to B2 with retries.
        Returns the CDN URL.
        """
        @self._get_retry_decorator()
        def _upload():
            try:
                if not os.path.exists(file_path):
                    logger.error(f"Frame file not found: {file_path}")
                    raise FileNotFoundError(f"Frame file not found: {file_path}")
                
                logger.info(f"Uploading frame {file_path} to B2 as {b2_file_path}")
                url = self.service.upload_file(file_path, b2_file_path)
                return url
            except ClientError as e:
                logger.error(f"B2 ClientError during frame upload: {e}")
                raise B2RetryableError(f"B2 frame upload failed: {e}") from e
            except Exception as e:
                logger.error(f"Unexpected error during frame upload: {e}")
                raise

        return _upload()

    def generate_signed_url(self, b2_file_path: str, expiration: int = 3600) -> str:
        """
        Generate a signed URL for B2 file access with caching.
        Cached URLs are returned if available and not expired.
        """
        cache_key = f"{SIGNED_URL_CACHE_KEY_PREFIX}{b2_file_path}"
        
        # Try to get from cache
        cached_url = cache.get(cache_key)
        if cached_url:
            logger.debug(f"Using cached signed URL for {b2_file_path}")
            return cached_url

        @self._get_retry_decorator()
        def _generate():
            try:
                logger.info(f"Generating signed URL for {b2_file_path}")
                url = self.service.generate_presigned_url(b2_file_path, expiration)
                # Cache the URL with a slightly shorter TTL to avoid expiration edge cases
                cache.set(cache_key, url, SIGNED_URL_CACHE_TTL)
                return url
            except ClientError as e:
                logger.error(f"B2 ClientError during signed URL generation: {e}")
                raise B2RetryableError(f"B2 signed URL generation failed: {e}") from e
            except Exception as e:
                logger.error(f"Unexpected error during signed URL generation: {e}")
                raise

        return _generate()

    def purge_artifacts(self, b2_file_paths: list) -> bool:
        """
        Delete multiple artifacts from B2.
        Returns True if all deletes succeed, False otherwise.
        """
        success = True
        for b2_file_path in b2_file_paths:
            try:
                @self._get_retry_decorator()
                def _delete():
                    logger.info(f"Deleting artifact from B2: {b2_file_path}")
                    self.service.s3_client.delete_object(
                        Bucket=self.service.bucket_name,
                        Key=b2_file_path
                    )
                    logger.info(f"Successfully deleted {b2_file_path} from B2")

                _delete()
                
                # Clear any cached signed URLs for this artifact
                cache_key = f"{SIGNED_URL_CACHE_KEY_PREFIX}{b2_file_path}"
                cache.delete(cache_key)
                
            except Exception as e:
                logger.error(f"Failed to delete {b2_file_path}: {e}")
                success = False

        return success

    def delete_artifact(self, b2_file_path: str) -> bool:
        """
        Delete a single artifact from B2.
        Returns True if successful, False otherwise.
        """
        return self.purge_artifacts([b2_file_path])

    def refresh_cache_for_path(self, b2_file_path: str) -> None:
        """
        Refresh (invalidate) cached signed URL for a path.
        """
        cache_key = f"{SIGNED_URL_CACHE_KEY_PREFIX}{b2_file_path}"
        cache.delete(cache_key)
        logger.debug(f"Refreshed cache for {b2_file_path}")


# Singleton instance for convenience
_b2_utils_instance = None


def get_b2_utils():
    """Returns a singleton instance of B2Utils."""
    global _b2_utils_instance
    if _b2_utils_instance is None:
        _b2_utils_instance = B2Utils()
    return _b2_utils_instance


def with_b2_retry(func):
    """
    Decorator to add B2 retry logic to a function.
    Usage:
        @with_b2_retry
        def my_function():
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        b2_utils = get_b2_utils()
        retry_decorator = b2_utils._get_retry_decorator()
        return retry_decorator(func)(*args, **kwargs)
    return wrapper
