from rest_framework import serializers
from operators.models import OperatorLabel, OperatorActionLog


class OperatorLabelSerializer(serializers.ModelSerializer):
    """Serializer for OperatorLabel model."""
    video_name = serializers.CharField(source='video.original_name', read_only=True)
    operator_name = serializers.CharField(source='operator.username', read_only=True)
    final_label_display = serializers.CharField(source='get_final_label_display', read_only=True)
    trigger_source = serializers.CharField(source='ai_trigger.trigger_source', read_only=True, allow_null=True)
    
    class Meta:
        model = OperatorLabel
        fields = [
            'id', 'video', 'video_name', 'operator', 'operator_name',
            'ai_trigger', 'trigger_source', 'start_time_sec',
            'final_label', 'final_label_display', 'comment',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'operator', 'created_at', 'updated_at']
    
    def validate(self, attrs):
        """Validate operator label data."""
        request = self.context.get('request')
        if request and request.user:
            attrs['operator'] = request.user
        
        ai_trigger = attrs.get('ai_trigger')
        video = attrs.get('video')
        
        if ai_trigger and ai_trigger.video != video:
            raise serializers.ValidationError("AI trigger does not belong to the specified video.")
        
        return attrs


class OperatorLabelCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating operator labels."""
    
    class Meta:
        model = OperatorLabel
        fields = [
            'id', 'video', 'ai_trigger', 'start_time_sec',
            'final_label', 'comment', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def create(self, validated_data):
        """Create operator label with current user as operator."""
        validated_data['operator'] = self.context['request'].user
        return super().create(validated_data)


class OperatorActionLogSerializer(serializers.ModelSerializer):
    """Serializer for OperatorActionLog model."""
    operator_name = serializers.CharField(source='operator.username', read_only=True)
    action_type_display = serializers.CharField(source='get_action_type_display', read_only=True)
    task_id = serializers.UUIDField(source='task.id', read_only=True, allow_null=True)
    trigger_id = serializers.UUIDField(source='trigger.id', read_only=True, allow_null=True)
    
    class Meta:
        model = OperatorActionLog
        fields = [
            'id', 'operator', 'operator_name', 'task', 'task_id',
            'trigger', 'trigger_id', 'action_type', 'action_type_display',
            'details', 'timestamp'
        ]
        read_only_fields = ['id', 'operator', 'timestamp']
