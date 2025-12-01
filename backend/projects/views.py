from django.shortcuts import render

# Create your views here.
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, DetailView

from users.views import ClientAccessMixin
from .models import Project, Video, VideoStatus
from .forms import ProjectForm, VideoUploadForm, VideoURLForm

class ProjectListView(LoginRequiredMixin, ClientAccessMixin, ListView):
    model = Project
    template_name = 'projects/project_list.html'
    
    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user)

class ProjectCreateView(LoginRequiredMixin, ClientAccessMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'projects/project_form.html'
    success_url = reverse_lazy('projects:project_list')
    
    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, 'Проект успешно создан!')
        return super().form_valid(form)

class ProjectDetailView(LoginRequiredMixin, ClientAccessMixin, DetailView):
    model = Project
    template_name = 'projects/project_detail.html'
    
    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = context['project']
        
        total_videos = project.videos.count()
        processing_videos = project.videos.filter(
            status__in=[VideoStatus.UPLOADED, VideoStatus.PROCESSING]
        ).count()
        completed_videos = project.videos.filter(
            status=VideoStatus.COMPLETED
        ).count()
        failed_videos = project.videos.filter(
            status=VideoStatus.FAILED
        ).count()
        
        context.update({
            'total_videos': total_videos,
            'processing_videos': processing_videos,
            'completed_videos': completed_videos,
            'failed_videos': failed_videos,
        })
        
        return context

class VideoUploadView(LoginRequiredMixin, ClientAccessMixin, CreateView):
    model = Video
    form_class = VideoUploadForm
    template_name = 'projects/video_upload.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, id=kwargs['project_id'], owner=request.user)
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
        return context
    
    def form_valid(self, form):
        if not self.request.user.has_sufficient_balance(0):
            messages.error(self.request, 'Недостаточно минут на балансе')
            return self.form_invalid(form)
        
        form.instance.project = self.project
        response = super().form_valid(form)
        
        from ai_pipeline.celery_tasks import process_video
        process_video.delay(str(self.object.id))
        
        messages.success(self.request, 'Видео загружено и отправлено на обработку!')
        return response
    
    def get_success_url(self):
        return reverse_lazy('projects:project_detail', kwargs={'pk': self.project.id})

class VideoDetailView(LoginRequiredMixin, ClientAccessMixin, DetailView):
    model = Video
    template_name = 'projects/video_detail.html'
    
    def get_queryset(self):
        return Video.objects.filter(project__owner=self.request.user)
    
    def get_object(self):
        return get_object_or_404(Video, id=self.kwargs['video_id'], project__owner=self.request.user)