from celery import chain, group, chord
from celery.utils.log import get_task_logger
from django.db import transaction
from django.utils import timezone
import os

from compliance_app.celery import app
from projects.models import Video, VideoStatus
from .models import PipelineExecution, VerificationTask
from .services.ai_services import (
    WhisperASRService, VideoAnalyticsService, NLPDictionaryService, ReportCompiler
)
from .services.ffmpeg_service import VideoPreprocessor, AudioProcessor, FrameProcessor

logger = get_task_logger(__name__)

def update_execution(video_id, current_task, progress):
    """Обновляет состояние PipelineExecution."""
    execution = PipelineExecution.objects.get(video_id=video_id)
    execution.current_task = current_task
    execution.progress = progress
    execution.save()
    return execution


@app.task(bind=True)
def process_video(self, video_id):
    """
    Главная задача пайплайна - запускает весь граф обработки видео.
    """
    try:
        logger.info(f"Starting AI pipeline for video {video_id}")
        
        with transaction.atomic():
            video = Video.objects.get(id=video_id)
            
            # Создаем запись о выполнении пайплайна
            execution, created = PipelineExecution.objects.get_or_create(
                video=video,
                defaults={
                    'status': PipelineExecution.Status.RUNNING, 
                    'started_at': timezone.now()
                }
            )
            
            execution.status = PipelineExecution.Status.RUNNING
            execution.started_at = timezone.now()
            execution.current_task = 'process_video_pipeline'
            execution.progress = 5
            execution.save()
            
            video.status = VideoStatus.PROCESSING
            video.save()

        # Chain: preprocess -> group(branch_audio_text, branch_frames) -> compile_report
        workflow = chain(
            preprocess_video.s(video_id),  # returns video_path
            group([
                chain(
                    run_ffmpeg_audio.s(video_id),      # will be called as run_ffmpeg_audio(video_path, video_id)
                    run_whisper_asr.s(video_id),       # run_whisper_asr(audio_path, video_id)
                    run_nlp_dictionaries.s(video_id)   # run_nlp_dictionaries(transcription, video_id)
                ),
                chain(
                    run_ffmpeg_frames.s(video_id),     # run_ffmpeg_frames(video_path, video_id)
                    run_video_analytics.s(video_id)    # run_video_analytics(frames_dir, video_id)
                )
            ]),
            compile_report.s(video_id)  # compile_report(results, video_id)
        )

        result = workflow.apply_async(link_error=handle_pipeline_error.s(video_id))
        logger.info(f"Pipeline workflow started for video {video_id}")
        return result.id
        
    except Exception as exc:
        logger.error(f"Failed to start pipeline for video {video_id}: {str(exc)}")
        handle_pipeline_error.delay(video_id, str(exc))
        raise


@app.task(bind=True)
def preprocess_video(self, video_id):
    """Задача 1: Препроцессинг видео"""
    try:
        update_execution(video_id, 'preprocess_video', 10)
        
        video = Video.objects.get(id=video_id)
        preprocessor = VideoPreprocessor()
        
        # Получаем путь к видео
        if video.video_url and not video.video_file:
            video_path = preprocessor.download_from_url(video.video_url)
        else:
            video_path = video.video_file.path
        
        logger.info(f"Video preprocessing completed for {video_id}")
        return video_path
        
    except Exception as exc:
        logger.error(f"Video preprocessing failed for {video_id}: {str(exc)}")
        raise

@app.task(bind=True)
def run_ffmpeg_audio(self, audio_input, video_id):
    """Задача 2: Извлечение аудио дорожки"""
    try:
        # audio_input == video_path
        update_execution(video_id, 'run_ffmpeg_audio', 20)
        
        audio_processor = AudioProcessor()
        audio_path = audio_processor.extract_audio(audio_input)
        
        logger.info(f"Audio extraction completed for {video_id}")
        return audio_path
        
    except Exception as exc:
        logger.error(f"Audio extraction failed: {str(exc)}")
        raise

@app.task(bind=True)
def run_ffmpeg_frames(self, video_path, video_id):
    """Задача 3: Нарезка кадров (1 кадр/сек)"""
    try:
        update_execution(video_id, 'run_ffmpeg_frames', 30)
        
        frame_processor = FrameProcessor()
        frames_dir = frame_processor.extract_frames(video_path, fps=1)
        
        logger.info(f"Frame extraction completed for {video_id}")
        return frames_dir
        
    except Exception as exc:
        logger.error(f"Frame extraction failed: {str(exc)}")
        raise

