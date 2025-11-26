from django.contrib import admin
from .models import Project, Video


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'owner__email']

    # улучшения
    list_select_related = ('owner',)
    readonly_fields = ('created_at', 'updated_at', 'id')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    autocomplete_fields = ('owner',)


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ['original_name', 'project', 'status', 'source_type', 'duration', 'file_size', 'created_at']
    list_filter = ['status', 'source_type', 'created_at']
    search_fields = ['original_name', 'project__name', 'checksum_sha256']

    # улучшения
    list_select_related = ('project', 'project__owner')
    readonly_fields = ('created_at', 'updated_at', 'id', 'checksum_sha256', 'processed_at', 'ingest_validated_at')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    autocomplete_fields = ('project',)
    list_per_page = 50
    fieldsets = (
        ('Основная информация', {
            'fields': ('id', 'project', 'original_name', 'status', 'status_message')
        }),
        ('Источник видео', {
            'fields': ('source_type', 'video_file', 'video_url', 'original_extension', 'b2_object_key')
        }),
        ('Метаданные', {
            'fields': ('duration', 'file_size', 'checksum_sha256')
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at', 'ingest_validated_at', 'processed_at')
        }),
        ('Отчет AI', {
            'fields': ('ai_report',),
            'classes': ('collapse',)
        }),
    )