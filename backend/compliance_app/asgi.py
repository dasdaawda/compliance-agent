"""
ASGI config for compliance_app project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os
import logging
from django.core.asgi import get_asgi_application

logger = logging.getLogger(__name__)

try:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'compliance_app.settings')
    application = get_asgi_application()
    logger.info("ASGI application initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize ASGI application: {e}")
    raise
