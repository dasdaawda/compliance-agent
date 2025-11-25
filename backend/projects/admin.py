from django.contrib import admin
from .models import Project, Video


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'owner__email']

    # улучшения
    list_select_related = ('owner',)
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    autocomplete_fields = ('owner',)


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ['original_name', 'project', 'status', 'duration', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['original_name', 'project__name']

    # улучшения
    list_select_related = ('project', 'project__owner')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    autocomplete_fields = ('project',)
    list_per_page = 50