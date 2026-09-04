# Sprint 10 — Reports and Audit Logs

Status: implemented.

## Delivered

- Administrator and Guidance report workspace at `/reports`.
- Attendance record report, intervention register, and confirmed-risk assessment report.
- Inclusive date filters, optional student filter (including historical/inactive students), stable ordering and 50-row preview pages.
- Printable, escaped HTML with A4 landscape print styles, repeated table headings, report period, generation timestamp, author and record count. Open the printable report and use Ctrl+P to print or save as PDF.
- Full filtered report generation independent of preview pagination. Reports over 5,000 rows are rejected with instructions to narrow the filters; results are not silently truncated.
- Administrator-only read-only audit viewer, with date, exact action, actor ID and pagination filters.
- Audit events for printable report generation; merely viewing a preview does not create an export event.

## Scope and privacy

Teachers, Students and Parents cannot access these reporting APIs. Guidance Personnel cannot access the audit viewer. Server permissions enforce these rules independently of navigation.

Attendance dates filter attendance events; intervention dates filter case creation; risk dates filter assessment dates; audit dates use local event dates. Intervention status and owner are current at generation, not reconstructed historical values. Date ranges for reports are limited to 367 inclusive days.

Reports omit excuse reasons, case reasons/findings, activity notes, risk reviewer notes and indicator JSON, all well-being responses and private notes. Risk reports include only Confirmed assessments and do not constitute diagnoses.

Audit output exposes only timestamp, actor, action, object type and object ID. Arbitrary existing summaries, metadata and IP addresses are deliberately excluded because earlier modules may have written sensitive data there. Audit editing, deletion and bulk exports are not exposed.

Printed files contain identifiable student information. Keep them under approved school access and retention rules. No external report service is contacted. No new database migration is needed.

## Verification

Run `python manage.py test reports` for permission, filtering, pagination, complete-print, escaping, privacy and print-limit regression tests.

## Boundaries

This sprint supplies browser-printable reports, not a server-side PDF/Excel renderer. It does not add production encryption, immutable external audit storage, retention automation or a deployment security review. Those remain deployment requirements.
