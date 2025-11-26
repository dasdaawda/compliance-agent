import logging
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)

from .services import TaskQueueService


@shared_task
def assign_pending_tasks(batch_size: int = 50) -> int:
    """
    Назначает ожидающие задачи свободным операторам.
    - Использует транзакции и select_for_update(skip_locked=True), чтобы избежать race conditions.
    - batch_size ограничивает число операций (защитный механизм для больших систем).
    """
    # локальный импорт чтобы избежать циклических зависимостей при старте процесса
    from users.models import User
    from operators.models import VerificationTask

    assigned_count = 0

    # Получаем активных операторов — адаптируйте фильтр под вашу модель User
    try:
        operators_qs = User.objects.filter(role=getattr(User, 'Role', None).OPERATOR if hasattr(User, 'Role') else 'OPERATOR', is_active=True)
    except Exception:
        operators_qs = User.objects.filter(is_active=True)

    for operator in operators_qs[:batch_size]:
        try:
            with transaction.atomic():
                # берём одну задачу и блокируем её (skip_locked предотвращает блокировки для других воркеров)
                task = (
                    VerificationTask.objects
                    .select_for_update(skip_locked=True)
                    .filter(status=VerificationTask.Status.PENDING)
                    .order_by('created_at')
                    .first()
                )

                if not task:
                    # нет задач — пропускаем
                    continue

                # используем сервис/метод для назначения и сохранения
                assigned = TaskQueueService.get_next_task(operator)
                if assigned:
                    assigned_count += 1
                    logger.info("Assigned task %s to operator %s", getattr(assigned, 'id', None), getattr(operator, 'id', None))
        except Exception as exc:
            logger.exception("Failed to assign task to operator %s: %s", getattr(operator, 'id', None), exc)

    return assigned_count


@shared_task
def release_stale_tasks() -> dict:
    """
    Освобождает задачи с истекшим временем блокировки.
    Возвращает статистику по обработанным задачам.
    """
    from ai_pipeline.models import VerificationTask
    from operators.models import OperatorActionLog

    now = timezone.now()
    released_count = 0
    notified_count = 0
    
    try:
        with transaction.atomic():
            # Находим все устаревшие задачи
            stale_tasks = (
                VerificationTask.objects
                .select_for_update()
                .filter(
                    status=VerificationTask.Status.IN_PROGRESS,
                    expires_at__lt=now
                )
            )
            
            for task in stale_tasks:
                # Логируем освобождение
                OperatorActionLog.objects.create(
                    operator=task.operator,
                    task=task,
                    action_type=OperatorActionLog.ActionType.RELEASED_TASK,
                    details={
                        'task_id': str(task.id),
                        'reason': 'stale_lock',
                        'expired_at': task.expires_at.isoformat() if task.expires_at else None,
                        'auto_released': True,
                    }
                )
                
                # Освобождаем задачу
                task.release_lock()
                released_count += 1
                
                logger.info("Auto-released stale task %s (operator: %s)", task.id, task.operator.username if task.operator else None)
    
    except Exception as exc:
        logger.exception("Error in release_stale_tasks: %s", exc)
        return {'error': str(exc), 'released_count': released_count}
    
    return {
        'released_count': released_count,
        'notified_count': notified_count,
        'timestamp': now.isoformat(),
    }


@shared_task
def check_idle_tasks_sla() -> dict:
    """
    Проверяет задачи, которые слишком долго находятся в статусе PENDING.
    Уведомляет администраторов о задачах, превышающих SLA.
    """
    from ai_pipeline.models import VerificationTask
    from django.contrib.auth.models import User
    
    # SLA: 4 часа для задач в очереди
    sla_threshold = timezone.now() - timezone.timedelta(hours=4)
    
    try:
        # Находим задачи, превышающие SLA
        idle_tasks = VerificationTask.objects.filter(
            status=VerificationTask.Status.PENDING,
            created_at__lt=sla_threshold
        )
        
        if idle_tasks.exists():
            # Получаем администраторов
            admin_users = User.objects.filter(is_staff=True, is_active=True)
            admin_emails = [admin.email for admin in admin_users if admin.email]
            
            if admin_emails:
                subject = f"Превышение SLA: {idle_tasks.count()} задач в очереди"
                message = f"""
Обнаружено {idle_tasks.count()} задач, превышающих SLA (4 часа в очереди):

Задачи:
""" + "\n".join([
                    f"- {task.video.original_name} (создана: {task.created_at.strftime('%Y-%m-%d %H:%M')})"
                    for task in idle_tasks[:10]  # Показываем только первые 10
                ])
                
                if idle_tasks.count() > 10:
                    message += f"\n... и еще {idle_tasks.count() - 10} задач"
                
                try:
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@ai-compliance.com'),
                        recipient_list=admin_emails,
                        fail_silently=False,
                    )
                    logger.info("SLA notification sent to admins: %d idle tasks", idle_tasks.count())
                    notified = True
                except Exception as email_exc:
                    logger.exception("Failed to send SLA notification: %s", email_exc)
                    notified = False
            else:
                logger.warning("No admin emails found for SLA notification")
                notified = False
        else:
            notified = None  # Нет нарушений SLA
        
        return {
            'idle_tasks_count': idle_tasks.count(),
            'sla_threshold_hours': 4,
            'notified': notified is True,
            'timestamp': timezone.now().isoformat(),
        }
        
    except Exception as exc:
        logger.exception("Error in check_idle_tasks_sla: %s", exc)
        return {'error': str(exc)}


@shared_task
def cleanup_old_action_logs(days: int = 30) -> int:
    """
    Очищает старые логи действий операторов.
    """
    from operators.models import OperatorActionLog
    
    cutoff_date = timezone.now() - timezone.timedelta(days=days)
    
    try:
        deleted_count, _ = OperatorActionLog.objects.filter(
            timestamp__lt=cutoff_date
        ).delete()
        
        logger.info("Cleaned up %d old action logs (older than %d days)", deleted_count, days)
        return deleted_count
        
    except Exception as exc:
        logger.exception("Error in cleanup_old_action_logs: %s", exc)
        return 0