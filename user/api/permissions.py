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
    """
    Permission class that allows Developer, Director, and Administrator roles.
    For full access to pages (read employees list, etc.)
    """
    def has_permission(self, request, view):  # type: ignore
        if not request.user or not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, 'employee_profile'):
            return False
        
        role = request.user.employee_profile.role
        return role in ['dasturchi', 'direktor', 'administrator']
    
    def has_object_permission(self, request, view, obj):  # type: ignore
        if not hasattr(request.user, 'employee_profile'):
            return False
        
        user_role = request.user.employee_profile.role
        
        # Developer can do everything
        if user_role == 'dasturchi':
            return True
        
        # Director can update/delete everyone except Developer
        if user_role == 'direktor':
            target_role = obj.role if hasattr(obj, 'role') else None
            if target_role == 'dasturchi':
                raise PermissionDenied('Direktor Dasturchi rolini yangilay olmaydi.')
            return True
        
        # Administrator can only update/delete roles below them
        if user_role == 'administrator':
            target_role = obj.role if hasattr(obj, 'role') else None
            
            if target_role in ['dasturchi', 'direktor']:
                raise PermissionDenied('Administrator Direktor yoki Dasturchi rollarini yangilay olmaydi.')
            
            return True
        
        return False


class IsEmployee(permissions.BasePermission):
    """Permission to allow any employee to read, but only Developer/Administrator to write"""
    def has_permission(self, request, view):  # type: ignore
        if not request.user or not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, 'employee_profile'):
            return False
        
        # All employees can read (GET)
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Only Developer and Administrator can write (POST, PUT, PATCH, DELETE)
        role = request.user.employee_profile.role
        return role in ['dasturchi', 'administrator']
