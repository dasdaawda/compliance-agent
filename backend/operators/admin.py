from django.contrib import admin
from .models import OperatorActionLog, OperatorLabel


@admin.register(OperatorActionLog)
class OperatorActionLogAdmin(admin.ModelAdmin):
    list_display = ['operator', 'action_type', 'task', 'trigger', 'timestamp']
    list_filter = ['action_type', 'timestamp']
    search_fields = ['operator__email', 'details']
    list_select_related = ('operator', 'task', 'trigger')
    readonly_fields = ('id', 'timestamp')
    ordering = ('-timestamp',)
    date_hierarchy = 'timestamp'
    autocomplete_fields = ('operator', 'task', 'trigger')
    list_per_page = 100
    fieldsets = (
        ('Основная информация', {
            'fields': ('id', 'operator', 'action_type', 'timestamp')
        }),
        ('Связи', {
            'fields': ('task', 'trigger')
        }),
        ('Детали', {
            'fields': ('details',)
        }),
    )


@admin.register(OperatorLabel)
class OperatorLabelAdmin(admin.ModelAdmin):
    list_display = ['video', 'operator', 'final_label', 'status', 'confidence', 'start_time_sec', 'created_at']
    list_filter = ['final_label', 'status', 'created_at']
    search_fields = ['video__original_name', 'operator__email', 'comment']
    list_select_related = ('video', 'operator', 'ai_trigger')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    autocomplete_fields = ('video', 'operator', 'ai_trigger')
    list_per_page = 50
    fieldsets = (
        ('Основная информация', {
            'fields': ('id', 'video', 'operator', 'ai_trigger')
        }),
        ('Метка', {
            'fields': ('final_label', 'status', 'confidence', 'start_time_sec', 'end_time_sec')
        }),
        ('Комментарий', {
            'fields': ('comment',)
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at')
        }),
    )
