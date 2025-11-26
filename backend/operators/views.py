import json
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView, View
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator

from users.views import OperatorRequiredMixin
from projects.models import Video, VideoStatus
from ai_pipeline.models import AITrigger, VerificationTask
from .models import OperatorLabel, OperatorActionLog
from .services import LabelingService, TaskQueueService

class OperatorDashboardView(LoginRequiredMixin, OperatorRequiredMixin, TemplateView):
    template_name = 'operators/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Показываем текущую задачу в работе или stale задачи
        context['current_task'] = VerificationTask.objects.filter(
            operator=self.request.user,
            status__in=[VerificationTask.Status.IN_PROGRESS]
        ).first()
        
        # Показываем stale задачи, которые можно возобновить
        context['stale_tasks'] = VerificationTask.objects.filter(
            operator=self.request.user,
            status=VerificationTask.Status.IN_PROGRESS
        ).filter(
            expires_at__lt=timezone.now()
        )
        
        context['operator_tasks'] = VerificationTask.objects.filter(operator=self.request.user)
        return context

class VerificationWorkspaceView(LoginRequiredMixin, OperatorRequiredMixin, TemplateView):
    template_name = 'operators/workspace.html'
    
    def get(self, request, *args, **kwargs):
        task_id = kwargs.get('task_id')
        with transaction.atomic():
            task = get_object_or_404(
                VerificationTask, 
                id=task_id, 
                operator=request.user
            )
            
            # Проверяем статус и блокировку
            if task.status == VerificationTask.Status.IN_PROGRESS:
                if task.is_stale():
                    # Задача устарела, но можно возобновить
                    task = TaskQueueService.resume_task(request.user, task)
                elif not task.is_locked():
                    # Блокировка истекла, возвращаем в очередь
                    task.release_lock()
                    return render(request, 'operators/task_expired.html', {'task': task})
            else:
                # Задача не в работе
                return render(request, 'operators/task_not_available.html', {'task': task})
        
        return super().get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        task_id = self.kwargs.get('task_id')
        
        with transaction.atomic():
            task = get_object_or_404(VerificationTask, id=task_id)
            
            # Обновляем heartbeat при загрузке страницы
            if task.status == VerificationTask.Status.IN_PROGRESS and task.operator == self.request.user:
                task.heartbeat()
                
                # Логируем heartbeat
                OperatorActionLog.objects.create(
                    operator=self.request.user,
                    task=task,
                    action_type=OperatorActionLog.ActionType.HEARTBEAT,
                    details={
                        'task_id': str(task.id),
                        'expires_at': task.expires_at.isoformat() if task.expires_at else None,
                    }
                )
        
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
class ResumeTaskView(LoginRequiredMixin, OperatorRequiredMixin, View):
    def post(self, request, task_id):
        try:
            with transaction.atomic():
                task = get_object_or_404(VerificationTask, id=task_id, operator=request.user)
                
                if task.status != VerificationTask.Status.IN_PROGRESS:
                    return JsonResponse({
                        'success': False,
                        'message': 'Задача не в работе'
                    })
                
                if not task.is_stale():
                    return JsonResponse({
                        'success': False,
                        'message': 'Задача не устарела'
                    })
                
                # Возобновляем задачу
                task = TaskQueueService.resume_task(request.user, task)
                
                return JsonResponse({
                    'success': True,
                    'redirect_url': reverse('operators:verification_workspace', kwargs={'task_id': task.id})
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Ошибка при возобновлении задачи: {str(e)}'
            })

@method_decorator(require_http_methods(["POST"]), name='dispatch')
class HandleTriggerView(LoginRequiredMixin, OperatorRequiredMixin, View):
    def post(self, request, task_id, trigger_id):
        try:
            data = json.loads(request.body)
            final_label = data.get('final_label')
            comment = data.get('comment', '')
            
            with transaction.atomic():
                # Проверяем, что задача назначена текущему оператору и не истекла
                task = get_object_or_404(
                    VerificationTask, 
                    id=task_id, 
                    operator=request.user,
                    status=VerificationTask.Status.IN_PROGRESS
                )
                
                if task.is_stale():
                    return HttpResponseForbidden("Task lock expired")
                
                ai_trigger = get_object_or_404(AITrigger, id=trigger_id, video=task.video)
                
                LabelingService.create_operator_label(
                    video=task.video,
                    operator=request.user,
                    ai_trigger=ai_trigger,
                    final_label=final_label,
                    comment=comment
                )
                
                # Обновляем heartbeat
                task.heartbeat()
            
            return JsonResponse({'success': True})
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Неверный формат JSON'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Ошибка при обработке триггера: {str(e)}'
            })

