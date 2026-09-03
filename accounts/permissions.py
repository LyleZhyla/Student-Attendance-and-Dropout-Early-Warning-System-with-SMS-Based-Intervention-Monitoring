from rest_framework.permissions import BasePermission


class IsAdministrator(BasePermission):
    message = 'Administrator access is required.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.role == request.user.Role.ADMIN or request.user.is_superuser)
        )


class IsAttendanceEncoder(BasePermission):
    message = 'Administrator or Teacher access is required to encode attendance.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_superuser
                or request.user.role in (request.user.Role.ADMIN, request.user.Role.TEACHER)
            )
        )
