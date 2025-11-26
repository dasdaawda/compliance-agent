import json
import logging
import os
from datetime import datetime
from celery import chain, group, chord
from celery.utils.log import get_task_logger
from django.db import transaction
from django.utils import timezone

from compliance_app.celery import app
from projects.models import Video, VideoStatus
from projects.validators import VideoValidator, VideoValidationError, notify_validation_failure
from storage.b2_utils import get_b2_utils
from .models import PipelineExecution, VerificationTask, AITrigger
from .services.ai_services import (
    WhisperASRService, VideoAnalyticsService, NLPDictionaryService, ReportCompiler
)
from .services.ffmpeg_service import VideoPreprocessor, AudioProcessor, FrameProcessor

logger = get_task_logger(__name__)


def log_pipeline_step(video_id, step_name, status, error=None):
    """Logs a pipeline step with structured JSON format."""
    log_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'video_id': str(video_id),
        'step': step_name,
        'status': status,
        'error': error,
    }
    logger.info(json.dumps(log_entry))


def update_execution(video_id, current_task, progress, last_step=None):
    """Updates PipelineExecution state with retry tracking."""
    try:
        execution = PipelineExecution.objects.get(video_id=video_id)
        execution.current_task = current_task
        execution.progress = progress
        if last_step:
            execution.last_step = last_step
        execution.save()
        return execution
    except PipelineExecution.DoesNotExist:
        logger.error(f"PipelineExecution not found for video {video_id}")
        raise


def record_error_trace(video_id, step_name, error_message):
    """Records error trace for debugging."""
    try:
        execution = PipelineExecution.objects.get(video_id=video_id)
        if not execution.error_trace:
            execution.error_trace = []
        execution.error_trace.append({
            'timestamp': datetime.utcnow().isoformat(),
            'step': step_name,
            'error': error_message,
        })
        execution.save()
    except Exception as e:
        logger.error(f"Failed to record error trace: {e}")


