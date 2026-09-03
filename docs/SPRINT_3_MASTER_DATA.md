# Sprint 3 — Academic and Student Master Data

Status: implemented.

## Delivered workflows

- Administrator management of school years, grade levels, subjects, sections, advisers, and class schedules
- Exactly one active school year at a time
- Schedule validation for time ranges and overlapping section or teacher assignments
- Student profiles with optional Student-role login links
- Guardian profiles with optional Parent/Guardian-role login links and explicit SMS consent
- Student-to-guardian links with one primary guardian per student
- Section enrollment lifecycle: Enrolled, Transferred, Completed, and Dropped
- Prevention of multiple active section enrollments in the same school year
- Searchable, responsive React tables and create/edit dialogs
- Audit logging for every master-data creation and update

## Access and safety rules

- All Sprint 3 endpoints require an authenticated Administrator account.
- Section advisers and schedule assignees must be active Teacher accounts.
- Student profiles can only be connected to active Student accounts.
- Guardian profiles can only be connected to active Parent/Guardian accounts.
- Existing records are updated or deactivated; destructive deletion is intentionally unavailable so references remain auditable.
- SMS consent is recorded but Sprint 3 does not send messages.

## Deferred items

- CSV import/export and bulk promotion are candidates for a later administration sprint.
- Attendance encoding against active enrollments is delivered in Sprint 4.
- Mobile-number verification is delivered with the SMS integration workflow.
