# Sprint 5 — Attendance Summaries and Dashboards

Status: implemented.

## Delivered workflows

- Monthly attendance summary with attendance, absence, and punctuality rates
- Daily status-distribution chart for the selected month
- Rolling six-month attendance-rate trend
- Per-student monitoring table ordered by unexcused absence, total absence, and late events
- Filters for month, authorized class schedule, and authorized student
- Role-aware dashboard cards and a seven-day attendance overview
- Dedicated React analytics workspace for Administrators, Teachers, Students, and Parents/Guardians

## Role scope

- Administrators see school-wide attendance data and all schedule/student filters.
- Teachers see only records, schedules, and students connected to their assigned classes.
- Students see only their own attendance analytics.
- Parents/Guardians see only students linked to their guardian profile.
- Guidance Personnel do not receive attendance-detail access in this sprint; their restricted risk and intervention views remain scheduled for later sprints.

## Calculation rules

- **Recorded sessions** exclude `Not Recorded` entries.
- **Attended sessions** include Present, Late, and School Activity.
- **Attendance rate** is attended sessions divided by recorded sessions.
- **Absences** combine Excused and Unexcused Absence. School Activity is not counted as absence.
- **Punctuality rate** is Present divided by Present plus Late.
- Months without recorded sessions return a zero rate rather than an undefined value.

The student monitoring table summarizes attendance events only. It does not assign risk, diagnose a student, or trigger discipline. Risk scoring and human review remain separate roadmap work.
