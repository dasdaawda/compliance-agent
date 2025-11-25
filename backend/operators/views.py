import json
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views.generic import TemplateView, View
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator

from users.views import OperatorRequiredMixin
from projects.models import Video, VideoStatus
from ai_pipeline.models import AITrigger, VerificationTask
from .models import OperatorLabel
from .services import LabelingService, TaskQueueService

class OperatorDashboardView(LoginRequiredMixin, OperatorRequiredMixin, TemplateView):
    template_name = 'operator/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Не назначаем новую задачу случайно при рендере дашборда — показываем текущую в работе
        context['current_task'] = VerificationTask.objects.filter(
            operator=self.request.user,
            status=VerificationTask.Status.IN_PROGRESS
        ).first()
        context['operator_tasks'] = VerificationTask.objects.filter(operator=self.request.user)
        return context

class VerificationWorkspaceView(LoginRequiredMixin, OperatorRequiredMixin, TemplateView):
    template_name = 'operator/workspace.html'
    
    def get(self, request, *args, **kwargs):
        task_id = kwargs.get('task_id')
        task = get_object_or_404(
            VerificationTask, 
            id=task_id, 
            operator=request.user,
            status=VerificationTask.Status.IN_PROGRESS
        )
        return super().get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        task_id = self.kwargs.get('task_id')
        task = get_object_or_404(VerificationTask, id=task_id)
        
        context.update({
            'task': task,
            'video': task.video,
            'ai_triggers': task.video.ai_triggers.filter(status=AITrigger.Status.PENDING).order_by('timestamp_sec'),
            'operator_labels': task.video.operator_labels.all().order_by('start_time_sec'),
        })
        return context

@method_decorator(require_http_methods(["POST"]), name='dispatch')
class TakeTaskView(LoginRequiredMixin, OperatorRequiredMixin, View):
    def post(self, request):
        task = TaskQueueService.get_next_task(request.user)
        
        if task:
            return JsonResponse({
                'success': True,
                'redirect_url': reverse('operators:verification_workspace', kwargs={'task_id': task.id})
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Нет доступных задач в очереди'
            })

@method_decorator(require_http_methods(["POST"]), name='dispatch')
class HandleTriggerView(LoginRequiredMixin, OperatorRequiredMixin, View):
    def post(self, request, task_id, trigger_id):
        try:
            data = json.loads(request.body)
            final_label = data.get('final_label')
            
            with transaction.atomic():
                task = get_object_or_404(VerificationTask, id=task_id, operator=request.user)
                ai_trigger = get_object_or_404(AITrigger, id=trigger_id, video=task.video)
                
                LabelingService.create_operator_label(
                    video=task.video,
                    operator=request.user,
                    ai_trigger=ai_trigger,
                    final_label=final_label,
                )
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Ошибка при обработке триггера: {str(e)}'
            })

@method_decorator(require_http_methods(["POST"]), name='dispatch')
class CompleteVerificationView(LoginRequiredMixin, OperatorRequiredMixin, View):
    def post(self, request, task_id):
        try:
            with transaction.atomic():
                task = get_object_or_404(VerificationTask, id=task_id, operator=request.user)
                task.video.status = VideoStatus.COMPLETED
                task.video.save()
                task.complete_task()
            
            messages.success(request, 'Верификация завершена!')
            return JsonResponse({
                'success': True,
                'redirect_url': reverse('operators:dashboard')
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Ошибка при завершении верификации: {str(e)}'
            })

class TriggerLabelsPartialView(LoginRequiredMixin, OperatorRequiredMixin, View):
    def get(self, request, task_id, trigger_id):
        task = get_object_or_404(VerificationTask, id=task_id)
        ai_trigger = get_object_or_404(AITrigger, id=trigger_id, video=task.video)
        
        available_labels = LabelingService.get_available_labels(ai_trigger.trigger_source)
        
        context = {
            'task': task,
            'ai_trigger': ai_trigger,
            'available_labels': available_labels,
        }
        return render(request, 'operator/partials/label_buttons.html', context)