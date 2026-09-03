from datetime import timedelta

from django.db import transaction
from django.db.models import Count

from attendance.models import AttendanceRecord
from interventions.models import InterventionCase

from .models import RiskAssessment


POLICY_VERSION = 'attendance-v1-draft'
WINDOW_DAYS = 30


class ReviewedAssessmentExists(Exception):
    pass


def attendance_counts(records):
    values = {value: 0 for value, _ in AttendanceRecord.Status.choices}
    for row in records.values('status').annotate(total=Count('id')):
        values[row['status']] = row['total']
    return values


def attendance_rate(counts):
    recorded = sum(counts.values()) - counts[AttendanceRecord.Status.NOT_RECORDED]
    attended = sum(counts[status] for status in (
        AttendanceRecord.Status.PRESENT,
        AttendanceRecord.Status.LATE,
        AttendanceRecord.Status.SCHOOL_ACTIVITY,
    ))
    return round(attended * 100 / recorded, 1) if recorded else 0.0, recorded


def maximum_consecutive_days(values):
    days = sorted(set(values))
    maximum = current = 0
    previous = None
    for day in days:
        current = current + 1 if previous and day == previous + timedelta(days=1) else 1
        maximum = max(maximum, current)
        previous = day
    return maximum


def calculate_risk(student, assessed_on):
    period_start = assessed_on - timedelta(days=WINDOW_DAYS - 1)
    previous_start = period_start - timedelta(days=WINDOW_DAYS)
    previous_end = period_start - timedelta(days=1)
    records = AttendanceRecord.objects.filter(student=student)
    current_records = records.filter(date__range=(period_start, assessed_on))
    previous_records = records.filter(date__range=(previous_start, previous_end))
    current_counts = attendance_counts(current_records)
    previous_counts = attendance_counts(previous_records)
    current_rate, current_recorded = attendance_rate(current_counts)
    previous_rate, previous_recorded = attendance_rate(previous_counts)
    decline = round(max(0, previous_rate - current_rate), 1) if previous_recorded else 0.0
    unexcused = current_counts[AttendanceRecord.Status.ABSENT_UNEXCUSED]
    late = current_counts[AttendanceRecord.Status.LATE]
    consecutive = maximum_consecutive_days(
        current_records.filter(status=AttendanceRecord.Status.ABSENT_UNEXCUSED).values_list('date', flat=True)
    )
    open_statuses = (
        InterventionCase.Status.FOR_REVIEW, InterventionCase.Status.CONTACTING_PARENT,
        InterventionCase.Status.MEETING_SCHEDULED, InterventionCase.Status.HOME_VISIT_SCHEDULED,
        InterventionCase.Status.UNDER_INTERVENTION, InterventionCase.Status.FOR_FOLLOW_UP,
    )
    open_interventions = InterventionCase.objects.filter(student=student, status__in=open_statuses).count()

    components = [
        {
            'key': 'unexcused_absences', 'label': 'Unexcused absences', 'value': unexcused,
            'points': min(unexcused * 8, 40), 'max_points': 40,
            'explanation': '8 points per unexcused absence in the current 30-day window.',
        },
        {
            'key': 'consecutive_unexcused_days', 'label': 'Consecutive unexcused-absence days', 'value': consecutive,
            'points': min(max(consecutive - 1, 0) * 5, 20), 'max_points': 20,
            'explanation': '5 points for each consecutive day after the first, capped at 20.',
        },
        {
            'key': 'late_records', 'label': 'Late attendance records', 'value': late,
            'points': min(late * 3, 15), 'max_points': 15,
            'explanation': '3 points per late record in the current 30-day window.',
        },
        {
            'key': 'attendance_decline', 'label': 'Attendance-rate decline', 'value': decline,
            'unit': 'percentage points', 'points': min(round(decline / 2), 15), 'max_points': 15,
            'explanation': '1 point per 2 percentage points of decline from the previous 30-day period.',
        },
        {
            'key': 'open_interventions', 'label': 'Unresolved interventions', 'value': open_interventions,
            'points': min(open_interventions * 10, 10), 'max_points': 10,
            'explanation': '10 points when at least one intervention remains unresolved.',
        },
    ]
    score = min(sum(item['points'] for item in components), 100)
    level = RiskAssessment.Level.LOW if score < 30 else RiskAssessment.Level.MODERATE if score < 60 else RiskAssessment.Level.HIGH
    indicators = {
        'policy_version': POLICY_VERSION,
        'components': components,
        'metrics': {
            'current_attendance_rate': current_rate,
            'previous_attendance_rate': previous_rate,
            'current_recorded_sessions': current_recorded,
            'previous_recorded_sessions': previous_recorded,
        },
        'disclaimer': 'Early-warning support indicator only; not a diagnosis or automated disciplinary decision.',
    }
    return {
        'score': score, 'level': level, 'indicators': indicators,
        'period_start': period_start, 'period_end': assessed_on,
    }


@transaction.atomic
def generate_assessment(student, assessed_on, generated_by):
    existing = RiskAssessment.objects.select_for_update().filter(
        student=student, assessed_on=assessed_on
    ).first()
    if existing and existing.review_decision != RiskAssessment.ReviewDecision.PENDING:
        raise ReviewedAssessmentExists('A reviewed assessment cannot be overwritten.')
    values = calculate_risk(student, assessed_on)
    if existing:
        for field, value in values.items():
            setattr(existing, field, value)
        existing.policy_version = POLICY_VERSION
        existing.generated_by = generated_by
        existing.reviewer_notes = ''
        existing.full_clean()
        existing.save()
        return existing, False
    assessment = RiskAssessment(
        student=student, assessed_on=assessed_on, policy_version=POLICY_VERSION,
        generated_by=generated_by, **values,
    )
    assessment.full_clean()
    assessment.save()
    return assessment, True
