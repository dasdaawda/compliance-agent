"""
WSGI config for compliance_app project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os
import logging
from django.core.wsgi import get_wsgi_application

logger = logging.getLogger(__name__)

try:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'compliance_app.settings')
    
    # Валидация конфигурации перед запуском
    from compliance_app.config_validator import validate_config
    validate_config()
    
    application = get_wsgi_application()
    logger.info("WSGI application initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize WSGI application: {e}")
    raise
