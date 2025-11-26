from rest_framework import permissions
from users.models import UserRole


class IsClient(permissions.BasePermission):
    """Permission class for client users."""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == UserRole.CLIENT


class IsOperator(permissions.BasePermission):
    """Permission class for operator users."""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == UserRole.OPERATOR


class IsAdmin(permissions.BasePermission):
    """Permission class for admin users."""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == UserRole.ADMIN


class IsProjectOwner(permissions.BasePermission):
    """Permission class to check if user owns the project."""
    
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        elif hasattr(obj, 'project'):
            return obj.project.owner == request.user
        return False


class IsTaskAssignee(permissions.BasePermission):
    """Permission class to check if user is assigned to the verification task."""
    
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'operator'):
            return obj.operator == request.user
        elif hasattr(obj, 'verification_task'):
            return obj.verification_task.operator == request.user
        return False
