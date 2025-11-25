"""
URL configuration for compliance_app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
import logging

logger = logging.getLogger(__name__)

urlpatterns = [
    # Встроенная административная панель Django
    path('admins/', admin.site.urls),
    
    # Маршруты для приложений
    path('users/', include('users.urls')),
    path('projects/', include('projects.urls')),
    path('operators/', include('operators.urls')),  # Исправлено имя приложения
    # path('custom-admin/', include('admin.urls')),  # Временно закомментировано
    
    # Перенаправление корневого URL
    path('', RedirectView.as_view(pattern_name='projects:project_list')),
]

logger.info("URL patterns initialized successfully.")
