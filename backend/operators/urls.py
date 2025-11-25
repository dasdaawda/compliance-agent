from django.urls import path
from . import views

app_name = 'operators'

urlpatterns = [
    path('dashboard/', views.OperatorDashboardView.as_view(), name='dashboard'),
    path('workspace/<uuid:task_id>/', views.VerificationWorkspaceView.as_view(), name='verification_workspace'),
    path('take-task/', views.TakeTaskView.as_view(), name='take_task'),
    path('workspace/<uuid:task_id>/trigger/<uuid:trigger_id>/', views.HandleTriggerView.as_view(), name='handle_trigger'),
    path('workspace/<uuid:task_id>/complete/', views.CompleteVerificationView.as_view(), name='complete_verification'),
    path('workspace/<uuid:task_id>/trigger/<uuid:trigger_id>/labels/', views.TriggerLabelsPartialView.as_view(), name='trigger_labels_partial'),
]