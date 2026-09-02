from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    role_label = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = get_user_model()
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'role_label', 'is_active', 'must_change_password',
            'is_superuser', 'last_login', 'date_joined', 'password_changed_at',
        )

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class UniqueEmailMixin:
    def validate_email(self, value):
        value = value.strip().lower()
        if not value:
            return value
        queryset = get_user_model().objects.filter(email__iexact=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError('An account already uses this email address.')
        return value


class UserCreateSerializer(UniqueEmailMixin, serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = get_user_model()
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'password', 'password_confirm')

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password_confirm'):
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match.'})
        candidate = get_user_model()(
            username=attrs.get('username', ''), email=attrs.get('email', ''),
            first_name=attrs.get('first_name', ''), last_name=attrs.get('last_name', '')
        )
        validate_password(attrs['password'], user=candidate)
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = get_user_model().objects.create_user(
            **validated_data,
            password=password,
            created_by=self.context['request'].user,
            must_change_password=True,
        )
        return user


class UserUpdateSerializer(UniqueEmailMixin, serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ('username', 'email', 'first_name', 'last_name', 'role')


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField()
    new_password = serializers.CharField()
    new_password_confirm = serializers.CharField()

    def validate(self, attrs):
        user = self.context['request'].user
        if not user.check_password(attrs['current_password']):
            raise serializers.ValidationError({'current_password': 'Current password is incorrect.'})
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': 'Passwords do not match.'})
        validate_password(attrs['new_password'], user=user)
        return attrs


class AdminResetPasswordSerializer(serializers.Serializer):
    temporary_password = serializers.CharField()
    temporary_password_confirm = serializers.CharField()

    def validate(self, attrs):
        if attrs['temporary_password'] != attrs['temporary_password_confirm']:
            raise serializers.ValidationError({'temporary_password_confirm': 'Passwords do not match.'})
        validate_password(attrs['temporary_password'], user=self.context['target_user'])
        return attrs
