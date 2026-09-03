from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from accounts.permissions import IsRiskReviewer, IsRiskViewer
from audit_logs.models import AuditLog
from students.models import Student

from .models import RiskAssessment
from .serializers import GenerateAssessmentSerializer, ReviewAssessmentSerializer, RiskAssessmentSerializer
from .services import POLICY_VERSION, ReviewedAssessmentExists, generate_assessment


def visible_students(user):
    students = Student.objects.filter(is_active=True)
    if user.is_superuser or user.role in (user.Role.ADMIN, user.Role.GUIDANCE):
        return students
    return students.filter(
        enrollments__status='ENROLLED', enrollments__section__schedules__teacher=user
    ).distinct()


def visible_assessments(user):
    assessments = RiskAssessment.objects.select_related('student', 'generated_by', 'reviewed_by')
    if user.is_superuser or user.role in (user.Role.ADMIN, user.Role.GUIDANCE):
        return assessments
    return assessments.filter(
        student__in=visible_students(user), review_decision=RiskAssessment.ReviewDecision.CONFIRMED
    )


def audit(request, action, assessment, summary):
    AuditLog.objects.create(
        actor=request.user, action=action, object_type=assessment._meta.label,
        object_id=str(assessment.pk), summary=summary,
        metadata={
            'student_id': assessment.student_id, 'score': assessment.score,
            'level': assessment.level, 'review_decision': assessment.review_decision,
            'policy_version': assessment.policy_version,
        },
        ip_address=request.META.get('REMOTE_ADDR'),
    )


@api_view(['GET'])
@permission_classes([IsRiskViewer])
def risk_options_api(request):
    students = visible_students(request.user).order_by('last_name', 'first_name')
    return Response({
        'success': True,
        'students': [{'id': item.pk, 'name': str(item), 'lrn': item.learner_reference_number} for item in students],
        'levels': [{'value': value, 'label': label} for value, label in RiskAssessment.Level.choices],
        'decisions': [{'value': value, 'label': label} for value, label in RiskAssessment.ReviewDecision.choices],
        'can_review': request.user.is_superuser or request.user.role in (request.user.Role.ADMIN, request.user.Role.GUIDANCE),
        'policy_version': POLICY_VERSION,
    })


@api_view(['GET'])
@permission_classes([IsRiskViewer])
def risk_assessments_api(request):
    assessments = visible_assessments(request.user)
    search = request.query_params.get('search', '').strip()
    level = request.query_params.get('level', '').strip()
    decision = request.query_params.get('decision', '').strip()
    if level:
        if level not in RiskAssessment.Level.values:
            return Response({'message': 'Choose a valid risk level.'}, status=400)
        assessments = assessments.filter(level=level)
    if decision:
        if decision not in RiskAssessment.ReviewDecision.values:
            return Response({'message': 'Choose a valid review decision.'}, status=400)
        assessments = assessments.filter(review_decision=decision)
    if search:
        assessments = assessments.filter(
            Q(student__first_name__icontains=search) | Q(student__last_name__icontains=search)
            | Q(student__learner_reference_number__icontains=search)
        )
    scoped = visible_assessments(request.user)
    level_totals = {row['level']: row['total'] for row in scoped.values('level').annotate(total=Count('id'))}
    decision_totals = {row['review_decision']: row['total'] for row in scoped.values('review_decision').annotate(total=Count('id'))}
    return Response({
        'success': True,
        'records': RiskAssessmentSerializer(assessments[:500], many=True, context={'request': request}).data,
        'summary': {
            'total': scoped.count(),
            **{value: level_totals.get(value, 0) for value, _ in RiskAssessment.Level.choices},
            **{value: decision_totals.get(value, 0) for value, _ in RiskAssessment.ReviewDecision.choices},
        },
    })


@api_view(['POST'])
@permission_classes([IsRiskReviewer])
def generate_risk_assessments_api(request):
    serializer = GenerateAssessmentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    assessed_on = serializer.validated_data.get('assessed_on', timezone.localdate())
    if assessed_on > timezone.localdate():
        return Response({'message': 'Assessments cannot be generated for a future date.'}, status=400)
    students = visible_students(request.user).order_by('last_name', 'first_name')
    student_id = serializer.validated_data.get('student')
    if student_id:
        students = students.filter(pk=student_id)
        if not students.exists():
            return Response({'message': 'Student not found or is outside your access.'}, status=404)
    generated = []
    conflicts = []
    with transaction.atomic():
        for student in students:
            try:
                assessment, created = generate_assessment(student, assessed_on, request.user)
            except ReviewedAssessmentExists:
                conflicts.append({'student': student.pk, 'student_name': str(student)})
                continue
            generated.append(assessment)
            audit(
                request, 'RISK_ASSESSMENT_GENERATED', assessment,
                f'{"Generated" if created else "Recalculated"} draft risk assessment for {student}.',
            )
    return Response({
        'success': True,
        'generated': len(generated), 'reviewed_conflicts': conflicts,
        'records': RiskAssessmentSerializer(generated, many=True, context={'request': request}).data,
    }, status=201 if generated else 200)


@api_view(['POST'])
@permission_classes([IsRiskReviewer])
def review_risk_assessment_api(request, record_id):
    assessment = visible_assessments(request.user).filter(pk=record_id).first()
    if not assessment:
        return Response({'message': 'Risk assessment not found.'}, status=404)
    serializer = ReviewAssessmentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    assessment.review_decision = serializer.validated_data['decision']
    assessment.reviewer_notes = serializer.validated_data.get('notes', '').strip()
    assessment.reviewed_by = request.user
    assessment.reviewed_at = timezone.now()
    assessment.full_clean()
    assessment.save(update_fields=(
        'review_decision', 'reviewer_notes', 'reviewed_by', 'reviewed_at', 'updated_at'
    ))
    audit(request, 'RISK_ASSESSMENT_REVIEWED', assessment, f'Reviewed risk assessment for {assessment.student}.')
    return Response({
        'success': True,
        'record': RiskAssessmentSerializer(assessment, context={'request': request}).data,
    })
