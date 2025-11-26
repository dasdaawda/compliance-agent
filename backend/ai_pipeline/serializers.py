from rest_framework import serializers
from ai_pipeline.models import AITrigger, VerificationTask, PipelineExecution, RiskDefinition


class AITriggerSerializer(serializers.ModelSerializer):
    """Serializer for AITrigger model."""
    trigger_source_display = serializers.CharField(source='get_trigger_source_display', read_only=True)
    video_name = serializers.CharField(source='video.original_name', read_only=True)
    
    class Meta:
        model = AITrigger
        fields = [
            'id', 'video', 'video_name', 'timestamp_sec',
            'trigger_source', 'trigger_source_display', 'confidence',
            'data', 'status', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class RiskDefinitionSerializer(serializers.ModelSerializer):
    """Serializer for RiskDefinition model."""
    trigger_source_display = serializers.CharField(source='get_trigger_source_display', read_only=True)
    risk_level_display = serializers.CharField(source='get_risk_level_display', read_only=True)
    
    class Meta:
        model = RiskDefinition
        fields = [
            'id', 'trigger_source', 'trigger_source_display',
            'name', 'description', 'risk_level', 'risk_level_display',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class VerificationTaskSerializer(serializers.ModelSerializer):
    """Serializer for VerificationTask model."""
    video_name = serializers.CharField(source='video.original_name', read_only=True)
    operator_name = serializers.CharField(source='operator.username', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_locked = serializers.SerializerMethodField()
    is_stale = serializers.SerializerMethodField()
    
    class Meta:
        model = VerificationTask
        fields = [
            'id', 'video', 'video_name', 'operator', 'operator_name',
            'status', 'status_display', 'started_at', 'completed_at',
            'total_processing_time', 'expires_at', 'last_heartbeat',
            'decision_summary', 'is_locked', 'is_stale'
        ]
        read_only_fields = [
            'id', 'started_at', 'completed_at', 'total_processing_time',
            'expires_at', 'last_heartbeat'
        ]
    
    def get_is_locked(self, obj):
        """Check if task is locked."""
        return obj.is_locked()
    
    def get_is_stale(self, obj):
        """Check if task lock is stale."""
        return obj.is_stale()


class VerificationTaskAssignSerializer(serializers.Serializer):
    """Serializer for assigning verification task to operator."""
    task_id = serializers.UUIDField()


class VerificationTaskHeartbeatSerializer(serializers.Serializer):
    """Serializer for heartbeat update."""
    pass


class VerificationTaskCompleteSerializer(serializers.Serializer):
    """Serializer for completing verification task."""
    decision_summary = serializers.CharField(required=False, allow_blank=True)


class PipelineExecutionSerializer(serializers.ModelSerializer):
    """Serializer for PipelineExecution model."""
    video_name = serializers.CharField(source='video.original_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = PipelineExecution
        fields = [
            'id', 'video', 'video_name', 'status', 'status_display',
            'current_task', 'progress', 'error_message',
            'started_at', 'completed_at', 'processing_time_seconds',
            'api_calls_count', 'cost_estimate'
        ]
        read_only_fields = [
            'id', 'started_at', 'completed_at', 'processing_time_seconds',
            'api_calls_count', 'cost_estimate'
        ]
