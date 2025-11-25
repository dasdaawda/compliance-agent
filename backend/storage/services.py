import os
import logging
from pathlib import Path
from typing import Optional
from uuid import UUID
from .backblaze_service import BackblazeService

logger = logging.getLogger(__name__)

class StorageManager:
    def __init__(self):
        self.b2_service = BackblazeService()

    def upload_video_file(self, video_instance, file_path: str) -> str:
        if not os.path.exists(file_path):
            logger.error("upload_video_file: file not found: %s", file_path)
            raise FileNotFoundError(file_path)
        
        b2_file_path = self._generate_b2_path(
            project_id=video_instance.project.id,
            video_id=video_instance.id,
            filename=video_instance.original_name
        )
        
        try:
            cdn_url = self.b2_service.upload_file(file_path, b2_file_path)
            logger.info("Uploaded video %s -> %s", file_path, b2_file_path)
            return cdn_url
        except Exception:
            logger.exception("Failed to upload video %s to %s", file_path, b2_file_path)
            raise

    def get_video_streaming_url(self, video_instance, expiration: int = 3600) -> str:
        b2_file_path = self._generate_b2_path(
            project_id=video_instance.project.id,
            video_id=video_instance.id,
            filename=video_instance.original_name
        )
        return self.b2_service.generate_presigned_url(b2_file_path, expiration=expiration)

    def _generate_b2_path(self, project_id: UUID, video_id: UUID, filename: str) -> str:
        """
        Генерирует путь для файла в B2, консистентный с get_video_upload_path в models.py.
        Формат: videos/raw/{project_id}/{video_id}.{ext}
        """
        ext = Path(filename).suffix.lower() or '.mp4'
        return f"videos/raw/{project_id}/{video_id}{ext}"
