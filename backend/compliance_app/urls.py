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
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
import logging

from projects.views_api import ProjectViewSet, VideoViewSet
from ai_pipeline.views_api import AITriggerViewSet, VerificationTaskViewSet, PipelineExecutionViewSet, RiskDefinitionViewSet
from operators.views_api import OperatorLabelViewSet, OperatorActionLogViewSet
from users.views_api import UserViewSet

logger = logging.getLogger(__name__)

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'videos', VideoViewSet, basename='video')
router.register(r'triggers', AITriggerViewSet, basename='trigger')
router.register(r'verification-tasks', VerificationTaskViewSet, basename='verification-task')
router.register(r'pipeline-executions', PipelineExecutionViewSet, basename='pipeline-execution')
router.register(r'risk-definitions', RiskDefinitionViewSet, basename='risk-definition')
router.register(r'operator-labels', OperatorLabelViewSet, basename='operator-label')
router.register(r'operator-logs', OperatorActionLogViewSet, basename='operator-log')
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    # Admin panel
    path('admins/', admin.site.urls),
    
    # API routes (JSON)
    path('api/', include(router.urls)),
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    
    # HTMX/Client routes
    path('client/', include('projects.urls')),
    path('client/users/', include('users.urls')),
    path('client/operators/', include('operators.urls')),
    
    # Root redirect
    path('', RedirectView.as_view(pattern_name='projects:dashboard')),
]

logger.info("URL patterns initialized successfully.")
