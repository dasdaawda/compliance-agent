import os
import logging
from celery import Celery

logger = logging.getLogger(__name__)

try:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'compliance_app.settings')

    app = Celery('compliance_app')
    app.config_from_object('django.conf:settings', namespace='CELERY')
    app.autodiscover_tasks()

    app.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='Europe/Moscow',
        enable_utc=True,
        
        task_routes={
            'ai_pipeline.tasks.*': {'queue': 'ai_pipeline'},
            'ai_pipeline.celery_tasks.*': {'queue': 'ai_pipeline'},
            'projects.tasks.*': {'queue': 'projects'},
            'operators.tasks.*': {'queue': 'operators'},
        },
        
        worker_prefetch_multiplier=1,
        task_acks_late=True,
        worker_max_tasks_per_child=100,
    )

    logger.info("Celery application initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize Celery application: {e}")
    raise