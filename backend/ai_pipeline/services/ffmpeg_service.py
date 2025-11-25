import os
import subprocess
import tempfile
import logging
from urllib.parse import urlparse
from django.conf import settings

logger = logging.getLogger(__name__)

class VideoPreprocessor:
    def download_from_url(self, video_url):
        # Проверяем валидность URL
        if not self._is_valid_url(video_url):
            logger.error(f"Invalid video URL: {video_url}")
            raise ValueError(f"Invalid video URL: {video_url}")
        
        import yt_dlp
        ydl_opts = {
            'outtmpl': os.path.join(tempfile.gettempdir(), 'downloaded_%(id)s.%(ext)s'),
            'format': 'best[height<=1080]',
            'quiet': True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                file_path = ydl.prepare_filename(info)
                logger.info(f"Video downloaded successfully: {file_path}")
                return file_path
        except Exception as e:
            logger.error(f"Error downloading video from URL {video_url}: {e}")
            raise

    def _is_valid_url(self, url):
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False


class AudioProcessor:
    def extract_audio(self, video_path):
        # Проверяем существование файла
        if not os.path.exists(video_path):
            logger.error(f"Video file does not exist: {video_path}")
            raise FileNotFoundError(f"Video file does not exist: {video_path}")
        
        output_path = os.path.join(tempfile.gettempdir(), f"audio_{os.path.basename(video_path)}.wav")
        cmd = [
            'ffmpeg', '-i', video_path, '-vn', '-acodec', 'pcm_s16le',
            '-ar', '16000', '-ac', '1', '-y', output_path
        ]
        try:
            subprocess.run(cmd, capture_output=True, check=True)
            logger.info(f"Audio extracted successfully: {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"Error extracting audio from video {video_path}: {e.stderr.decode()}")
            raise
        except FileNotFoundError:
            logger.error("ffmpeg is not installed or not found in PATH.")
            raise


class FrameProcessor:
    def extract_frames(self, video_path, fps=None):
        # Проверяем существование файла
        if not os.path.exists(video_path):
            logger.error(f"Video file does not exist: {video_path}")
            raise FileNotFoundError(f"Video file does not exist: {video_path}")
        
        target_fps = fps or settings.FRAME_EXTRACTION_FPS
        output_dir = tempfile.mkdtemp(prefix="frames_")
        cmd = [
            'ffmpeg', '-i', video_path, '-vf', f'fps={target_fps}',
            '-qscale:v', '2', os.path.join(output_dir, 'frame_%04d.jpg')
        ]
        try:
            subprocess.run(cmd, capture_output=True, check=True)
            logger.info(f"Frames extracted successfully to directory: {output_dir} at {target_fps} fps")
            return output_dir
        except subprocess.CalledProcessError as e:
            logger.error(f"Error extracting frames from video {video_path}: {e.stderr.decode()}")
            raise
        except FileNotFoundError:
            logger.error("ffmpeg is not installed or not found in PATH.")
            raise