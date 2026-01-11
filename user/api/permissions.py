from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied


class IsDeveloper(permissions.BasePermission):
    def has_permission(self, request, view):  # type: ignore
        if not request.user or not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, 'employee_profile'):
            return False
        
        return request.user.employee_profile.role == 'dasturchi'


class IsDeveloperOrAdministrator(permissions.BasePermission):
    def has_permission(self, request, view):  # type: ignore
        if not request.user or not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, 'employee_profile'):
            return False
        
        role = request.user.employee_profile.role
        return role in ['dasturchi', 'administrator']
    
    def has_object_permission(self, request, view, obj):  # type: ignore
        if not hasattr(request.user, 'employee_profile'):
            return False
        
        user_role = request.user.employee_profile.role
        
        if user_role == 'dasturchi':
            return True
        
        if user_role == 'administrator':
            target_role = obj.role if hasattr(obj, 'role') else None
            
            if target_role in ['dasturchi', 'direktor']:
                raise PermissionDenied('Administrator cannot update Director or Developer roles.')
            
            return True
        
        return False
