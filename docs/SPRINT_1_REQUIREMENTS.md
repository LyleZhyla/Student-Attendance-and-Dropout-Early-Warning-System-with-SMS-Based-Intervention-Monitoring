# Sprint 1 Requirements Baseline

Status: implemented as the project foundation. Policy values marked **To validate** require confirmation by school administrators, guidance personnel, and the research adviser before automation.

## Product goal

TardyTrack records attendance, identifies students who may need support, coordinates interventions or home visits, and informs verified guardians through auditable SMS workflows. A risk result is an early-warning indicator, not a medical diagnosis or an automated disciplinary decision.

## Roles and access

| Role | Initial scope |
|---|---|
| Administrator | Manage accounts/master data, monitor all operational records, reports, SMS, interventions, and audit logs |
| Teacher | View assigned classes/students, encode and correct permitted attendance, view appropriate support indicators |
| Student | View only their own attendance summary and approved support information |
| Parent/Guardian | View only linked children and receive consented notifications |
| Guidance Personnel | Restricted access to well-being responses, reviewed risks, referrals, and interventions |

Sensitive well-being answers must not be exposed in ordinary teacher, student, parent, or report views. Object-level permissions will be implemented in Sprint 2.

## Attendance rules

Supported statuses: Present, Late, Excused Absence, Unexcused Absence, School Activity, and Not Recorded.

- Exactly one record per student, class schedule, and date.
- Future dates are rejected.
- Excused absence requires a reason.
- Encoder and create/update timestamps are retained.
- A student must be actively enrolled in the schedule's section before encoding. **Sprint 4 implementation.**
- Late threshold: **To validate** (recommended configuration per class/school policy).
- Editing cutoff and approval flow: **To validate**.
- School activity is excluded from absence counts unless policy says otherwise.

## SMS rules

- Guardian must be linked, verified, and have recorded SMS consent.
- Only one notification per event key to prevent duplicates.
- Attendance notification threshold: **To validate**.
- High-risk wording requires human review; do not send a sensitive label automatically.
- Store masked recipient, category, message, provider reference, status, retries, and errors.
- Scheduled meeting/home-visit messages include purpose, exact date/time, and school contact details.

## Early-warning rules

- Initial implementation will be transparent and rule-based; machine learning requires historical labeled outcomes.
- Proposed indicators: unexcused absences, consecutive absences, late frequency, attendance decline, academic decline, past unresolved interventions, and approved well-being indicators.
- Proposed baseline bands: 0-29 Low, 30-59 Moderate, 60-100 High. **To validate.**
- High results are queued for teacher/guidance review before intervention or parent messaging.
- The system must preserve score components in `indicators` so every result is explainable.

## Intervention workflow

For Review → Contacting Parent → Meeting Scheduled or Home Visit Scheduled → Under Intervention → For Follow-up → Resolved → Closed.

Each case retains student, reason, assigned personnel, schedule, findings, follow-up date, and timestamps.

## Non-functional requirements

- Role-based least-privilege access and object scoping
- Auditability of authentication and material record changes
- Server-side validation and CSRF protection
- Secrets supplied through environment variables
- Daily backup and tested restore procedure before production
- Philippine timezone (`Asia/Manila`)
- Privacy notice, consent basis, retention schedule, and breach procedure before pilot deployment

## Sprint acceptance criteria

- Project starts with documented commands.
- Login redirects anonymous users and authenticated users see a dashboard shell.
- Initial models migrate from a clean database.
- PostgreSQL configuration is available; SQLite enables immediate development.
- Database constraints and model validation cover core attendance invariants.
- Requirements, roles, policies needing validation, architecture, and ERD are documented.
- Django checks and automated tests pass.
