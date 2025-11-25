from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Sum, Q, Prefetch
from django.views.generic import TemplateView

from users.models import User, UserRole
from projects.models import Video, VideoStatus
from ai_pipeline.models import VerificationTask


class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        # Проверяем, что пользователь аутентифицирован и является администратором
        return self.request.user.is_authenticated and getattr(self.request.user, 'is_admin', False)


class AdminDashboardView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    template_name = 'admin/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Оптимизированная статистика по видео (один запрос)
        video_stats = Video.objects.aggregate(
            total=Count('id'),
            processing=Count('id', filter=Q(status=VideoStatus.PROCESSING)),
            verification=Count('id', filter=Q(status=VideoStatus.VERIFICATION)),
            completed=Count('id', filter=Q(status=VideoStatus.COMPLETED)),
        )
        
        # Статистика по операторам
        operator_stats = {
            'total': User.objects.filter(role=UserRole.OPERATOR, is_active=True).count(),
            'active_tasks': VerificationTask.objects.filter(status=VerificationTask.Status.IN_PROGRESS).count(),
        }
        
        # Статистика по клиентам
        client_stats = User.objects.filter(role=UserRole.CLIENT, is_active=True).aggregate(
            total=Count('id'),
            total_balance=Sum('balance_minutes')
        )
        client_stats['total_balance'] = client_stats['total_balance'] or 0
        
        context.update({
            'video_stats': video_stats,
            'operator_stats': operator_stats,
            'client_stats': client_stats,
        })
        return context


class ClientManagementView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    template_name = 'admin/client_management.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Оптимизация запросов с использованием select_related и annotate
        clients = User.objects.filter(role=UserRole.CLIENT).annotate(
            project_count=Count('projects'),
            video_count=Count('projects__videos')
        ).order_by('-date_joined')
        
        context['clients'] = clients
        return context


class OperatorManagementView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    template_name = 'admin/operator_management.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Оптимизация запросов с использованием select_related и annotate
        operators = User.objects.filter(role=UserRole.OPERATOR, is_active=True).annotate(
            completed_tasks=Count('assigned_tasks', filter=Q(assigned_tasks__status=VerificationTask.Status.COMPLETED)),
            active_tasks=Count('assigned_tasks', filter=Q(assigned_tasks__status=VerificationTask.Status.IN_PROGRESS)),
        )
        
        # Видео, ожидающие проверки
        pending_videos = Video.objects.filter(status=VideoStatus.VERIFICATION).exclude(verification_task__isnull=False)
        
        context.update({
            'operators': operators,
            'pending_videos': pending_videos,
        })
        return context