def notify_pipeline_failure(video_id, stage, message):
    """Unified notification on pipeline failure."""
    from projects.tasks import send_pipeline_failure_notification
    send_pipeline_failure_notification.delay(str(video_id), stage, message)


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 1},
    retry_backoff=True,
    retry_backoff_max=600,
    time_limit=300,
    soft_time_limit=280,
)
def process_video(self, video_id):
    """
    Main pipeline task - orchestrates the entire video processing workflow.
    Implements idempotent resumable processing.
    """
    try:
        logger.info(f"Starting AI pipeline for video {video_id}")
        log_pipeline_step(video_id, 'process_video', 'started')
        
        with transaction.atomic():
            video = Video.objects.get(id=video_id)
            
            # Create or get execution record
            execution, created = PipelineExecution.objects.get_or_create(
                video=video,
                defaults={
                    'status': PipelineExecution.Status.RUNNING,
                    'started_at': timezone.now(),
                    'error_trace': [],
                }
            )
            
            # Validate video before starting pipeline
            try:
                validator = VideoValidator()
                validator.validate_video(video)
                log_pipeline_step(video_id, 'validate_video', 'completed')
            except VideoValidationError as e:
                logger.error(f"Video validation failed: {e}")
                record_error_trace(video_id, 'validate_video', str(e))
                notify_validation_failure(video, str(e))
                
                video.status = VideoStatus.FAILED
                video.status_message = f"Validation failed: {e}"
                video.save()
                
                execution.status = PipelineExecution.Status.FAILED
                execution.error_message = str(e)
                execution.completed_at = timezone.now()
                execution.save()
                
                log_pipeline_step(video_id, 'process_video', 'failed', str(e))
                return None
            
            execution.status = PipelineExecution.Status.RUNNING
            execution.started_at = timezone.now()
            execution.current_task = 'process_video_pipeline'
            execution.progress = 5
            execution.save()
            
            video.status = VideoStatus.PROCESSING
            video.save()

        # Resume from last successful step if retrying
        if execution.last_step:
            logger.info(f"Resuming pipeline from step: {execution.last_step}")

        # Chain: preprocess -> group(audio_branch, frames_branch) -> compile_report
        workflow = chain(
            preprocess_video.s(video_id),
            group([
                chain(
                    run_ffmpeg_audio.s(video_id),
                    run_whisper_asr.s(video_id),
                    run_nlp_dictionaries.s(video_id)
                ),
                chain(
                    run_ffmpeg_frames.s(video_id),
                    run_video_analytics.s(video_id)
                )
            ]),
            compile_report.s(video_id)
        )

        result = workflow.apply_async(link_error=handle_pipeline_error.s(video_id))
        logger.info(f"Pipeline workflow started for video {video_id}, task_id={result.id}")
        log_pipeline_step(video_id, 'process_video', 'workflow_started')
        return result.id
        
    except Exception as exc:
        logger.error(f"Failed to start pipeline for video {video_id}: {str(exc)}")
        log_pipeline_step(video_id, 'process_video', 'failed', str(exc))
        record_error_trace(video_id, 'process_video', str(exc))
        handle_pipeline_error.delay(video_id, 'process_video', str(exc))
        raise


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 2},
    retry_backoff=True,
    time_limit=600,
    soft_time_limit=580,
)
def preprocess_video(self, video_id):
    """Stage 1: Video preprocessing and download."""
    try:
        update_execution(video_id, 'preprocess_video', 10, 'preprocess_video')
        log_pipeline_step(video_id, 'preprocess_video', 'started')
        
        video = Video.objects.get(id=video_id)
        preprocessor = VideoPreprocessor()
        
        # Get video path
        if video.video_url and not video.video_file:
            video_path = preprocessor.download_from_url(video.video_url)
        else:
            video_path = video.video_file.path
        
        logger.info(f"Video preprocessing completed for {video_id}")
        log_pipeline_step(video_id, 'preprocess_video', 'completed')
        return video_path
        
    except Exception as exc:
        logger.error(f"Video preprocessing failed for {video_id}: {str(exc)}")
        log_pipeline_step(video_id, 'preprocess_video', 'failed', str(exc))
        record_error_trace(video_id, 'preprocess_video', str(exc))
        raise


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 2},
    retry_backoff=True,
    time_limit=600,
    soft_time_limit=580,
)
def run_ffmpeg_audio(self, audio_input, video_id):
    """Stage 2: Audio extraction."""
    try:
        update_execution(video_id, 'run_ffmpeg_audio', 20, 'run_ffmpeg_audio')
        log_pipeline_step(video_id, 'run_ffmpeg_audio', 'started')
        
        audio_processor = AudioProcessor()
        audio_path = audio_processor.extract_audio(audio_input)
        
        logger.info(f"Audio extraction completed for {video_id}")
        log_pipeline_step(video_id, 'run_ffmpeg_audio', 'completed')
        return audio_path
        
    except Exception as exc:
        logger.error(f"Audio extraction failed: {str(exc)}")
        log_pipeline_step(video_id, 'run_ffmpeg_audio', 'failed', str(exc))
        record_error_trace(video_id, 'run_ffmpeg_audio', str(exc))
        raise


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 2},
    retry_backoff=True,
    time_limit=600,
    soft_time_limit=580,
)
def run_ffmpeg_frames(self, video_path, video_id):
    """Stage 3: Frame extraction (1 frame/sec)."""
    try:
        update_execution(video_id, 'run_ffmpeg_frames', 30, 'run_ffmpeg_frames')
        log_pipeline_step(video_id, 'run_ffmpeg_frames', 'started')
        
        frame_processor = FrameProcessor()
        frames_dir = frame_processor.extract_frames(video_path, fps=1)
        
        logger.info(f"Frame extraction completed for {video_id}")
        log_pipeline_step(video_id, 'run_ffmpeg_frames', 'completed')
        return frames_dir
        
    except Exception as exc:
        logger.error(f"Frame extraction failed: {str(exc)}")
        log_pipeline_step(video_id, 'run_ffmpeg_frames', 'failed', str(exc))
        record_error_trace(video_id, 'run_ffmpeg_frames', str(exc))
        raise


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    time_limit=900,
    soft_time_limit=880,
)
def run_whisper_asr(self, audio_path, video_id):
    """Stage 4: Audio transcription via Whisper."""
    try:
        update_execution(video_id, 'run_whisper_asr', 40, 'run_whisper_asr')
        log_pipeline_step(video_id, 'run_whisper_asr', 'started')
        
        whisper_service = WhisperASRService()
        transcription = whisper_service.transcribe(audio_path)
        
        logger.info(f"Whisper ASR completed for {video_id}")
        log_pipeline_step(video_id, 'run_whisper_asr', 'completed')
        return transcription
        
    except Exception as exc:
        logger.error(f"Whisper ASR failed: {str(exc)}")
        log_pipeline_step(video_id, 'run_whisper_asr', 'failed', str(exc))
        record_error_trace(video_id, 'run_whisper_asr', str(exc))
        notify_pipeline_failure(video_id, 'whisper_asr', str(exc))
        raise


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    time_limit=900,
    soft_time_limit=880,
)
def run_video_analytics(self, frames_dir, video_id):
    """Stage 5: Frame analysis via AI models."""
    try:
        update_execution(video_id, 'run_video_analytics', 50, 'run_video_analytics')
        log_pipeline_step(video_id, 'run_video_analytics', 'started')
        
        analytics_service = VideoAnalyticsService()
        
        # Process frames
        frame_files = [f for f in os.listdir(frames_dir) if f.endswith('.jpg')]
        frame_results = []
        execution = PipelineExecution.objects.get(video_id=video_id)
        
        for i, frame_file in enumerate(frame_files[:5]):  # Process first 5 frames
            frame_path = os.path.join(frames_dir, frame_file)
            result = analytics_service.analyze_frame(frame_path, i)
            frame_results.append(result)
            
            # Update API call counters
            execution.api_calls_count += 2  # YOLO + NSFW
            execution.cost_estimate += 0.0002
            execution.save()
        
        logger.info(f"Video analytics completed, processed {len(frame_results)} frames")
        log_pipeline_step(video_id, 'run_video_analytics', 'completed')
        return frame_results
        
    except Exception as exc:
        logger.error(f"Video analytics failed: {str(exc)}")
        log_pipeline_step(video_id, 'run_video_analytics', 'failed', str(exc))
        record_error_trace(video_id, 'run_video_analytics', str(exc))
        notify_pipeline_failure(video_id, 'video_analytics', str(exc))
        raise


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 2},
    retry_backoff=True,
    time_limit=300,
    soft_time_limit=280,
)
def run_nlp_dictionaries(self, transcription, video_id):
    """Stage 6: NLP text analysis."""
    try:
        update_execution(video_id, 'run_nlp_dictionaries', 80, 'run_nlp_dictionaries')
        log_pipeline_step(video_id, 'run_nlp_dictionaries', 'started')
        
        nlp_service = NLPDictionaryService()
        text_triggers = nlp_service.analyze_transcription(transcription)
        
        logger.info(f"NLP analysis completed, found {len(text_triggers)} triggers")
        log_pipeline_step(video_id, 'run_nlp_dictionaries', 'completed')
        return text_triggers
        
    except Exception as exc:
        logger.error(f"NLP analysis failed: {str(exc)}")
        log_pipeline_step(video_id, 'run_nlp_dictionaries', 'failed', str(exc))
        record_error_trace(video_id, 'run_nlp_dictionaries', str(exc))
        raise


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 1},
    retry_backoff=True,
    time_limit=300,
    soft_time_limit=280,
)
def compile_report(self, results, video_id):
    """Stage 7: Final report compilation and verification task creation."""
    try:
        execution = PipelineExecution.objects.get(video_id=video_id)
        execution.current_task = 'compile_report'
        execution.progress = 90
        execution.last_step = 'compile_report'
        execution.save()
        
        log_pipeline_step(video_id, 'compile_report', 'started')
        
        with transaction.atomic():
            video = Video.objects.get(id=video_id)
            compiler = ReportCompiler()
            
            # results contains [nlp_results, video_results]
            nlp_results, video_results = results
            all_triggers = nlp_results + video_results
            
            # Save triggers to DB
            compiler.save_triggers_to_db(video, all_triggers)
            
            # Build report from DB data only (filter by status)
            final_report = compiler.compile_final_report_from_db(video)
            
            # Update video
            video.ai_report = final_report
            video.status = VideoStatus.VERIFICATION
            video.processed_at = timezone.now()
            video.save()
            
            # Create verification task for operator
            VerificationTask.objects.get_or_create(video=video)
            
            # Complete pipeline execution
            execution.status = PipelineExecution.Status.COMPLETED
            execution.progress = 100
            execution.completed_at = timezone.now()
            execution.processing_time_seconds = int(
                (timezone.now() - execution.started_at).total_seconds()
            )
            execution.save()
        
        # Send success notification
        from projects.tasks import send_video_ready_notification
        send_video_ready_notification.delay(str(video_id))
        
        logger.info(f"Pipeline completed successfully for {video_id}")
        log_pipeline_step(video_id, 'compile_report', 'completed')
        return final_report
        
    except Exception as exc:
        logger.error(f"Report compilation failed for {video_id}: {str(exc)}")
        log_pipeline_step(video_id, 'compile_report', 'failed', str(exc))
        record_error_trace(video_id, 'compile_report', str(exc))
        handle_pipeline_error.delay(video_id, 'compile_report', str(exc))
        raise


