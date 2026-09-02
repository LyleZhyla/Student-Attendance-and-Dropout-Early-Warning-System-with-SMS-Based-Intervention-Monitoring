from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from audit_logs.models import AuditLog

from .permissions import IsAdministrator
from .serializers import (
    AdminResetPasswordSerializer,
    ChangePasswordSerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)


def client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    return forwarded.split(',')[0].strip() if forwarded else request.META.get('REMOTE_ADDR')


def audit(request, action, target, summary, metadata=None):
    AuditLog.objects.create(
        actor=request.user,
        action=action,
        object_type='accounts.User',
        object_id=str(target.pk),
        summary=summary,
        metadata=metadata or {},
        ip_address=client_ip(request),
    )


def protected_superuser(request, target):
    return target.is_superuser and not request.user.is_superuser


def is_last_active_admin(target):
    if target.role != target.Role.ADMIN or not target.is_active:
        return False
    return not get_user_model().objects.filter(
        role=target.Role.ADMIN, is_active=True
    ).exclude(pk=target.pk).exists()


@api_view(['GET', 'POST'])
@permission_classes([IsAdministrator])
def users_api(request):
    User = get_user_model()
    if request.method == 'GET':
        queryset = User.objects.all().order_by('last_name', 'first_name', 'username')
        search = request.query_params.get('search', '').strip()
        role = request.query_params.get('role', '').strip()
        active = request.query_params.get('active', '').strip().lower()
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) | Q(email__icontains=search)
                | Q(first_name__icontains=search) | Q(last_name__icontains=search)
            )
        if role in User.Role.values:
            queryset = queryset.filter(role=role)
        if active in ('true', 'false'):
            queryset = queryset.filter(is_active=(active == 'true'))
        return Response({
            'success': True,
            'users': UserSerializer(queryset, many=True).data,
            'roles': [{'value': value, 'label': label} for value, label in User.Role.choices],
        })

    serializer = UserCreateSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    audit(request, 'ACCOUNT_CREATED', user, f'Created account {user.username}.', {'role': user.role})
    return Response({'success': True, 'user': UserSerializer(user).data}, status=201)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAdministrator])
def user_detail_api(request, user_id):
    User = get_user_model()
    try:
        target = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({'message': 'Account not found.'}, status=404)
    if protected_superuser(request, target):
        return Response({'message': 'Only a superuser can modify this account.'}, status=403)
    if request.method == 'GET':
        return Response({'success': True, 'user': UserSerializer(target).data})

    previous_role = target.role
    serializer = UserUpdateSerializer(target, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    new_role = serializer.validated_data.get('role', previous_role)
    if new_role != target.Role.ADMIN and is_last_active_admin(target):
        return Response({'message': 'The last active administrator cannot be reassigned.'}, status=400)
    serializer.save()
    audit(
        request, 'ACCOUNT_UPDATED', target, f'Updated account {target.username}.',
        {'previous_role': previous_role, 'role': target.role},
    )
    return Response({'success': True, 'user': UserSerializer(target).data})


@api_view(['POST'])
@permission_classes([IsAdministrator])
def user_status_api(request, user_id):
    User = get_user_model()
    try:
        target = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({'message': 'Account not found.'}, status=404)
    if protected_superuser(request, target):
        return Response({'message': 'Only a superuser can modify this account.'}, status=403)
    active = request.data.get('is_active')
    if not isinstance(active, bool):
        return Response({'message': 'is_active must be true or false.'}, status=400)
    if target.pk == request.user.pk and not active:
        return Response({'message': 'You cannot deactivate your own account.'}, status=400)
    if not active and is_last_active_admin(target):
        return Response({'message': 'The last active administrator cannot be deactivated.'}, status=400)
    target.is_active = active
    target.save(update_fields=['is_active', 'is_staff'])
    if not active:
        Token.objects.filter(user=target).delete()
    action = 'ACCOUNT_ACTIVATED' if active else 'ACCOUNT_DEACTIVATED'
    audit(request, action, target, f'{"Activated" if active else "Deactivated"} account {target.username}.')
    return Response({'success': True, 'user': UserSerializer(target).data})


@api_view(['POST'])
@permission_classes([IsAdministrator])
def admin_reset_password_api(request, user_id):
    User = get_user_model()
    try:
        target = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({'message': 'Account not found.'}, status=404)
    if protected_superuser(request, target):
        return Response({'message': 'Only a superuser can modify this account.'}, status=403)
    serializer = AdminResetPasswordSerializer(data=request.data, context={'target_user': target})
    serializer.is_valid(raise_exception=True)
    target.set_password(serializer.validated_data['temporary_password'])
    target.must_change_password = True
    target.password_changed_at = timezone.now()
    target.save(update_fields=['password', 'must_change_password', 'password_changed_at', 'is_staff'])
    Token.objects.filter(user=target).delete()
    audit(request, 'PASSWORD_RESET_BY_ADMIN', target, f'Reset password for account {target.username}.')
    return Response({'success': True, 'message': 'Temporary password saved. The user must change it at next sign-in.'})


@api_view(['POST'])
def change_password_api(request):
    serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    user = request.user
    user.set_password(serializer.validated_data['new_password'])
    user.must_change_password = False
    user.password_changed_at = timezone.now()
    user.save(update_fields=['password', 'must_change_password', 'password_changed_at', 'is_staff'])
    Token.objects.filter(user=user).delete()
    token = Token.objects.create(user=user)
    audit(request, 'PASSWORD_CHANGED', user, f'Account {user.username} changed its password.')
    return Response({'success': True, 'token': token.key, 'user': UserSerializer(user).data})
