from django.urls import path
from django.contrib.auth.decorators import login_required
from . import views

app_name = 'projects'

urlpatterns = [
    path('', views.ProjectListView.as_view(), name='project_list'),
    path('create/', login_required(views.ProjectCreateView.as_view()), name='project_create'),
    path('<uuid:pk>/', login_required(views.ProjectDetailView.as_view()), name='project_detail'),
    path('<uuid:project_id>/upload/', login_required(views.VideoUploadView.as_view()), name='video_upload'),
    path('video/<uuid:video_id>/', login_required(views.VideoDetailView.as_view()), name='video_detail'),
]