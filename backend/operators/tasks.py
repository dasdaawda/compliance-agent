import logging
from celery import shared_task
from django.db import transaction

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