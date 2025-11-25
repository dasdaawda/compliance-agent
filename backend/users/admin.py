from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'company_name', 'role', 'balance_minutes', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active', 'is_active_operator', 'date_joined')
    search_fields = ('email', 'company_name', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'company_name')}),
        ('Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Balance & Metrics', {'fields': ('balance_minutes', 'is_active_operator', 'performance_metric')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'role'),
        }),
    )

    # usability improvements
    list_display_links = ('email',)
    readonly_fields = ('date_joined', 'last_login')
    # autocomplete_fields = ('groups', 'user_permissions')  # Закомментировано чтобы избежать ошибки
    list_per_page = 25