from django.urls import path
from django.contrib.auth.decorators import login_required
from . import views
from . import views_htmx

app_name = 'projects'

urlpatterns = [
    path('', views.ProjectListView.as_view(), name='project_list'),
    path('create/', login_required(views.ProjectCreateView.as_view()), name='project_create'),
    path('<uuid:pk>/', login_required(views.ProjectDetailView.as_view()), name='project_detail'),
    path('<uuid:project_id>/upload/', login_required(views.VideoUploadView.as_view()), name='video_upload'),
    path('video/<uuid:video_id>/', login_required(views.VideoDetailView.as_view()), name='video_detail'),
    
    path('dashboard/', login_required(views_htmx.DashboardView.as_view()), name='dashboard'),
    path('htmx/projects/', login_required(views_htmx.ProjectListPartialView.as_view()), name='project_list_partial'),
    path('htmx/projects/create/', login_required(views_htmx.ProjectCreatePartialView.as_view()), name='project_create_partial'),
    path('htmx/projects/<uuid:project_id>/videos/', login_required(views_htmx.VideoListPartialView.as_view()), name='video_list_partial'),
    path('htmx/projects/<uuid:project_id>/upload/', login_required(views_htmx.VideoUploadPartialView.as_view()), name='video_upload_partial'),
    path('htmx/videos/<uuid:video_id>/report/', login_required(views_htmx.ReportDetailPartialView.as_view()), name='report_detail_partial'),
    path('htmx/videos/<uuid:video_id>/signed-url/', login_required(views_htmx.VideoSignedUrlView.as_view()), name='video_signed_url'),
    path('htmx/messages/', login_required(views_htmx.MessagesPartialView.as_view()), name='messages_partial'),
]