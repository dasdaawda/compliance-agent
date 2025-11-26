"""
Tests for resilient pipeline and storage features.
Tests for idempotent resume, B2 retry logic, error handling, and notifications.
"""
import json
import uuid
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock

from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.conf import settings

from projects.models import Video, VideoStatus, Project
from projects.validators import VideoValidator, VideoValidationError
from users.models import User, UserRole
from ai_pipeline.models import PipelineExecution, AITrigger
from storage.b2_utils import B2Utils, B2RetryableError


class VideoValidationTests(TestCase):
    """Tests for video validation before pipeline starts."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass',
            role=UserRole.ADMIN
        )
        self.project = Project.objects.create(
            name='Test Project',
            owner=self.user,
        )
        self.validator = VideoValidator()

    def test_validate_video_success(self):
        """Test that validation passes for valid video."""
        video = Video.objects.create(
            project=self.project,
            original_name='test.mp4',
            file_size=1024 * 1024 * 500,  # 500MB
            duration=3600,  # 1 hour
        )
        
        # Should not raise
        result = self.validator.validate_video(video)
        self.assertTrue(result)

    def test_validate_video_file_too_large(self):
        """Test that validation fails for oversized video."""
        video = Video.objects.create(
            project=self.project,
            original_name='test.mp4',
            file_size=3 * 1024 * 1024 * 1024,  # 3GB, exceeds 2GB default
            duration=3600,
        )
        
        with self.assertRaises(VideoValidationError) as context:
            self.validator.validate_video(video)
        
        self.assertIn('exceeds maximum', str(context.exception))

    def test_validate_video_duration_too_long(self):
        """Test that validation fails for video with excessive duration."""
        video = Video.objects.create(
            project=self.project,
            original_name='test.mp4',
            file_size=1024 * 1024 * 500,
            duration=10000,  # ~2.8 hours, exceeds 2 hour default
        )
        
        with self.assertRaises(VideoValidationError) as context:
            self.validator.validate_video(video)
        
        self.assertIn('exceeds maximum', str(context.exception))

    def test_validate_video_unsupported_format(self):
        """Test that validation fails for unsupported file format."""
        video = Video.objects.create(
            project=self.project,
            original_name='test.xyz',
            file_size=1024 * 1024 * 500,
            duration=3600,
        )
        
        with self.assertRaises(VideoValidationError) as context:
            self.validator.validate_video(video)
        
        self.assertIn('not allowed', str(context.exception))


class B2UtilsRetryTests(TestCase):
    """Tests for B2 storage utilities with retry logic."""

    def setUp(self):
        self.b2_utils = B2Utils()

    @patch('storage.b2_utils.BackblazeService')
    def test_upload_video_success(self, mock_service_class):
        """Test successful video upload."""
        mock_service = Mock()
        mock_service.upload_file.return_value = 'https://cdn.example.com/video.mp4'
        mock_service_class.return_value = mock_service
        
        b2_utils = B2Utils()
        
        result = b2_utils.upload_video('/tmp/test.mp4', 'videos/test.mp4')
        self.assertEqual(result, 'https://cdn.example.com/video.mp4')
        mock_service.upload_file.assert_called_once()

    @patch('storage.b2_utils.BackblazeService')
    def test_upload_video_file_not_found(self, mock_service_class):
        """Test upload fails gracefully for missing file."""
        b2_utils = B2Utils()
        
        with self.assertRaises(FileNotFoundError):
            b2_utils.upload_video('/nonexistent/file.mp4', 'videos/test.mp4')

    @patch('storage.b2_utils.BackblazeService')
    def test_generate_signed_url_caching(self, mock_service_class):
        """Test that signed URLs are cached."""
        mock_service = Mock()
        mock_service.generate_presigned_url.return_value = 'https://signed.example.com/video.mp4'
        mock_service_class.return_value = mock_service
        
        b2_utils = B2Utils()
        
        # First call should generate URL
        url1 = b2_utils.generate_signed_url('videos/test.mp4')
        self.assertEqual(url1, 'https://signed.example.com/video.mp4')
        
        # Second call should use cache
        url2 = b2_utils.generate_signed_url('videos/test.mp4')
        self.assertEqual(url2, 'https://signed.example.com/video.mp4')
        
        # Service should only be called once
        self.assertEqual(mock_service.generate_presigned_url.call_count, 1)


class PipelineResilienceTests(TransactionTestCase):
    """Tests for pipeline resilience, retries, and idempotent resume."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass',
            role=UserRole.ADMIN
        )
        self.project = Project.objects.create(
            name='Test Project',
            owner=self.user,
        )
        self.video = Video.objects.create(
            project=self.project,
            original_name='test.mp4',
            file_size=1024 * 1024 * 500,
            duration=3600,
        )

    def test_pipeline_execution_tracking(self):
        """Test that pipeline execution tracks progress and retries."""
        execution = PipelineExecution.objects.create(
            video=self.video,
            status=PipelineExecution.Status.RUNNING,
            started_at=timezone.now(),
        )
        
        # Simulate progress update
        execution.current_task = 'preprocess_video'
        execution.progress = 10
        execution.last_step = 'preprocess_video'
        execution.save()
        
        # Verify state
        execution.refresh_from_db()
        self.assertEqual(execution.current_task, 'preprocess_video')
        self.assertEqual(execution.progress, 10)
        self.assertEqual(execution.last_step, 'preprocess_video')

    def test_pipeline_error_trace_recording(self):
        """Test that error traces are recorded for debugging."""
        execution = PipelineExecution.objects.create(
            video=self.video,
            status=PipelineExecution.Status.RUNNING,
            error_trace=[],
        )
        
        # Simulate error
        error_entry = {
            'timestamp': timezone.now().isoformat(),
            'step': 'run_whisper_asr',
            'error': 'API timeout',
        }
        execution.error_trace.append(error_entry)
        execution.save()
        
        # Verify error was recorded
        execution.refresh_from_db()
        self.assertEqual(len(execution.error_trace), 1)
        self.assertEqual(execution.error_trace[0]['step'], 'run_whisper_asr')

    def test_pipeline_idempotent_resume(self):
        """Test that pipeline can be resumed from last successful step."""
        execution = PipelineExecution.objects.create(
            video=self.video,
            status=PipelineExecution.Status.FAILED,
            last_step='run_ffmpeg_frames',
            error_message='Video analytics failed',
        )
        
        # Simulate retry
        execution.status = PipelineExecution.Status.RUNNING
        execution.retry_count += 1
        execution.progress = 50  # Resume from run_video_analytics
        execution.save()
        
        # Verify resume state
        execution.refresh_from_db()
        self.assertEqual(execution.retry_count, 1)
        self.assertEqual(execution.last_step, 'run_ffmpeg_frames')
        self.assertEqual(execution.status, PipelineExecution.Status.RUNNING)


