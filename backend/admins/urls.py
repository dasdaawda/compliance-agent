from django.urls import path
from . import views

app_name = 'admins'

urlpatterns = [
    path('dashboard/', views.AdminDashboardView.as_view(), name='dashboard'),
    path('clients/', views.ClientManagementView.as_view(), name='client_management'),
    path('operators/', views.OperatorManagementView.as_view(), name='operator_management'),
]