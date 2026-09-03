# Sprint 7 — Interventions and Home Visits

Status: implemented.

## Delivered workflows

- Intervention case register with student, reason, assigned owner, status, schedule, findings, and follow-up date
- Enforced workflow from For Review through parent contact, meeting/home visit, intervention, follow-up, resolution, and closure
- Case ownership for active Administrators, Teachers, and Guidance Personnel
- Parent-contact attempts with linked guardian, contact channel, outcome, and notes
- Case notes, meetings, home visits, and follow-up activity records
- Immutable status-change history generated when a case changes stage
- Search, status filtering, operational summary cards, and complete case timelines
- Audit events for case creation, updates, and activity entries
- Django Admin support for cases and their activity history

## Role scope

- **Administrators** can view, create, assign, and update every intervention case.
- **Guidance Personnel** can view and manage every intervention case.
- **Teachers** can create cases only for students in their assigned classes. New teacher-created cases are assigned to that teacher.
- Teachers can view cases involving their assigned students but can update or add activities only when they own the case.
- Students and Parents/Guardians do not receive access to staff intervention notes in Sprint 7.

## Workflow rules

The supported forward workflow is:

```text
For Review
  -> Contacting Parent
      -> Meeting Scheduled or Home Visit Scheduled
          -> Under Intervention
              -> For Follow-up
                  -> Resolved
                      -> Closed
```

Controlled return transitions support rescheduling and renewed intervention. Invalid stage jumps are rejected by the API.

- New cases always start as **For Review**.
- Meeting and home-visit stages require a future date and time.
- For Follow-up requires a current or future follow-up date.
- Resolved and Closed cases require findings.
- Parent-contact activities require a guardian linked to the case student, a channel, an outcome, and notes.
- Activities cannot be dated in the future.
- Closed cases cannot be reopened through the Sprint 7 workflow.

## Privacy and SMS boundaries

Intervention notes are restricted to authorized staff. Sprint 7 does not expose case findings to student or guardian accounts and does not automatically send sensitive case details.

Administrators may use the Sprint 6 SMS workspace for approved meeting or home-visit messages. Those messages should contain the purpose, exact date/time, and official school contact information and remain subject to guardian link, consent, and mobile-verification checks.

## Deferred decisions

- School-approved intervention categories, service-level targets, escalation timeframes, and closure authority
- Approved guardian-facing message templates and automatic scheduling notifications
- Attachment storage, signatures, and printable home-visit forms
- Fine-grained restrictions for especially sensitive guidance notes
