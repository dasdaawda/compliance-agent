import logging
from typing import List, Optional, Any

from django.utils import timezone
from django.db import transaction
from django.core.exceptions import FieldDoesNotExist

from .models import OperatorLabel, OperatorActionLog
from ai_pipeline.models import VerificationTask

logger = logging.getLogger(__name__)

# безопасная попытка получить вложенный FinalLabel — чтобы избежать ImportError/линтеров
try:
    FinalLabel = OperatorLabel.FinalLabel
except Exception:
    FinalLabel = None


class LabelingService:
    # ленивый маппинг — инициализируется при первом обращении
    LABEL_MAPPING = {}
    _mapping_initialized = False

    @classmethod
    def _ensure_mapping(cls):
        if cls._mapping_initialized:
            return
        try:
            from ai_pipeline.models import AITrigger  # локальный импорт для избежания цикла

            def _pref(vals):
                # возвращаем список строк-значений, фильтруя None
                out = []
                for v in (vals or []):
                    if v is None:
                        continue
                    out.append(getattr(v, 'value', str(v)))
                return out

            # явный маппинг по trigger source; создаём ключи и для .name и для .value
            mapping = {}
            if FinalLabel:
                mapping_pairs = {
                    AITrigger.TriggerSource.YOLO_OBJECT: [FinalLabel.OK, FinalLabel.AD_BRAND],
                    AITrigger.TriggerSource.WHISPER_PROFANITY: [FinalLabel.OK_FALSE, FinalLabel.PROFANITY_SPEECH],
                    AITrigger.TriggerSource.FALCONSAI_NSFW: [FinalLabel.OK, FinalLabel.PORNOGRAPHY_18],
                    AITrigger.TriggerSource.VIOLENCE_DETECTOR: [FinalLabel.OK, FinalLabel.VIOLENCE_18],
                }
            else:
                mapping_pairs = {}

            for src, labels in mapping_pairs.items():
                label_values = _pref(labels)
                # ключи: Enum.name (например 'YOLO_OBJECT') и Enum.value (например 'yolo_object')
                mapping[src.name] = label_values
                mapping[src.value] = label_values

            # минимальный fallback
            mapping['default'] = _pref([FinalLabel.OK]) if FinalLabel else []
            cls.LABEL_MAPPING = mapping

        except Exception as exc:
            logger.exception("Failed to initialize LABEL_MAPPING: %s", exc)
            cls.LABEL_MAPPING = {'default': [getattr(FinalLabel, 'OK', 'ok').value if FinalLabel else 'ok']}

        cls._mapping_initialized = True

    @classmethod
    def get_available_labels(cls, trigger_source: Any) -> List[str]:
        cls._ensure_mapping()
        name = getattr(trigger_source, 'name', None)
        value = getattr(trigger_source, 'value', None)
        key = name or value or str(trigger_source)
        return cls.LABEL_MAPPING.get(key, cls.LABEL_MAPPING.get('default', []))

    @classmethod
    def create_operator_label(cls, video, operator, ai_trigger=None, final_label=None,
                              comment: str = "", start_time_sec=None, end_time_sec=None):
        """
        Создаёт OperatorLabel с логированием действия.
        - ai_trigger может быть None (ручное добавление) -> в этом случае требуется start_time_sec.
        - если ai_trigger передан и start_time_sec не указан, берём ai_trigger.timestamp_sec.
        - final_label может быть Enum member (FinalLabel) или строкой (значение choice).
        """
        if final_label is None:
            raise ValueError("final_label is required")

        if ai_trigger is not None and start_time_sec is None:
            start_time_sec = getattr(ai_trigger, 'timestamp_sec', None)

        if start_time_sec is None:
            raise ValueError("start_time_sec must be provided for manual labels (ai_trigger is None)")

        # нормализуем final_label к строковому значению choice
        if hasattr(final_label, 'value'):
            final_label_value = final_label.value
        else:
            final_label_value = str(final_label)

        # валидация final_label по доступным меткам для этого триггера (если ai_trigger передан)
        if ai_trigger is not None:
            available = cls.get_available_labels(getattr(ai_trigger, 'trigger_source', ai_trigger))
            if available and final_label_value not in available:
                logger.warning("final_label '%s' not in available labels %s for trigger %s",
                               final_label_value, available, getattr(ai_trigger, 'id', None))
                # допускаем, но логируем; при необходимости можно бросать ошибку:
                # raise ValueError("final_label not allowed for this trigger_source")

        # подготовка полей для create — учитываем опциональность end_time_sec в модели
        create_kwargs = dict(
            video=video,
            operator=operator,
            ai_trigger=ai_trigger,
            start_time_sec=start_time_sec,
            final_label=final_label_value,
            comment=comment
        )

        # conditionally include end_time_sec if field exists on model
        try:
            OperatorLabel._meta.get_field('end_time_sec')
            create_kwargs['end_time_sec'] = end_time_sec
        except FieldDoesNotExist:
            # модель не содержит end_time_sec — игнорируем переданное значение
            pass

        with transaction.atomic():
            operator_label = OperatorLabel.objects.create(**create_kwargs)

            if ai_trigger is not None:
                try:
                    # безопасно установить статус триггера
                    status_enum = getattr(ai_trigger.__class__, 'Status', None)
                    ai_trigger.status = getattr(status_enum, 'PROCESSED', 'processed') if status_enum else 'processed'
                except Exception:
                    ai_trigger.status = 'processed'
                ai_trigger.save(update_fields=['status'])

            # Опционально: пометить видео как "На верификации" если есть объект VideoStatus
            try:
                from projects.models import VideoStatus
                video.status = getattr(VideoStatus, 'VERIFICATION', VideoStatus.VERIFICATION)  # noqa: F821
                video.save(update_fields=['status'])
            except Exception:
                # если нет VideoStatus или не получилось — пропускаем
                pass

            # Логируем действие оператора
            try:
                task = video.verification_task if hasattr(video, 'verification_task') else None
                OperatorActionLog.objects.create(
                    operator=operator,
                    task=task,
                    trigger=ai_trigger,
                    action_type=OperatorActionLog.ActionType.PROCESSED_TRIGGER,
                    details={
                        'final_label': final_label_value,
                        'comment': comment,
                        'start_time_sec': float(start_time_sec),
                        'ai_trigger_id': str(ai_trigger.id) if ai_trigger else None,
                        'ai_trigger_source': getattr(ai_trigger, 'trigger_source', None) if ai_trigger else None,
                    }
                )
            except Exception as log_exc:
                logger.exception("Failed to log operator action: %s", log_exc)

            return operator_label


