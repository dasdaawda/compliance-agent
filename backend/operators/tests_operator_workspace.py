import json
import uuid
from decimal import Decimal
from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient

from users.models import UserRole, User
from projects.models import Video, VideoStatus
from ai_pipeline.models import AITrigger, VerificationTask, RiskDefinition
from operators.models import OperatorLabel, OperatorActionLog
from operators.services import LabelingService, TaskQueueService
from operators.tasks import release_stale_tasks, check_idle_tasks_sla


class OperatorTemplateTest(TestCase):
    """Тесты шаблонов операторского интерфейса"""
    
    def setUp(self):
        self.operator_user = User.objects.create_user(
            username='operator1',
            email='operator1@test.com',
            password='testpass123',
            role=UserRole.OPERATOR
        )
        
        # Create a project first
        from projects.models import Project
        project = Project.objects.create(
            name='Test Project',
            owner=self.operator_user
        )
        
        self.video = Video.objects.create(
            original_name='test_video.mp4',
            status=VideoStatus.COMPLETED,
            project=project,
            video_file=None,
            video_url=None
        )
        
        self.task = VerificationTask.objects.create(
            video=self.video,
            status=VerificationTask.Status.PENDING
        )
        
        self.trigger = AITrigger.objects.create(
            video=self.video,
            trigger_source=AITrigger.TriggerSource.VISION,
            timestamp_sec=10.5,
            confidence=85.0,
            data={'objects': ['person', 'car']}
        )
    
    def test_dashboard_template_renders(self):
        """Тест отображения шаблона дашборда"""
        self.client.force_login(self.operator_user)
        response = self.client.get(reverse('operators:dashboard'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Панель оператора')
        self.assertContains(response, 'htmx-indicator')  # Проверка наличия индикаторов
        self.assertContains(response, 'Взять задачу')
    
    def test_workspace_template_renders_with_static_js(self):
        """Тест отображения шаблона рабочего пространства с загрузкой JS"""
        self.task.assign_to_operator(self.operator_user)
        
        self.client.force_login(self.operator_user)
        response = self.client.get(reverse('operators:verification_workspace', args=[self.task.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Рабочее пространство')
        self.assertContains(response, 'js/operators/workspace.js')  # Проверка загрузки статического JS
        self.assertContains(response, 'data-trigger-id')  # Проверка атрибутов для триггеров
        self.assertContains(response, 'aria-label')  # Проверка доступности
    
    def test_trigger_row_partial_renders_with_context(self):
        """Тест отображения partial для строки триггера с правильным контекстом"""
        self.task.assign_to_operator(self.operator_user)
        
        self.client.force_login(self.operator_user)
        response = self.client.get(reverse('operators:verification_workspace', args=[self.task.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '10.5s')  # Временная метка триггера
        self.assertContains(response, 'VISION')  # Источник триггера
        self.assertContains(response, '85.0%')  # Уверенность
        self.assertContains(response, 'объектов')  # Данные триггера
        self.assertContains(response, 'role="button"')  # Доступность
        self.assertContains(response, 'tabindex="0"')  # Навигация с клавиатуры
    
    def test_task_expired_template_extends_base(self):
        """Тест шаблона истекшей задачи наследует base.html"""
        expired_task = VerificationTask.objects.create(
            video=self.video,
            status=VerificationTask.Status.PENDING,
            expires_at=timezone.now() - timezone.timedelta(hours=1)
        )
        
        self.client.force_login(self.operator_user)
        response = self.client.get(reverse('operators:task_expired', args=[expired_task.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Оператор верификации')  # Из base.html
        self.assertContains(response, 'Время задачи истекло')
        self.assertContains(response, 'navbar')  # Навигационная панель из base.html
    
    def test_task_not_available_template_extends_base(self):
        """Тест шаблона недоступной задачи наследует base.html"""
        self.client.force_login(self.operator_user)
        response = self.client.get(reverse('operators:task_not_available'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Оператор верификации')  # Из base.html
        self.assertContains(response, 'Задача недоступна')
        self.assertContains(response, 'navbar')  # Навигационная панель из base.html
    
    def test_responsive_css_classes_present(self):
        """Тест наличия CSS классов для адаптивности"""
        self.task.assign_to_operator(self.operator_user)
        
        self.client.force_login(self.operator_user)
        response = self.client.get(reverse('operators:verification_workspace', args=[self.task.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'p-3 p-md-2')  # Адаптивные отступы
        self.assertContains(response, 'd-md-none')  # Скрытие на мобильных
        self.assertContains(response, 'flex-wrap')  # Перенос на мобильных
        self.assertContains(response, '@media (max-width: 768px)')  # Media запросы
    
    def test_htmx_indicators_present(self):
        """Тест наличия HTMX индикаторов"""
        self.client.force_login(self.operator_user)
        response = self.client.get(reverse('operators:dashboard'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'hx-indicator')  # Атрибуты индикаторов
        self.assertContains(response, 'htmx-indicator')  # CSS классы индикаторов
        self.assertContains(response, 'spinner-border')  # Bootstrap спиннеры


class OperatorTaskLifecycleTest(TransactionTestCase):
    """Тесты жизненного цикла задач оператора"""
    
    def setUp(self):
        self.operator_user = User.objects.create_user(
            username='operator1',
            email='operator1@test.com',
            password='testpass123',
            role=UserRole.OPERATOR
        )
        
        self.operator_user2 = User.objects.create_user(
            username='operator2',
            email='operator2@test.com',
            password='testpass123',
            role=UserRole.OPERATOR
        )
        
        self.video = Video.objects.create(
            original_name='test_video.mp4',
            status=VideoStatus.COMPLETED,
            file_path='/test/path.mp4'
        )
        
        self.task = VerificationTask.objects.create(
            video=self.video,
            status=VerificationTask.Status.PENDING
        )
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.operator_user)
    
    def test_task_assignment_with_concurrency(self):
        """Тест назначения задачи с предотвращением race conditions"""
        # Создаем две задачи
        task2 = VerificationTask.objects.create(
            video=Video.objects.create(
                original_name='test_video2.mp4',
                status=VideoStatus.COMPLETED
            ),
            status=VerificationTask.Status.PENDING
        )
        
        # Первый оператор берет задачу
        task1 = TaskQueueService.get_next_task(self.operator_user)
        self.assertIsNotNone(task1)
        self.assertEqual(task1.operator, self.operator_user)
        self.assertEqual(task1.status, VerificationTask.Status.IN_PROGRESS)
        
        # Второй оператор не может взять ту же задачу
        task1_again = TaskQueueService.get_next_task(self.operator_user2)
        self.assertIsNotNone(task1_again)
        self.assertNotEqual(task1_again.id, task1.id)
        
        # Проверяем логирование
        self.assertTrue(
            OperatorActionLog.objects.filter(
                operator=self.operator_user,
                task=task1,
                action_type=OperatorActionLog.ActionType.ASSIGNED_TASK
            ).exists()
        )
    
    def test_task_expires_and_releases(self):
        """Тест истечения времени и освобождения задачи"""
        # Назначаем задачу с истекшим временем
        self.task.assign_to_operator(self.operator_user)
        self.task.expires_at = timezone.now() - timezone.timedelta(hours=1)
        self.task.save()
        
        # Запускаем задачу очистки
        result = release_stale_tasks()
        
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, VerificationTask.Status.PENDING)
        self.assertIsNone(self.task.operator)
        self.assertEqual(result['released_count'], 1)
        
        # Проверяем логирование
        self.assertTrue(
            OperatorActionLog.objects.filter(
                operator=self.operator_user,
                task=self.task,
                action_type=OperatorActionLog.ActionType.RELEASED_TASK,
                details__auto_released=True
            ).exists()
        )
    
    def test_task_heartbeat(self):
        """Тест обновления активности задачи"""
        self.task.assign_to_operator(self.operator_user)
        original_expires = self.task.expires_at
        
        # Обновляем heartbeat
        self.task.heartbeat()
        
        self.task.refresh_from_db()
        self.assertGreater(self.task.expires_at, original_expires)
        self.assertIsNotNone(self.task.last_heartbeat)
    
    def test_task_completion(self):
        """Тест завершения задачи"""
        self.task.assign_to_operator(self.operator_user)
        
        decision_summary = "All triggers processed successfully"
        self.task.complete(decision_summary)
        
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, VerificationTask.Status.COMPLETED)
        self.assertEqual(self.task.decision_summary, decision_summary)
        self.assertIsNotNone(self.task.completed_at)
        self.assertGreater(self.task.total_processing_time, 0)
    
    def test_resume_stale_task(self):
        """Тест возобновления устаревшей задачи"""
        # Назначаем и делаем устаревшей
        self.task.assign_to_operator(self.operator_user)
        self.task.expires_at = timezone.now() - timezone.timedelta(hours=1)
        self.task.save()
        
        # Возобновляем
        resumed_task = TaskQueueService.resume_task(self.operator_user, self.task)
        
        self.assertIsNotNone(resumed_task)
        self.assertGreater(resumed_task.expires_at, timezone.now())
        self.assertEqual(resumed_task.operator, self.operator_user)


class OperatorHTMXViewsTest(TestCase):
    """Тесты HTMX представлений оператора"""
    
    def setUp(self):
        self.operator_user = User.objects.create_user(
            username='operator1',
            email='operator1@test.com',
            password='testpass123',
            role=UserRole.OPERATOR
        )
        
        self.other_operator = User.objects.create_user(
            username='operator2',
            email='operator2@test.com',
            password='testpass123',
            role=UserRole.OPERATOR
        )
        
        self.video = Video.objects.create(
            original_name='test_video.mp4',
            status=VideoStatus.COMPLETED,
            signed_url='https://example.com/video.mp4'
        )
        
        self.task = VerificationTask.objects.create(
            video=self.video,
            operator=self.operator_user,
            status=VerificationTask.Status.IN_PROGRESS,
            expires_at=timezone.now() + timezone.timedelta(hours=1)
        )
        
        self.trigger = AITrigger.objects.create(
            video=self.video,
            timestamp_sec=Decimal('10.5'),
            trigger_source=AITrigger.TriggerSource.WHISPER_PROFANITY,
            confidence=Decimal('0.9'),
            data={'text': 'test text', 'matched_word': 'bad_word'}
        )
    
    def test_workspace_view_access_control(self):
        """Тест контроля доступа к рабочему пространству"""
        self.client.force_authenticate(user=self.other_operator)
        
        # Другой оператор не может получить доступ
        response = self.client.get(reverse('operators:verification_workspace', args=[self.task.id]))
        self.assertEqual(response.status_code, 404)
    
    def test_handle_trigger_view_success(self):
        """Тест обработки триггера"""
        self.client.force_authenticate(user=self.operator_user)
        
        data = {
            'final_label': 'profanity_speech',
            'comment': 'Confirmed profanity'
        }
        
        response = self.client.post(
            reverse('operators:handle_trigger', args=[self.task.id, self.trigger.id]),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertTrue(response_data['success'])
        
        # Проверяем, что триггер обработан
        self.trigger.refresh_from_db()
        self.assertEqual(self.trigger.status, AITrigger.Status.PROCESSED)
        
        # Проверяем создание метки оператора
        self.assertTrue(
            OperatorLabel.objects.filter(
                video=self.video,
                operator=self.operator_user,
                ai_trigger=self.trigger,
                final_label='profanity_speech'
            ).exists()
        )
        
        # Проверяем логирование
        self.assertTrue(
            OperatorActionLog.objects.filter(
                operator=self.operator_user,
                task=self.task,
                trigger=self.trigger,
                action_type=OperatorActionLog.ActionType.PROCESSED_TRIGGER
            ).exists()
        )
    
    def test_handle_trigger_view_forbidden(self):
        """Тест обработки триггера с неправильным доступом"""
        self.client.force_authenticate(user=self.other_operator)
        
        data = {
            'final_label': 'profanity_speech',
            'comment': 'Confirmed profanity'
        }
        
        response = self.client.post(
            reverse('operators:handle_trigger', args=[self.task.id, self.trigger.id]),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_complete_verification_view(self):
        """Тест завершения верификации"""
        self.client.force_authenticate(user=self.operator_user)
        
        data = {
            'decision_summary': 'All triggers processed, video is safe'
        }
        
        response = self.client.post(
            reverse('operators:complete_verification', args=[self.task.id]),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertTrue(response_data['success'])
        
        # Проверяем, что задача завершена
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, VerificationTask.Status.COMPLETED)
        self.assertEqual(self.task.decision_summary, 'All triggers processed, video is safe')
    
    def test_heartbeat_view(self):
        """Тест обновления активности"""
        self.client.force_authenticate(user=self.operator_user)
        
        response = self.client.post(
            reverse('operators:heartbeat', args=[self.task.id])
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertTrue(response_data['success'])


class OperatorReportingTest(TestCase):
    """Тесты отчетности с исключением обработанных триггеров"""
    
    def setUp(self):
        self.video = Video.objects.create(
            original_name='test_video.mp4',
            status=VideoStatus.COMPLETED
        )
        
        self.operator_user = User.objects.create_user(
            username='operator1',
            email='operator1@test.com',
            password='testpass123',
            role=UserRole.OPERATOR
        )
        
        # Создаем триггеры с разными статусами
        self.pending_trigger = AITrigger.objects.create(
            video=self.video,
            timestamp_sec=Decimal('10.0'),
            trigger_source=AITrigger.TriggerSource.WHISPER_PROFANITY,
            status=AITrigger.Status.PENDING,
            data={'text': 'bad word'}
        )
        
        self.processed_trigger = AITrigger.objects.create(
            video=self.video,
            timestamp_sec=Decimal('20.0'),
            trigger_source=AITrigger.TriggerSource.YOLO_OBJECT,
            status=AITrigger.Status.PROCESSED,
            data={'objects': [{'class_name': 'person'}]}
        )
        
        # Создаем метку оператора для обработанного триггера
        OperatorLabel.objects.create(
            video=self.video,
            operator=self.operator_user,
            ai_trigger=self.processed_trigger,
            final_label=OperatorLabel.FinalLabel.OK_FALSE,
            start_time_sec=Decimal('20.0')
        )
    
    def test_report_excludes_processed_triggers(self):
        """Тест, что отчет исключает обработанные триггеры"""
        from ai_pipeline.services.ai_services import ReportCompiler
        
        compiler = ReportCompiler()
        report = compiler.compile_final_report_from_db(self.video)
        
        # В отчете должен быть только один триггер (pending)
        self.assertEqual(report['total_triggers'], 1)
        
        # Проверяем, что только pending триггер включен
        trigger_ids = [risk['id'] for risk in report['risks']]
        self.assertIn(str(self.pending_trigger.id), trigger_ids)
        self.assertNotIn(str(self.processed_trigger.id), trigger_ids)
    
    def test_false_positive_triggers_hidden(self):
        """Тест, что триггеры с OK_FALSE скрыты от клиента"""
        from ai_pipeline.services.ai_services import ReportCompiler
        
        compiler = ReportCompiler()
        report = compiler.compile_final_report_from_db(self.video)
        
        # Проверяем, что обработанные триггеры не включены
        self.assertEqual(len(report['risks']), 1)
        self.assertEqual(report['risks'][0]['source'], 'whisper_profanity')


class OperatorActionLogTest(TestCase):
    """Тесты логирования действий оператора"""
    
    def setUp(self):
        self.operator_user = User.objects.create_user(
            username='operator1',
            email='operator1@test.com',
            password='testpass123',
            role=UserRole.OPERATOR
        )
        
        self.video = Video.objects.create(
            original_name='test_video.mp4',
            status=VideoStatus.COMPLETED
        )
        
        self.task = VerificationTask.objects.create(
            video=self.video,
            status=VerificationTask.Status.PENDING
        )
        
        self.trigger = AITrigger.objects.create(
            video=self.video,
            timestamp_sec=Decimal('10.0'),
            trigger_source=AITrigger.TriggerSource.WHISPER_PROFANITY,
            status=AITrigger.Status.PENDING,
            data={'text': 'bad word'}
        )
    
    def test_action_log_creation_for_each_action(self):
        """Тест создания лога для каждого действия оператора"""
        # Назначение задачи
        self.task.assign_to_operator(self.operator_user)
        
        self.assertTrue(
            OperatorActionLog.objects.filter(
                operator=self.operator_user,
                task=self.task,
                action_type=OperatorActionLog.ActionType.ASSIGNED_TASK
            ).exists()
        )
        
        # Heartbeat
        self.task.heartbeat()
        
        self.assertTrue(
            OperatorActionLog.objects.filter(
                operator=self.operator_user,
                task=self.task,
                action_type=OperatorActionLog.ActionType.HEARTBEAT
            ).exists()
        )
        
        # Обработка триггера
        LabelingService.create_operator_label(
            video=self.video,
            operator=self.operator_user,
            ai_trigger=self.trigger,
            final_label=OperatorLabel.FinalLabel.PROFANITY_SPEECH,
            comment='Confirmed profanity'
        )
        
        self.assertTrue(
            OperatorActionLog.objects.filter(
                operator=self.operator_user,
                task=self.task,
                trigger=self.trigger,
                action_type=OperatorActionLog.ActionType.PROCESSED_TRIGGER
            ).exists()
        )
        
        # Завершение задачи
        self.task.complete('All processed')
        
        self.assertTrue(
            OperatorActionLog.objects.filter(
                operator=self.operator_user,
                task=self.task,
                action_type=OperatorActionLog.ActionType.COMPLETED_TASK
            ).exists()
        )
    
    def test_action_log_details_structure(self):
        """Тест структуры деталей в логах действий"""
        self.task.assign_to_operator(self.operator_user)
        
        log_entry = OperatorActionLog.objects.get(
            operator=self.operator_user,
            task=self.task,
            action_type=OperatorActionLog.ActionType.ASSIGNED_TASK
        )
        
        self.assertIsInstance(log_entry.details, dict)
        self.assertIn('task_id', log_entry.details)
        self.assertIn('video_id', log_entry.details)
        self.assertIn('video_name', log_entry.details)
        self.assertIn('expires_at', log_entry.details)


class CeleryTasksTest(TestCase):
    """Тесты Celery задач"""
    
    def setUp(self):
        self.operator_user = User.objects.create_user(
            username='operator1',
            email='operator1@test.com',
            password='testpass123',
            role=UserRole.OPERATOR
        )
        
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True
        )
        
        self.video = Video.objects.create(
            original_name='test_video.mp4',
            status=VideoStatus.COMPLETED
        )
    
    @patch('operators.tasks.send_mail')
    def test_idle_tasks_sla_notification(self, mock_send_mail):
        """Тест уведомления о нарушении SLA"""
        # Создаем старую задачу
        old_task = VerificationTask.objects.create(
            video=self.video,
            status=VerificationTask.Status.PENDING,
            created_at=timezone.now() - timezone.timedelta(hours=5)
        )
        
        result = check_idle_tasks_sla()
        
        self.assertEqual(result['idle_tasks_count'], 1)
        self.assertTrue(result['notified'])
        mock_send_mail.assert_called_once()
    
    def test_cleanup_old_action_logs(self):
        """Тест очистки старых логов"""
        from operators.tasks import cleanup_old_action_logs
        
        # Создаем старый лог
        old_log = OperatorActionLog.objects.create(
            operator=self.operator_user,
            action_type=OperatorActionLog.ActionType.HEARTBEAT,
            timestamp=timezone.now() - timezone.timedelta(days=35)
        )
        
        # Создаем новый лог
        new_log = OperatorActionLog.objects.create(
            operator=self.operator_user,
            action_type=OperatorActionLog.ActionType.HEARTBEAT,
            timestamp=timezone.now() - timezone.timedelta(days=1)
        )
        
        deleted_count = cleanup_old_action_logs(days=30)
        
        self.assertEqual(deleted_count, 1)
        self.assertFalse(OperatorActionLog.objects.filter(id=old_log.id).exists())
        self.assertTrue(OperatorActionLog.objects.filter(id=new_log.id).exists())