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
    """
    Permission class for attendance operations.
    - All employees can read (GET)
    - Only Administrator and Mentor can create/update/delete
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, 'employee_profile'):
            return False
        
        # All employees can read
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Only Administrator and Mentor can write
        role = request.user.employee_profile.role
        return role in ['administrator', 'mentor', 'dasturchi', 'direktor']


class IsDeveloperDirectorOrAdministrator(permissions.BasePermission):
    """Permission for Developer, Director, Administrator to have full CRUD access"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, 'employee_profile'):
            return False
        
        role = request.user.employee_profile.role
        return role in ['dasturchi', 'direktor', 'administrator']


class CanViewGroups(permissions.BasePermission):
    """Permission for viewing groups: All employees can view (with filtering for Mentors)"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, 'employee_profile'):
            return False
        
        # All employees can view groups
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Only Developer, Director, Administrator can CRUD
        role = request.user.employee_profile.role
        return role in ['dasturchi', 'direktor', 'administrator']
