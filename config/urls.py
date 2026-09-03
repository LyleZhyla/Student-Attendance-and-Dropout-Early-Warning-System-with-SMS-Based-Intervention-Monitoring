"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, re_path

from core.views import react_app, react_asset
from core.api import dashboard_summary, login_api, logout_api, me_api
from accounts.api import (
    admin_reset_password_api,
    change_password_api,
    user_detail_api,
    user_status_api,
    users_api,
)
from academics.api import (
    academic_options_api, grade_level_detail_api, grade_levels_api, schedule_detail_api, schedules_api,
    school_year_detail_api, school_years_api, section_detail_api, sections_api, subject_detail_api, subjects_api,
)
from students.api import (
    enrollment_detail_api, enrollments_api, guardian_detail_api, guardian_link_detail_api, guardian_links_api,
    guardians_api, student_detail_api, student_options_api, students_api,
)
from attendance.api import (
    attendance_analytics_api, attendance_bulk_api, attendance_options_api, attendance_records_api,
    attendance_roster_api,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/login/', login_api, name='api-login'),
    path('api/auth/logout/', logout_api, name='api-logout'),
    path('api/auth/me/', me_api, name='api-me'),
    path('api/dashboard/summary/', dashboard_summary, name='api-dashboard-summary'),
    path('api/accounts/users/', users_api, name='api-users'),
    path('api/accounts/users/<int:user_id>/', user_detail_api, name='api-user-detail'),
    path('api/accounts/users/<int:user_id>/status/', user_status_api, name='api-user-status'),
    path('api/accounts/users/<int:user_id>/reset-password/', admin_reset_password_api, name='api-admin-reset-password'),
    path('api/account/change-password/', change_password_api, name='api-change-password'),
    path('api/academics/options/', academic_options_api, name='api-academic-options'),
    path('api/academics/school-years/', school_years_api, name='api-school-years'),
    path('api/academics/school-years/<int:record_id>/', school_year_detail_api, name='api-school-year-detail'),
    path('api/academics/grade-levels/', grade_levels_api, name='api-grade-levels'),
    path('api/academics/grade-levels/<int:record_id>/', grade_level_detail_api, name='api-grade-level-detail'),
    path('api/academics/subjects/', subjects_api, name='api-subjects'),
    path('api/academics/subjects/<int:record_id>/', subject_detail_api, name='api-subject-detail'),
    path('api/academics/sections/', sections_api, name='api-sections'),
    path('api/academics/sections/<int:record_id>/', section_detail_api, name='api-section-detail'),
    path('api/academics/schedules/', schedules_api, name='api-schedules'),
    path('api/academics/schedules/<int:record_id>/', schedule_detail_api, name='api-schedule-detail'),
    path('api/students/options/', student_options_api, name='api-student-options'),
    path('api/students/', students_api, name='api-students'),
    path('api/students/<int:record_id>/', student_detail_api, name='api-student-detail'),
    path('api/guardians/', guardians_api, name='api-guardians'),
    path('api/guardians/<int:record_id>/', guardian_detail_api, name='api-guardian-detail'),
    path('api/enrollments/', enrollments_api, name='api-enrollments'),
    path('api/enrollments/<int:record_id>/', enrollment_detail_api, name='api-enrollment-detail'),
    path('api/student-guardians/', guardian_links_api, name='api-student-guardian-links'),
    path('api/student-guardians/<int:record_id>/', guardian_link_detail_api, name='api-student-guardian-link-detail'),
    path('api/attendance/options/', attendance_options_api, name='api-attendance-options'),
    path('api/attendance/roster/', attendance_roster_api, name='api-attendance-roster'),
    path('api/attendance/bulk/', attendance_bulk_api, name='api-attendance-bulk'),
    path('api/attendance/records/', attendance_records_api, name='api-attendance-records'),
    path('api/attendance/analytics/', attendance_analytics_api, name='api-attendance-analytics'),
    path('favicon.svg', react_asset, {'filename': 'favicon.svg'}, name='react-favicon'),
    path('asset-manifest.json', react_asset, {'filename': 'asset-manifest.json'}, name='react-asset-manifest'),
    re_path(r'^(?!api/|admin/).*$', react_app, name='react-app'),
]
