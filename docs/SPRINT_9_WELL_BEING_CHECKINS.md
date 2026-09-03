# Sprint 9 — Restricted Well-being Check-ins

Status: implemented.

## Delivered workflows

- Restricted well-being check-in register for Administrators and Guidance Personnel
- Explicit student consent or assent confirmation and retained privacy-notice version
- Fixed, versioned draft support questionnaire with validated response values
- Human-selected Routine, Prompt, or Urgent support priority
- Open, Action Planned, and Closed follow-up workflow
- Required action plan for urgent priority and Action Planned status
- Required private closure notes before a check-in can be closed
- Immutable submitted student, date, consent, privacy notice, questionnaire version, and responses
- Summary lists that exclude raw responses and private notes
- Restricted detail view for submitted answers, private guidance notes, and actions
- Sanitized audit events that do not copy raw answers or private notes
- Dashboard count of open restricted check-ins for authorized roles

## Access and privacy rules

- Only Administrators and Guidance Personnel can create, list, open, or update check-ins.
- Teachers, Students, and Parents/Guardians receive no API or navigation access to these records.
- Collection responses expose operational metadata only. Raw responses and private notes require the restricted detail endpoint.
- Audit metadata contains the student identifier, date, workflow status, and questionnaire version. It does not duplicate answers, notes, or the human-selected priority.
- Submitted answers are immutable. If an entry is materially incorrect, staff should close it with an appropriate restricted note and create a correctly dated record under the approved data-correction procedure.
- Closed records are immutable.

## Draft questionnaire

Questionnaire version: `support-check-in-v1-draft`

The check-in asks only whether:

- circumstances are affecting regular attendance;
- the student feels connected and supported at school;
- the student knows an adult at school they can approach;
- the student requests follow-up support; and
- the student chooses to discuss approved support topics.

Every sensitive choice includes or permits a “Prefer not to say” response. The questionnaire is a support-coordination aid, not a diagnostic or clinical screening instrument.

## Consent and workflow rules

- Consent or assent must be explicitly confirmed before responses can be stored.
- The current privacy notice version (`wellbeing-privacy-v1-draft`) must be recorded.
- Future-dated check-ins are rejected.
- Only one check-in per student and date is allowed.
- Support priority is selected by authorized staff and is never calculated from the answers.
- Urgent priority requires a documented human action plan.
- Action Planned requires recommended actions.
- Closing requires private closure notes and retains reviewer identity and time.

## Separation from automated risk scoring

Sprint 9 responses, support priorities, notes, and actions do **not** add points to or otherwise modify the Sprint 8 automated score. This prevents sensitive self-reported information from becoming an opaque automated label. Authorized staff may consider a check-in during human support planning, but any action remains a human decision.

The system does not automatically create interventions, notify guardians, or send SMS messages from well-being answers.

## Deployment decisions still required

- Approval of the questionnaire and privacy notice by school leadership, guidance personnel, and the research adviser
- Legal basis, age-appropriate consent/assent wording, guardian involvement policy, and withdrawal procedure
- Record retention, correction, export, and secure deletion procedures
- Immediate-safety escalation protocol and trained personnel coverage
- Encryption, backup access, breach response, and production audit-log review procedures
