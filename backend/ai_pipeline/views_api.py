from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from ai_pipeline.models import AITrigger, VerificationTask, PipelineExecution, RiskDefinition
from ai_pipeline.serializers import (
    AITriggerSerializer, VerificationTaskSerializer, PipelineExecutionSerializer,
    RiskDefinitionSerializer, VerificationTaskAssignSerializer,
    VerificationTaskHeartbeatSerializer, VerificationTaskCompleteSerializer
)
from users.permissions import IsClient, IsOperator, IsAdmin, IsProjectOwner, IsTaskAssignee
from operators.models import OperatorActionLog


class AITriggerViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for AITrigger model (read-only for clients)."""
    serializer_class = AITriggerSerializer
    permission_classes = [IsAuthenticated, IsClient | IsOperator | IsAdmin]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['video', 'trigger_source', 'status']
    ordering_fields = ['timestamp_sec', 'confidence', 'created_at']
    ordering = ['timestamp_sec']
    
    def get_queryset(self):
        """Return triggers based on user role."""
        user = self.request.user
        
        if user.is_admin:
            return AITrigger.objects.all().select_related('video', 'video__project')
        elif user.is_operator:
            return AITrigger.objects.filter(
                video__verification_task__operator=user
            ).select_related('video', 'video__project')
        else:
            return AITrigger.objects.filter(
                video__project__owner=user
            ).select_related('video', 'video__project')


class RiskDefinitionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for RiskDefinition model (read-only)."""
    serializer_class = RiskDefinitionSerializer
    permission_classes = [IsAuthenticated]
    queryset = RiskDefinition.objects.all()
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['trigger_source', 'risk_level']
    ordering = ['trigger_source']


class VerificationTaskViewSet(viewsets.ModelViewSet):
    """ViewSet for VerificationTask model."""
    serializer_class = VerificationTaskSerializer
    permission_classes = [IsAuthenticated, IsOperator | IsAdmin]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'operator']
    ordering_fields = ['started_at', 'completed_at']
    ordering = ['-id']
    
    def get_queryset(self):
        """Return tasks based on user role."""
        user = self.request.user
        
        if user.is_admin:
            return VerificationTask.objects.all().select_related('video', 'operator')
        elif user.is_operator:
            return VerificationTask.objects.filter(
                status=VerificationTask.Status.PENDING
            ) | VerificationTask.objects.filter(
                operator=user
            ).select_related('video', 'operator')
        
        return VerificationTask.objects.none()
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending tasks available for assignment."""
        tasks = VerificationTask.objects.filter(
            status=VerificationTask.Status.PENDING
        ).select_related('video')
        
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_tasks(self, request):
        """Get tasks assigned to current operator."""
        tasks = VerificationTask.objects.filter(
            operator=request.user,
            status=VerificationTask.Status.IN_PROGRESS
        ).select_related('video')
        
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """Assign task to current operator."""
        task = self.get_object()
        
        if task.status != VerificationTask.Status.PENDING:
            return Response(
                {'error': f'Task is not pending (current status: {task.status})'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            task.assign_to_operator(request.user)
            
            OperatorActionLog.objects.create(
                operator=request.user,
                task=task,
                action_type=OperatorActionLog.ActionType.ASSIGNED_TASK,
                details={'task_id': str(task.id)}
            )
            
            serializer = self.get_serializer(task)
            return Response(serializer.data)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def heartbeat(self, request, pk=None):
        """Update task heartbeat to keep it locked."""
        task = self.get_object()
        
        if task.operator != request.user:
            return Response(
                {'error': 'You are not assigned to this task'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            task.heartbeat()
            
            OperatorActionLog.objects.create(
                operator=request.user,
                task=task,
                action_type=OperatorActionLog.ActionType.HEARTBEAT,
                details={'task_id': str(task.id)}
            )
            
            serializer = self.get_serializer(task)
            return Response(serializer.data)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete verification task."""
        task = self.get_object()
        
        if task.operator != request.user:
            return Response(
                {'error': 'You are not assigned to this task'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = VerificationTaskCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            decision_summary = serializer.validated_data.get('decision_summary', '')
            task.complete(decision_summary=decision_summary)
            
            OperatorActionLog.objects.create(
                operator=request.user,
                task=task,
                action_type=OperatorActionLog.ActionType.COMPLETED_TASK,
                details={
                    'task_id': str(task.id),
                    'decision_summary': decision_summary
                }
            )
            
            task_serializer = self.get_serializer(task)
            return Response(task_serializer.data)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def release(self, request, pk=None):
        """Release task lock (return to pending)."""
        task = self.get_object()
        
        if task.operator != request.user and not request.user.is_admin:
            return Response(
                {'error': 'You are not assigned to this task'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            task.release_lock()
            
            OperatorActionLog.objects.create(
                operator=request.user,
                task=task,
                action_type=OperatorActionLog.ActionType.RELEASED_TASK,
                details={'task_id': str(task.id)}
            )
            
            serializer = self.get_serializer(task)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PipelineExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for PipelineExecution model (read-only)."""
    serializer_class = PipelineExecutionSerializer
    permission_classes = [IsAuthenticated, IsClient | IsAdmin]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'video']
    ordering_fields = ['started_at', 'completed_at', 'processing_time_seconds']
    ordering = ['-started_at']
    
    def get_queryset(self):
        """Return pipeline executions based on user role."""
        user = self.request.user
        
        if user.is_admin:
            return PipelineExecution.objects.all().select_related('video', 'video__project')
        else:
            return PipelineExecution.objects.filter(
                video__project__owner=user
            ).select_related('video', 'video__project')
