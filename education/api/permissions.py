from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied


class IsAdministrator(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, 'employee_profile'):
            return False
        
        role = request.user.employee_profile.role
        return role in ['administrator', 'dasturchi']


class IsAdministratorOrMentor(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, 'employee_profile'):
            return False
        
        role = request.user.employee_profile.role
        return role in ['administrator', 'mentor', 'dasturchi']