class TaskQueueService:
    @classmethod
    def create_verification_task(cls, video):
        task, created = VerificationTask.objects.get_or_create(video=video)
        if created:
            try:
                task.status = VerificationTask.Status.PENDING
            except Exception:
                task.status = 'pending'
            task.save(update_fields=['status'])
        return task

    @classmethod
    def get_next_task(cls, operator):
        """
        Получить следующую задачу с правильной блокировкой и FIFO порядком.
        Использует select_for_update(skip_locked=True) для предотвращения race conditions.
        """
        with transaction.atomic():
            # Блокируем следующую задачу в порядке FIFO
            task = (
                VerificationTask.objects
                .select_for_update(skip_locked=True)
                .filter(status=VerificationTask.Status.PENDING)
                .order_by('created_at', 'id')
                .first()
            )

            if task:
                try:
                    # Назначаем задачу оператору
                    task.assign_to_operator(operator)
                    
                    # Логируем назначение
                    OperatorActionLog.objects.create(
                        operator=operator,
                        task=task,
                        action_type=OperatorActionLog.ActionType.ASSIGNED_TASK,
                        details={
                            'task_id': str(task.id),
                            'video_id': str(task.video.id),
                            'video_name': task.video.original_name,
                            'expires_at': task.expires_at.isoformat() if task.expires_at else None,
                        }
                    )
                    
                    logger.info("Task %s assigned to operator %s", task.id, operator.id)
                    return task
                    
                except Exception as exc:
                    logger.exception("Failed to assign task %s to operator %s: %s", task.id, operator.id, exc)
                    return None
        
        return None
    
    @classmethod
    def resume_task(cls, operator, task):
        """
        Возобновить работу над задачей (если она была назначена ранее этому же оператору)
        """
        with transaction.atomic():
            # Блокируем задачу для проверки
            current_task = (
                VerificationTask.objects
                .select_for_update()
                .get(id=task.id)
            )
            
            if current_task.operator != operator:
                raise ValueError("Task is not assigned to this operator")
            
            if current_task.status != VerificationTask.Status.IN_PROGRESS:
                raise ValueError("Task is not in progress")
            
            # Обновляем heartbeat и продлеваем блокировку
            current_task.heartbeat()
            
            # Логируем возобновление
            OperatorActionLog.objects.create(
                operator=operator,
                task=current_task,
                action_type=OperatorActionLog.ActionType.RESUMED_TASK,
                details={
                    'task_id': str(current_task.id),
                    'new_expires_at': current_task.expires_at.isoformat() if current_task.expires_at else None,
                }
            )
            
            return current_task