class PipelineErrorHandlingTests(TransactionTestCase):
    """Tests for error handling and notifications."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass',
            role=UserRole.ADMIN
        )
        self.project = Project.objects.create(
            name='Test Project',
            owner=self.user,
        )
        self.video = Video.objects.create(
            project=self.project,
            original_name='test.mp4',
            file_size=1024 * 1024 * 500,
            duration=3600,
        )

    @patch('projects.tasks.send_mail')
    def test_pipeline_failure_notification(self, mock_send_mail):
        """Test that failure notifications are sent to admins."""
        from projects.tasks import send_pipeline_failure_notification
        
        # Call the notification task
        with patch('projects.tasks.settings.ADMIN_EMAIL', 'admin@example.com'):
            send_pipeline_failure_notification(str(self.video.id), 'whisper_asr', 'API timeout')
        
        # Verify email was sent
        mock_send_mail.assert_called_once()
        call_args = mock_send_mail.call_args
        self.assertIn('admin@example.com', call_args[1]['recipient_list'])
        self.assertIn('whisper_asr', call_args[1]['subject'])

    @patch('projects.tasks.send_mail')
    def test_validation_failure_notification(self, mock_send_mail):
        """Test that validation failure notifications are sent."""
        from projects.validators import notify_validation_failure
        
        error_msg = "File size exceeds maximum"
        notify_validation_failure(self.video, error_msg)
        
        # Verify email was sent
        mock_send_mail.assert_called_once()
        call_args = mock_send_mail.call_args
        self.assertIn(self.user.email, call_args[1]['recipient_list'])
        self.assertIn('Ошибка валидации', call_args[1]['subject'])


class ReportCompilerTests(TestCase):
    """Tests for report compilation from database."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass',
            role=UserRole.ADMIN
        )
        self.project = Project.objects.create(
            name='Test Project',
            owner=self.user,
        )
        self.video = Video.objects.create(
            project=self.project,
            original_name='test.mp4',
            file_size=1024 * 1024 * 500,
            duration=3600,
        )

    def test_compile_report_from_db_filters_by_status(self):
        """Test that report compilation only includes PENDING triggers."""
        from ai_pipeline.services.ai_services import ReportCompiler
        
        # Create triggers with different statuses
        pending_trigger = AITrigger.objects.create(
            video=self.video,
            timestamp_sec=Decimal('10.5'),
            trigger_source=AITrigger.TriggerSource.WHISPER_PROFANITY,
            confidence=Decimal('0.95'),
            data={'matched_word': 'bad_word'},
            status=AITrigger.Status.PENDING,
        )
        
        processed_trigger = AITrigger.objects.create(
            video=self.video,
            timestamp_sec=Decimal('20.5'),
            trigger_source=AITrigger.TriggerSource.WHISPER_BRAND,
            confidence=Decimal('0.85'),
            data={'matched_brand': 'brand_name'},
            status=AITrigger.Status.PROCESSED,
        )
        
        # Compile report
        compiler = ReportCompiler()
        report = compiler.compile_final_report_from_db(self.video)
        
        # Should only include pending trigger
        self.assertEqual(report['total_triggers'], 1)
        self.assertEqual(len(report['risks']), 1)
        self.assertEqual(report['risks'][0]['source'], 'whisper_profanity')

    def test_compile_report_includes_risk_definitions(self):
        """Test that report includes RiskDefinition metadata."""
        from ai_pipeline.models import RiskDefinition
        from ai_pipeline.services.ai_services import ReportCompiler
        
        # Create risk definition
        risk_def = RiskDefinition.objects.create(
            trigger_source=AITrigger.TriggerSource.FALCONSAI_NSFW,
            name='NSFW Content',
            description='Sexually explicit or nude content',
            risk_level='high',
        )
        
        # Create trigger
        AITrigger.objects.create(
            video=self.video,
            timestamp_sec=Decimal('15.0'),
            trigger_source=AITrigger.TriggerSource.FALCONSAI_NSFW,
            confidence=Decimal('0.92'),
            data={'score': 0.92},
            status=AITrigger.Status.PENDING,
        )
        
        # Compile report
        compiler = ReportCompiler()
        report = compiler.compile_final_report_from_db(self.video)
        
        # Verify risk definition metadata is included
        self.assertEqual(len(report['risks']), 1)
        risk = report['risks'][0]
        self.assertEqual(risk['risk_level'], 'high')
        self.assertEqual(risk['risk_name'], 'NSFW Content')


class StructuredLoggingTests(TestCase):
    """Tests for structured JSON logging of pipeline stages."""

    def test_pipeline_step_logging(self):
        """Test that pipeline steps are logged with structured JSON."""
        from ai_pipeline.celery_tasks import log_pipeline_step
        
        with patch('ai_pipeline.celery_tasks.logger') as mock_logger:
            video_id = uuid.uuid4()
            log_pipeline_step(video_id, 'preprocess_video', 'completed')
            
            # Verify logger was called with JSON
            mock_logger.info.assert_called_once()
            log_call_arg = mock_logger.info.call_args[0][0]
            
            # Should be valid JSON
            log_data = json.loads(log_call_arg)
            self.assertEqual(log_data['step'], 'preprocess_video')
            self.assertEqual(log_data['status'], 'completed')
            self.assertEqual(str(log_data['video_id']), str(video_id))
