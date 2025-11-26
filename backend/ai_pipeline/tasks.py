# This file is deprecated. Import tasks from celery_tasks.py instead.
# Kept for backward compatibility.
from .celery_tasks import (
    process_video,
    preprocess_video,
    run_ffmpeg_audio,
    run_ffmpeg_frames,
    run_whisper_asr,
    run_video_analytics,
    run_nlp_dictionaries,
    compile_report,
    handle_pipeline_error,
    cleanup_artifacts_periodic,
    refresh_cdn_cache_periodic,
)

__all__ = [
    'process_video',
    'preprocess_video',
    'run_ffmpeg_audio',
    'run_ffmpeg_frames',
    'run_whisper_asr',
    'run_video_analytics',
    'run_nlp_dictionaries',
    'compile_report',
    'handle_pipeline_error',
    'cleanup_artifacts_periodic',
    'refresh_cdn_cache_periodic',
]
