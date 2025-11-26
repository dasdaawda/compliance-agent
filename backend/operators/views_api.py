from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db import models

from operators.models import OperatorLabel, OperatorActionLog
from operators.serializers import (
    OperatorLabelSerializer, OperatorLabelCreateSerializer, OperatorActionLogSerializer
)
from users.permissions import IsOperator, IsAdmin


class OperatorLabelViewSet(viewsets.ModelViewSet):
    """ViewSet for OperatorLabel model."""
    permission_classes = [IsAuthenticated, IsOperator | IsAdmin]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['video', 'operator', 'final_label', 'ai_trigger']
    ordering_fields = ['start_time_sec', 'created_at']
    ordering = ['start_time_sec']
    
    def get_queryset(self):
        """Return labels based on user role."""
        user = self.request.user
        
        if user.is_admin:
            return OperatorLabel.objects.all().select_related('video', 'operator', 'ai_trigger')
        elif user.is_operator:
            return OperatorLabel.objects.filter(
                operator=user
            ).select_related('video', 'operator', 'ai_trigger')
        
        return OperatorLabel.objects.none()
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return OperatorLabelCreateSerializer
        return OperatorLabelSerializer
    
    def perform_create(self, serializer):
        """Create label and log action."""
        label = serializer.save(operator=self.request.user)
        
        if label.ai_trigger:
            label.ai_trigger.status = 'processed'
            label.ai_trigger.save()
            
            OperatorActionLog.objects.create(
                operator=self.request.user,
                trigger=label.ai_trigger,
                action_type=OperatorActionLog.ActionType.PROCESSED_TRIGGER,
                details={
                    'label_id': str(label.id),
                    'final_label': label.final_label
                }
            )
    
    @action(detail=False, methods=['get'])
    def my_labels(self, request):
        """Get labels created by current operator."""
        labels = OperatorLabel.objects.filter(
            operator=request.user
        ).select_related('video', 'ai_trigger')
        
        serializer = self.get_serializer(labels, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get operator label statistics."""
        user = request.user
        labels = OperatorLabel.objects.filter(operator=user)
        
        stats = {
            'total_labels': labels.count(),
            'by_final_label': {},
            'by_video': {}
        }
        
        for label_choice in OperatorLabel.FinalLabel.choices:
            count = labels.filter(final_label=label_choice[0]).count()
            stats['by_final_label'][label_choice[0]] = {
                'count': count,
                'display': label_choice[1]
            }
        
        video_counts = labels.values('video__original_name').annotate(
            count=models.Count('id')
        ).order_by('-count')[:10]
        
        for item in video_counts:
            stats['by_video'][item['video__original_name']] = item['count']
        
        return Response(stats)


class OperatorActionLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for OperatorActionLog model (read-only)."""
    serializer_class = OperatorActionLogSerializer
    permission_classes = [IsAuthenticated, IsOperator | IsAdmin]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['operator', 'task', 'trigger', 'action_type']
    ordering_fields = ['timestamp']
    ordering = ['-timestamp']
    
    def get_queryset(self):
        """Return action logs based on user role."""
        user = self.request.user
        
        if user.is_admin:
            return OperatorActionLog.objects.all().select_related('operator', 'task', 'trigger')
        elif user.is_operator:
            return OperatorActionLog.objects.filter(
                operator=user
            ).select_related('operator', 'task', 'trigger')
        
        return OperatorActionLog.objects.none()
    
    @action(detail=False, methods=['get'])
    def my_actions(self, request):
        """Get action logs for current operator."""
        logs = OperatorActionLog.objects.filter(
            operator=request.user
        ).select_related('task', 'trigger')
        
        serializer = self.get_serializer(logs, many=True)
        return Response(serializer.data)
