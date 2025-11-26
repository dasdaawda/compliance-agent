from django.contrib import admin
from .models import AITrigger, PipelineExecution, RiskDefinition, VerificationTask


@admin.register(AITrigger)
class AITriggerAdmin(admin.ModelAdmin):
    list_display = ['video', 'trigger_source', 'timestamp_sec', 'confidence', 'status', 'created_at']
    list_filter = ['trigger_source', 'status', 'created_at']
    search_fields = ['video__original_name', 'data']
    list_select_related = ('video', 'video__project', 'risk_code')
    readonly_fields = ('id', 'created_at')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    autocomplete_fields = ('video', 'risk_code')
    list_per_page = 50
    fieldsets = (
        ('Основная информация', {
            'fields': ('id', 'video', 'trigger_source', 'timestamp_sec', 'confidence', 'status')
        }),
        ('Данные', {
            'fields': ('data', 'raw_payload', 'risk_code')
        }),
        ('Даты', {
            'fields': ('created_at',)
        }),
    )


@admin.register(PipelineExecution)
class PipelineExecutionAdmin(admin.ModelAdmin):
    list_display = ['video', 'status', 'current_task', 'progress', 'retry_count', 'started_at', 'completed_at']
    list_filter = ['status', 'started_at']
    search_fields = ['video__original_name']
    list_select_related = ('video', 'video__project')
    readonly_fields = ('id', 'started_at', 'completed_at')
    ordering = ('-started_at',)
    date_hierarchy = 'started_at'
    autocomplete_fields = ('video',)
    list_per_page = 50
    fieldsets = (
        ('Основная информация', {
            'fields': ('id', 'video', 'status', 'current_task', 'progress')
        }),
        ('Резильентность', {
            'fields': ('last_step', 'retry_count', 'error_trace', 'error_message')
        }),
        ('Метрики', {
            'fields': ('processing_time_seconds', 'api_calls_count', 'cost_estimate')
        }),
        ('Даты', {
            'fields': ('started_at', 'completed_at')
        }),
    )


@admin.register(RiskDefinition)
class RiskDefinitionAdmin(admin.ModelAdmin):
    list_display = ['name', 'trigger_source', 'risk_level', 'created_at', 'updated_at']
    list_filter = ['risk_level', 'trigger_source']
    search_fields = ['name', 'description']
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('trigger_source',)
    fieldsets = (
        ('Основная информация', {
            'fields': ('id', 'trigger_source', 'name', 'risk_level')
        }),
        ('Описание', {
            'fields': ('description',)
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(VerificationTask)
class VerificationTaskAdmin(admin.ModelAdmin):
    list_display = ['video', 'operator', 'status', 'priority', 'created_at', 'started_at', 'completed_at']
    list_filter = ['status', 'priority', 'created_at']
    search_fields = ['video__original_name', 'operator__email']
    list_select_related = ('video', 'operator', 'locked_by')
    readonly_fields = ('id', 'created_at', 'updated_at', 'started_at', 'locked_at', 'completed_at')
    ordering = ['priority', 'created_at']
    date_hierarchy = 'created_at'
    autocomplete_fields = ('video', 'operator', 'locked_by')
    list_per_page = 50
    fieldsets = (
        ('Основная информация', {
            'fields': ('id', 'video', 'operator', 'status', 'priority')
        }),
        ('Блокировка', {
            'fields': ('locked_by', 'locked_at', 'expires_at', 'last_heartbeat')
        }),
        ('Результаты', {
            'fields': ('decision_summary', 'total_processing_time')
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at', 'started_at', 'completed_at')
        }),
    )
