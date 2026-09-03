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


class IsAttendanceViewer(BasePermission):
    message = 'Attendance monitoring is available to administrators, teachers, students, and linked guardians.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_superuser
                or request.user.role in (
                    request.user.Role.ADMIN,
                    request.user.Role.TEACHER,
                    request.user.Role.STUDENT,
                    request.user.Role.PARENT,
                )
            )
        )


class IsInterventionStaff(BasePermission):
    message = 'Administrator, Guidance Personnel, or Teacher access is required.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_superuser
                or request.user.role in (
                    request.user.Role.ADMIN,
                    request.user.Role.GUIDANCE,
                    request.user.Role.TEACHER,
                )
            )
        )


class IsRiskViewer(BasePermission):
    message = 'Administrator, Guidance Personnel, or Teacher access is required.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_superuser
                or request.user.role in (
                    request.user.Role.ADMIN,
                    request.user.Role.GUIDANCE,
                    request.user.Role.TEACHER,
                )
            )
        )


class IsRiskReviewer(BasePermission):
    message = 'Administrator or Guidance Personnel access is required.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_superuser
                or request.user.role in (request.user.Role.ADMIN, request.user.Role.GUIDANCE)
            )
        )
