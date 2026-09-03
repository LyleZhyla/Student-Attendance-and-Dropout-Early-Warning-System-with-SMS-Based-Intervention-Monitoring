# Sprint 8 — Explainable Risk Assessment

Status: implemented.

## Delivered workflows

- On-demand draft risk generation for one active student or the active student population
- Transparent attendance-based score with every component, observation, point value, cap, and explanation retained
- Current 30-day assessment window compared with the previous 30-day attendance period
- Low, Moderate, and High bands using the documented draft thresholds
- Pending, Confirmed, Dismissed, and Needs More Information review decisions
- Required human review by an Administrator or Guidance Personnel
- Reviewer identity, notes, decision, and timestamp retained with the assessment
- Teacher access limited to confirmed assessments for currently assigned students
- Search, level and review filters, summary cards, and an indicator explanation view
- Audit events for generation, recalculation, and human review
- Protection against overwriting an assessment after a human review

## Draft scoring policy

Policy version: `attendance-v1-draft`

| Component | Draft points | Maximum |
|---|---:|---:|
| Unexcused absences in current 30-day window | 8 per record | 40 |
| Consecutive unexcused-absence days | 5 per day after the first | 20 |
| Late records in current 30-day window | 3 per record | 15 |
| Attendance-rate decline versus previous 30 days | 1 per 2 percentage points | 15 |
| One or more unresolved interventions | 10 | 10 |

The total is capped at 100. Draft bands are:

- **Low:** 0–29
- **Moderate:** 30–59
- **High:** 60–100

These weights and bands remain subject to school and research-adviser validation. The policy version is saved on every assessment so future revisions do not obscure how an older score was produced.

## Attendance calculations

- Recorded sessions exclude `Not Recorded` entries.
- Present, Late, and School Activity count as attended.
- Attendance decline is measured only when the previous period contains recorded sessions.
- Consecutive absence points use distinct calendar dates, preventing multiple classes on one date from inflating the streak.
- Resolved and Closed intervention cases do not contribute unresolved-intervention points.

## Review and access rules

- Administrators and Guidance Personnel can generate and review assessments for active students.
- Teachers cannot generate or review risk assessments.
- Teachers see only **Confirmed** results for active students in their assigned classes.
- Students and Parents/Guardians do not receive access to risk records in Sprint 8.
- Pending assessments can be recalculated idempotently for the same student and date.
- Once reviewed, that student/date assessment cannot be overwritten. A later assessment date creates a new historical result.
- Dismissed and Needs More Information decisions require reviewer notes.

## Safety boundary

A score is an early-warning support indicator. It is not a diagnosis, proof that a student will drop out, or an automated disciplinary decision. Sprint 8 does not automatically create interventions, send guardian messages, or expose sensitive labels.

Restricted well-being assessment remains planned for Sprint 9 and must use separate permissions so raw responses are not exposed to Teachers, Students, Parents, or general reports.

## Deferred policy decisions

- Validation or revision of weights, caps, windows, and score bands using approved historical data
- Academic-performance inputs and approved handling of missing grades
- School-approved review cadence, escalation timelines, and assessment retention
- Fairness, false-positive, subgroup, and outcome validation before pilot use
