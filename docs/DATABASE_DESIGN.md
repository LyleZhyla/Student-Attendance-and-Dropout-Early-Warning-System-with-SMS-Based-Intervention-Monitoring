# Database Design

The initial schema deliberately includes downstream entities so relationships and deletion behavior are stable before feature sprints. Fields may expand as school policy is validated.

```mermaid
erDiagram
    USER ||--o| STUDENT : owns_profile
    USER ||--o| GUARDIAN : owns_profile
    USER ||--o{ SECTION : advises
    USER ||--o{ CLASS_SCHEDULE : teaches
    SCHOOL_YEAR ||--o{ SECTION : contains
    GRADE_LEVEL ||--o{ SECTION : groups
    SECTION ||--o{ ENROLLMENT : accepts
    STUDENT ||--o{ ENROLLMENT : has
    STUDENT }o--o{ GUARDIAN : linked_via_student_guardian
    SECTION ||--o{ CLASS_SCHEDULE : schedules
    SUBJECT ||--o{ CLASS_SCHEDULE : defines
    STUDENT ||--o{ ATTENDANCE_RECORD : receives
    CLASS_SCHEDULE ||--o{ ATTENDANCE_RECORD : records
    STUDENT ||--o{ RISK_ASSESSMENT : evaluated
    STUDENT ||--o{ INTERVENTION_CASE : supported
    STUDENT ||--o{ SMS_LOG : concerns
    GUARDIAN ||--o{ SMS_LOG : receives
    USER ||--o{ AUDIT_LOG : performs
```

## Key constraints

- Usernames and learner reference numbers are unique.
- A section name is unique within grade level and school year.
- Enrollment is unique per student and section.
- Guardian linking is unique per student/guardian pair.
- Attendance is unique per student/class schedule/date.
- SMS event keys are unique to make repeat processing idempotent.
- Risk assessment is unique per student/day.

## Retention and deletion

Operational records use `PROTECT` for students, users, and schedules referenced by history. User/profile links that are optional use `SET_NULL`. Hard deletion policies are not enabled until the school approves retention and anonymization rules.