@app.task(bind=True)
def run_whisper_asr(self, audio_path, video_id):
    """Задача 4: Транскрибация аудио через Whisper"""
    try:
        update_execution(video_id, 'run_whisper_asr', 40)
        
        whisper_service = WhisperASRService()
        transcription = whisper_service.transcribe(audio_path)
        
        logger.info(f"Whisper ASR completed for {video_id}")
        return transcription
        
    except Exception as exc:
        logger.error(f"Whisper ASR failed: {str(exc)}")
        raise

@app.task(bind=True)
def run_video_analytics(self, frames_dir, video_id):
    """Задача 5: Анализ кадров через AI модели"""
    try:
        update_execution(video_id, 'run_video_analytics', 50)
        
        analytics_service = VideoAnalyticsService()
        
        # Обрабатываем кадры
        frame_files = [f for f in os.listdir(frames_dir) if f.endswith('.jpg')]
        frame_results = []
        execution = PipelineExecution.objects.get(video_id=video_id)
        
        for i, frame_file in enumerate(frame_files[:5]):  # Обрабатываем первые 5 кадров
            frame_path = os.path.join(frames_dir, frame_file)
            result = analytics_service.analyze_frame(frame_path, i)
            frame_results.append(result)
            
            # Обновляем счетчики API вызовов
            execution.api_calls_count += 2  # YOLO + NSFW
            execution.cost_estimate += 0.0002  # Примерная стоимость
            execution.save()
        
        logger.info(f"Video analytics completed, processed {len(frame_results)} frames")
        return frame_results
        
    except Exception as exc:
        logger.error(f"Video analytics failed: {str(exc)}")
        raise

@app.task(bind=True)
def run_nlp_dictionaries(self, transcription, video_id):
    """Задача 6: Анализ текста по словарям"""
    try:
        update_execution(video_id, 'run_nlp_dictionaries', 80)
        
        nlp_service = NLPDictionaryService()
        text_triggers = nlp_service.analyze_transcription(transcription)
        
        logger.info(f"NLP analysis completed, found {len(text_triggers)} triggers")
        return text_triggers
        
    except Exception as exc:
        logger.error(f"NLP analysis failed: {str(exc)}")
        raise

@app.task(bind=True)
def compile_report(self, results, video_id):
    """Задача 7: Компиляция финального отчета"""
    try:
        execution = PipelineExecution.objects.get(video_id=video_id)
        execution.current_task = 'compile_report'
        execution.progress = 90
        execution.save()
        
        with transaction.atomic():
            video = Video.objects.get(id=video_id)
            compiler = ReportCompiler()
            
            # results содержит [nlp_results, video_results]
            nlp_results, video_results = results
            all_triggers = nlp_results + video_results
            
            # Сохраняем триггеры в БД
            compiler.save_triggers_to_db(video, all_triggers)
            
            # Создаем финальный отчет
            final_report = compiler.compile_final_report(video, all_triggers)
            
            # Обновляем видео
            video.ai_report = final_report
            video.status = VideoStatus.VERIFICATION
            video.processed_at = timezone.now()
            video.save()
            
            # Создаем задачу верификации для оператора
            VerificationTask.objects.get_or_create(video=video)
            
            # Завершаем выполнение пайплайна
            execution.status = PipelineExecution.Status.COMPLETED
            execution.progress = 100
            execution.completed_at = timezone.now()
            execution.processing_time_seconds = (timezone.now() - execution.started_at).total_seconds()
            execution.save()
        
        # Отправляем уведомление клиенту
        from projects.tasks import send_video_ready_notification
        send_video_ready_notification.delay(str(video_id))
        
        logger.info(f"Pipeline completed successfully for {video_id}")
        return final_report
        
    except Exception as exc:
        logger.error(f"Report compilation failed for {video_id}: {str(exc)}")
        handle_pipeline_error.delay(video_id, str(exc))
        raise

@app.task
def handle_pipeline_error(video_id, error_message):
    """Обработчик ошибок пайплайна"""
    try:
        logger.error(f"Handling pipeline error for video {video_id}: {error_message}")
        
        with transaction.atomic():
            video = Video.objects.get(id=video_id)
            video.status = VideoStatus.FAILED
            video.status_message = error_message
            video.save()
            
            execution = PipelineExecution.objects.get(video=video)
            execution.status = PipelineExecution.Status.FAILED
            execution.error_message = error_message
            execution.completed_at = timezone.now()
            execution.save()
        
        logger.error(f"Pipeline failed for video {video_id}")
        
    except Exception as e:
        logger.error(f"Error handling pipeline error for {video_id}: {str(e)}")