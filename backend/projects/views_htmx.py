from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, DetailView, View
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib.messages import get_messages

from users.views import ClientAccessMixin
from projects.models import Project, Video, VideoStatus
from projects.forms import ProjectForm, VideoUploadForm
from storage.b2_utils import get_b2_utils


class DashboardView(LoginRequiredMixin, ClientAccessMixin, ListView):
    """Main dashboard view with HTMX support."""
    model = Project
    template_name = 'client/dashboard.html'
    context_object_name = 'projects'
    
    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        projects = context['projects']
        
        total_videos = Video.objects.filter(project__owner=user).count()
        processing_videos = Video.objects.filter(
            project__owner=user,
            status__in=[VideoStatus.UPLOADED, VideoStatus.PROCESSING]
        ).count()
        completed_videos = Video.objects.filter(
            project__owner=user,
            status=VideoStatus.COMPLETED
        ).count()
        
        context.update({
            'total_projects': projects.count(),
            'total_videos': total_videos,
            'processing_videos': processing_videos,
            'completed_videos': completed_videos,
        })
        
        return context


class ProjectListPartialView(LoginRequiredMixin, ClientAccessMixin, ListView):
    """HTMX partial view for project list."""
    model = Project
    template_name = 'partials/project_list.html'
    context_object_name = 'projects'
    
    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user)
    
    def render_to_response(self, context, **response_kwargs):
        if self.request.htmx:
            return super().render_to_response(context, **response_kwargs)
        return redirect('projects:dashboard')


class ProjectCreatePartialView(LoginRequiredMixin, ClientAccessMixin, CreateView):
    """HTMX partial view for project creation."""
    model = Project
    form_class = ProjectForm
    template_name = 'partials/project_form.html'
    
    def form_valid(self, form):
        form.instance.owner = self.request.user
        self.object = form.save()
        
        if self.request.htmx:
            messages.success(self.request, 'Проект успешно создан!')
            html = render_to_string(
                'partials/project_list.html',
                {'projects': Project.objects.filter(owner=self.request.user)},
                request=self.request
            )
            response = HttpResponse(html)
            response['HX-Trigger'] = '{"projectCreated": true, "messagesUpdated": true}'
            return response
        
        messages.success(self.request, 'Проект успешно создан!')
        return redirect('projects:dashboard')
    
    def form_invalid(self, form):
        if self.request.htmx:
            return super().form_invalid(form)
        messages.error(self.request, 'Ошибка при создании проекта')
        return redirect('projects:dashboard')


class VideoUploadPartialView(LoginRequiredMixin, ClientAccessMixin, CreateView):
    """HTMX partial view for video upload."""
    model = Video
    form_class = VideoUploadForm
    template_name = 'partials/video_upload.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(
            Project,
            id=kwargs.get('project_id'),
            owner=request.user
        )
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
        return context
    
    def form_valid(self, form):
        if not self.request.user.has_sufficient_balance(0):
            if self.request.htmx:
                messages.error(self.request, 'Недостаточно минут на балансе')
                return self.form_invalid(form)
            messages.error(self.request, 'Недостаточно минут на балансе')
            return redirect('projects:project_detail', pk=self.project.id)
        
        form.instance.project = self.project
        self.object = form.save()
        
        from ai_pipeline.celery_tasks import run_full_pipeline
        run_full_pipeline.delay(str(self.object.id))
        
        if self.request.htmx:
            messages.success(self.request, 'Видео загружено и отправлено на обработку!')
            html = render_to_string(
                'partials/video_list.html',
                {'videos': self.project.videos.all(), 'project': self.project},
                request=self.request
            )
            response = HttpResponse(html)
            response['HX-Trigger'] = '{"videosUpdated": {"projectId": "' + str(self.project.id) + '"}, "messagesUpdated": true}'
            return response
        
        messages.success(self.request, 'Видео загружено и отправлено на обработку!')
        return redirect('projects:project_detail', pk=self.project.id)
    
    def form_invalid(self, form):
        if self.request.htmx:
            return super().form_invalid(form)
        messages.error(self.request, 'Ошибка при загрузке видео')
        return redirect('projects:project_detail', pk=self.project.id)


class VideoListPartialView(LoginRequiredMixin, ClientAccessMixin, View):
    """HTMX partial view for video list."""
    
    def get(self, request, project_id):
        project = get_object_or_404(Project, id=project_id, owner=request.user)
        videos = project.videos.all()
        
        html = render_to_string(
            'partials/video_list.html',
            {'videos': videos, 'project': project},
            request=request
        )
        
        return HttpResponse(html)


class ReportDetailPartialView(LoginRequiredMixin, ClientAccessMixin, View):
    """HTMX partial view for report detail."""
    
    def get(self, request, video_id):
        video = get_object_or_404(Video, id=video_id, project__owner=request.user)
        
        if not video.ai_report:
            return HttpResponse('<p class="text-muted">Отчет еще не готов</p>')
        
        html = render_to_string(
            'partials/report_detail.html',
            {'video': video, 'report': video.ai_report},
            request=request
        )
        
        return HttpResponse(html)


class VideoSignedUrlView(LoginRequiredMixin, ClientAccessMixin, View):
    """HTMX view for getting signed video URL."""
    
    def get(self, request, video_id):
        video = get_object_or_404(Video, id=video_id, project__owner=request.user)
        
        if not video.video_url:
            return HttpResponse('<p class="text-danger">URL видео недоступен</p>')
        
        try:
            b2_utils = get_b2_utils()
            b2_path = video.video_url.split('/')[-1] if '/' in video.video_url else video.video_url
            signed_url = b2_utils.generate_signed_url(b2_path, expiration=3600)
            
            # Show the video player row and inject the video element
            html = f'''
            <script>
                document.getElementById('video-player-{video.id}').classList.remove('d-none');
            </script>
            <video controls class="w-100" style="max-height: 400px;">
                <source src="{signed_url}" type="video/mp4">
                Ваш браузер не поддерживает воспроизведение видео.
            </video>
            '''
            return HttpResponse(html)
        except Exception as e:
            return HttpResponse(f'<p class="text-danger">Ошибка при получении URL: {str(e)}</p>')


class MessagesPartialView(LoginRequiredMixin, ClientAccessMixin, View):
    """HTMX partial view for messages."""
    
    def get(self, request):
        html = render_to_string(
            'partials/messages.html',
            {'messages': get_messages(request)},
            request=request
        )
        return HttpResponse(html)
