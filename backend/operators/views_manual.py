import json
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from django.views.generic import View

from users.views import OperatorRequiredMixin
from ai_pipeline.models import VerificationTask
from .services import LabelingService


@method_decorator(require_http_methods(["POST"]), name='dispatch')
class AddManualLabelView(LoginRequiredMixin, OperatorRequiredMixin, View):
    """Добавление риска вручную оператором (US-O9)."""
    def post(self, request, task_id):
        try:
            data = json.loads(request.body)
            start_time_sec = data.get('start_time_sec')
            final_label = data.get('final_label')
            comment = data.get('comment', '')
            
            if not start_time_sec or not final_label:
                return JsonResponse({
                    'success': False,
                    'message': 'Требуются поля: start_time_sec и final_label'
                })
            
            with transaction.atomic():
                # Проверяем, что задача назначена текущему оператору
                task = get_object_or_404(
                    VerificationTask, 
                    id=task_id, 
                    operator=request.user,
                    status=VerificationTask.Status.IN_PROGRESS
                )
                
                if task.is_stale():
                    return HttpResponseForbidden("Task lock expired")
                
                # Создаем метку вручную (без ai_trigger)
                LabelingService.create_operator_label(
                    video=task.video,
                    operator=request.user,
                    ai_trigger=None,  # Ручное добавление
                    final_label=final_label,
                    comment=comment,
                    start_time_sec=start_time_sec
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
                'message': f'Ошибка при добавлении риска: {str(e)}'
            })
