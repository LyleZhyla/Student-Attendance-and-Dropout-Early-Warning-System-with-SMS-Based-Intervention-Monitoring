from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class TardyTrackUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (('TardyTrack', {'fields': ('role', 'must_change_password', 'password_changed_at', 'created_by')}),)
    add_fieldsets = UserAdmin.add_fieldsets + (('TardyTrack', {'fields': ('role', 'must_change_password')}),)
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_active', 'must_change_password')
    list_filter = UserAdmin.list_filter + ('role',)

# Register your models here.
