from django.urls import path
from . import views

app_name = 'operators'

urlpatterns = [
    path('dashboard/', views.OperatorDashboardView.as_view(), name='dashboard'),
    path('workspace/<uuid:task_id>/', views.VerificationWorkspaceView.as_view(), name='verification_workspace'),
    path('workspace/<uuid:task_id>/heartbeat/', views.HeartbeatView.as_view(), name='heartbeat'),
    path('take-task/', views.TakeTaskView.as_view(), name='take_task'),
    path('resume-task/<uuid:task_id>/', views.ResumeTaskView.as_view(), name='resume_task'),
    path('release-task/<uuid:task_id>/', views.ReleaseTaskView.as_view(), name='release_task'),
    path('workspace/<uuid:task_id>/trigger/<uuid:trigger_id>/', views.HandleTriggerView.as_view(), name='handle_trigger'),
    path('workspace/<uuid:task_id>/complete/', views.CompleteVerificationView.as_view(), name='complete_verification'),
    path('workspace/<uuid:task_id>/trigger/<uuid:trigger_id>/labels/', views.TriggerLabelsPartialView.as_view(), name='trigger_labels_partial'),
    path('workspace/<uuid:task_id>/trigger/<uuid:trigger_id>/row/', views.TriggerRowPartialView.as_view(), name='trigger_row_partial'),
]