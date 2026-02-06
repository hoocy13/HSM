from rest_framework.permissions import BasePermission


def _role(user):
    if not user or not user.is_authenticated:
        return None
    try:
        return user.profile.role
    except Exception:
        from .models import UserProfile
        p = UserProfile.objects.filter(user=user).first()
        return p.role if p else None


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return _role(request.user) == 'admin'


class IsDoctor(BasePermission):
    def has_permission(self, request, view):
        return _role(request.user) == 'doctor'


class IsPharmacist(BasePermission):
    def has_permission(self, request, view):
        return _role(request.user) == 'pharmacist'


class IsAdminOrPharmacist(BasePermission):
    def has_permission(self, request, view):
        r = _role(request.user)
        return r in ('admin', 'pharmacist')


class IsAdminOrDoctor(BasePermission):
    def has_permission(self, request, view):
        r = _role(request.user)
        return r in ('admin', 'doctor')