@method_decorator(require_http_methods(["POST"]), name='dispatch')
class CompleteVerificationView(LoginRequiredMixin, OperatorRequiredMixin, View):
    def post(self, request, task_id):
        try:
            data = json.loads(request.body)
            decision_summary = data.get('decision_summary', '')
            
            with transaction.atomic():
                task = get_object_or_404(
                    VerificationTask, 
                    id=task_id, 
                    operator=request.user,
                    status=VerificationTask.Status.IN_PROGRESS
                )
                
                if task.is_stale():
                    return HttpResponseForbidden("Task lock expired")
                
                # Завершаем задачу
                task.complete(decision_summary)
                
                # Обновляем статус видео
                try:
                    task.video.status = VideoStatus.COMPLETED
                    task.video.save()
                except Exception:
                    pass
                
                # Логируем завершение
                OperatorActionLog.objects.create(
                    operator=request.user,
                    task=task,
                    action_type=OperatorActionLog.ActionType.COMPLETED_TASK,
                    details={
                        'task_id': str(task.id),
                        'decision_summary': decision_summary,
                        'total_processing_time': task.total_processing_time,
                    }
                )
            
            messages.success(request, 'Верификация завершена!')
            return JsonResponse({
                'success': True,
                'redirect_url': reverse('operators:dashboard')
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Неверный формат JSON'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Ошибка при завершении верификации: {str(e)}'
            })

@method_decorator(require_http_methods(["POST"]), name='dispatch')
class ReleaseTaskView(LoginRequiredMixin, OperatorRequiredMixin, View):
    def post(self, request, task_id):
        try:
            with transaction.atomic():
                task = get_object_or_404(
                    VerificationTask, 
                    id=task_id, 
                    operator=request.user,
                    status=VerificationTask.Status.IN_PROGRESS
                )
                
                # Освобождаем задачу
                task.release_lock()
                
                # Логируем освобождение
                OperatorActionLog.objects.create(
                    operator=request.user,
                    task=task,
                    action_type=OperatorActionLog.ActionType.RELEASED_TASK,
                    details={
                        'task_id': str(task.id),
                    }
                )
            
            return JsonResponse({
                'success': True,
                'redirect_url': reverse('operators:dashboard')
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Ошибка при освобождении задачи: {str(e)}'
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
        return render(request, 'operators/partials/decision_panel.html', context)

class TriggerRowPartialView(LoginRequiredMixin, OperatorRequiredMixin, View):
    def get(self, request, task_id, trigger_id):
        task = get_object_or_404(VerificationTask, id=task_id)
        ai_trigger = get_object_or_404(AITrigger, id=trigger_id, video=task.video)
        
        context = {
            'task': task,
            'ai_trigger': ai_trigger,
            'available_labels': LabelingService.get_available_labels(ai_trigger.trigger_source),
        }
        return render(request, 'operators/partials/trigger_row.html', context)

@method_decorator(require_http_methods(["POST"]), name='dispatch')
class HeartbeatView(LoginRequiredMixin, OperatorRequiredMixin, View):
    def post(self, request, task_id):
        try:
            with transaction.atomic():
                task = get_object_or_404(
                    VerificationTask, 
                    id=task_id, 
                    operator=request.user,
                    status=VerificationTask.Status.IN_PROGRESS
                )
                
                # Обновляем heartbeat
                task.heartbeat()
                
                # Логируем heartbeat
                OperatorActionLog.objects.create(
                    operator=request.user,
                    task=task,
                    action_type=OperatorActionLog.ActionType.HEARTBEAT,
                    details={
                        'task_id': str(task.id),
                        'expires_at': task.expires_at.isoformat() if task.expires_at else None,
                    }
                )
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Ошибка при обновлении активности: {str(e)}'
            })