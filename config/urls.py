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
from reports.api import audit_log_list, report_options, report_preview, report_print
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
from notifications.api import sms_logs_api, sms_options_api, sms_send_api
from interventions.api import (
    intervention_activities_api, intervention_case_detail_api, intervention_cases_api,
    intervention_options_api,
)
from risk_assessment.api import (
    generate_risk_assessments_api, review_risk_assessment_api, risk_assessments_api, risk_options_api,
)
from risk_assessment.well_being_api import (
    well_being_checkin_detail_api, well_being_checkins_api, well_being_options_api,
)

urlpatterns = [
    path('api/reports/options/', report_options, name='api-report-options'),
    path('api/reports/', report_preview, name='api-report-preview'),
    path('api/reports/print/', report_print, name='api-report-print'),
    path('api/audit-logs/', audit_log_list, name='api-audit-logs'),
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
    path('api/notifications/options/', sms_options_api, name='api-sms-options'),
    path('api/notifications/', sms_logs_api, name='api-sms-logs'),
    path('api/notifications/<int:record_id>/send/', sms_send_api, name='api-sms-send'),
    path('api/interventions/options/', intervention_options_api, name='api-intervention-options'),
    path('api/interventions/', intervention_cases_api, name='api-intervention-cases'),
    path('api/interventions/<int:record_id>/', intervention_case_detail_api, name='api-intervention-case-detail'),
    path('api/interventions/<int:record_id>/activities/', intervention_activities_api, name='api-intervention-activities'),
    path('api/risk-assessments/options/', risk_options_api, name='api-risk-options'),
    path('api/risk-assessments/', risk_assessments_api, name='api-risk-assessments'),
    path('api/risk-assessments/generate/', generate_risk_assessments_api, name='api-risk-generate'),
    path('api/risk-assessments/<int:record_id>/review/', review_risk_assessment_api, name='api-risk-review'),
    path('api/well-being/options/', well_being_options_api, name='api-well-being-options'),
    path('api/well-being/', well_being_checkins_api, name='api-well-being-checkins'),
    path('api/well-being/<int:record_id>/', well_being_checkin_detail_api, name='api-well-being-detail'),
    path('favicon.svg', react_asset, {'filename': 'favicon.svg'}, name='react-favicon'),
    path('tardytrack-logo.png', react_asset, {'filename': 'tardytrack-logo.png'}, name='react-logo'),
    path('asset-manifest.json', react_asset, {'filename': 'asset-manifest.json'}, name='react-asset-manifest'),
    re_path(r'^(?!api/|admin/).*$', react_app, name='react-app'),
]
