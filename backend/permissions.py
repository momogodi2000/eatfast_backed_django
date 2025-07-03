
# backend/permissions.py
from rest_framework import permissions

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow admins to edit objects.
    Read permissions are allowed to any authenticated user.
    """
    
    def has_permission(self, request, view):
        # Read permissions for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        # Write permissions only for admin users
        return request.user and request.user.is_authenticated and request.user.is_staff

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object or admins to edit it.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        # Write permissions for admin users
        if request.user.is_staff:
            return True
        
        # Check if user is owner (for models that have user field)
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        return False

class IsContactOwnerOrAdmin(permissions.BasePermission):
    """
    Permission for contact messages - admin can view all, users can only view their own
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Admin can access all
        if request.user.is_staff:
            return True
        
        # Users can only access their own messages (by email)
        return obj.email == request.user.email

class IsPartnerOwnerOrAdmin(permissions.BasePermission):
    """
    Permission for partner applications - admin can view all, users can only view their own
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Admin can access all
        if request.user.is_staff:
            return True
        
        # Users can only access their own applications (by email)
        return obj.email == request.user.email