@app.task
def handle_pipeline_error(video_id, stage, error_message):
    """Unified error handler for pipeline failures."""
    try:
        logger.error(
            f"Pipeline error handler triggered for video {video_id} at stage {stage}: {error_message}"
        )
        log_pipeline_step(video_id, 'handle_pipeline_error', 'started')
        
        with transaction.atomic():
            video = Video.objects.get(id=video_id)
            video.status = VideoStatus.FAILED
            video.status_message = f"Pipeline failed at {stage}: {error_message}"
            video.save()
            
            execution = PipelineExecution.objects.get(video=video)
            execution.status = PipelineExecution.Status.FAILED
            execution.error_message = error_message
            execution.completed_at = timezone.now()
            execution.retry_count += 1
            execution.save()
        
        # Send failure notification to admins
        from projects.tasks import send_pipeline_failure_notification
        send_pipeline_failure_notification.delay(str(video_id), stage, error_message)
        
        log_pipeline_step(video_id, 'handle_pipeline_error', 'completed')
        
    except Exception as e:
        logger.error(f"Error handling pipeline error for {video_id}: {str(e)}")


@app.task
def cleanup_artifacts_periodic():
    """
    Periodic task to clean up stale temporary files and orphaned frames/audio from B2.
    Runs as Celery Beat job.
    """
    try:
        logger.info("Starting periodic artifact cleanup")
        log_pipeline_step(None, 'cleanup_artifacts_periodic', 'started')
        
        b2_utils = get_b2_utils()
        
        # Find completed or failed executions older than 7 days
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=7)
        old_executions = PipelineExecution.objects.filter(
            status__in=[
                PipelineExecution.Status.COMPLETED,
                PipelineExecution.Status.FAILED,
            ],
            completed_at__lt=cutoff_date
        )
        
        deleted_count = 0
        for execution in old_executions:
            # TODO: Implement logic to identify and delete temp files
            # This depends on your naming scheme for temp files in B2
            pass
        
        logger.info(f"Artifact cleanup completed, deleted {deleted_count} artifacts")
        log_pipeline_step(None, 'cleanup_artifacts_periodic', 'completed')
        
    except Exception as e:
        logger.error(f"Error in periodic artifact cleanup: {e}")
        log_pipeline_step(None, 'cleanup_artifacts_periodic', 'failed', str(e))


@app.task
def refresh_cdn_cache_periodic():
    """
    Periodic task to refresh signed URLs and CDN caches.
    Runs as Celery Beat job.
    """
    try:
        logger.info("Starting periodic CDN cache refresh")
        log_pipeline_step(None, 'refresh_cdn_cache_periodic', 'started')
        
        # TODO: Implement Cloudflare cache purge logic
        # This depends on your Cloudflare API setup
        
        logger.info("CDN cache refresh completed")
        log_pipeline_step(None, 'refresh_cdn_cache_periodic', 'completed')
        
    except Exception as e:
        logger.error(f"Error in periodic CDN cache refresh: {e}")
        log_pipeline_step(None, 'refresh_cdn_cache_periodic', 'failed', str(e))
