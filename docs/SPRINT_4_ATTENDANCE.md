# Sprint 4 — Attendance Encoding

Status: implemented.

## Delivered workflows

- Administrator access to every class schedule and Teacher access only to assigned schedules
- Date-specific rosters generated from active section enrollments
- Bulk attendance encoding for Present, Late, Excused Absence, Unexcused Absence, School Activity, and Not Recorded
- One-click “mark all present” flow with per-student status, time-in, and excuse-reason fields
- Safe correction through idempotent update of the unique student/schedule/date record
- Role-scoped attendance history for Administrators, Teachers, Students, and linked Parents/Guardians
- Status totals for the attendance history visible to the signed-in account
- Audit events containing the class, date, affected student IDs, and create/update counts

## Validation and access rules

- Future attendance is rejected.
- The selected date must fall inside the schedule's school year and match its configured weekday.
- A student must be active and actively enrolled in the schedule's section on the attendance date.
- Excused absence requires a reason.
- Duplicate students in one bulk request are rejected.
- Bulk writes are atomic: an invalid entry prevents every entry in that request from being saved.
- Teachers cannot view rosters or records for schedules assigned to another teacher.
- Students see only their profile; guardians see only linked students.

## Deferred policy decisions

- A school-approved late threshold remains required before automatically deriving Late from time-in.
- An editing cutoff and approval workflow remain required before restricting corrections.
- Sprint 5 will add monthly summaries, trends, and expanded role-specific monitoring.
