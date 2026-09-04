# TardyTrack

TardyTrack is a student attendance and dropout early-warning system with an SMS-based intervention workflow roadmap.

## Sprint 1 delivered

- Django 5.2 project with modular apps
- Custom user model and five initial roles
- Academic, student, attendance, SMS, intervention, risk, and audit schema
- Initial migrations and Django admin integration
- Login and authenticated dashboard shell
- PostgreSQL configuration with SQLite local fallback
- Business rules, permissions, architecture, and ERD documentation
- Automated foundation and attendance-validation tests

## Sprint 2 delivered

- Administrator user-management interface and protected account APIs
- Five-role access model with role-filtered navigation and scoped dashboard metrics
- Temporary-password enforcement, self-service password changes, and token rotation
- Activation/deactivation, administrator password reset, and safety protections
- Account/login/logout audit events

## Sprint 3 delivered

- Academic setup for school years, grade levels, subjects, sections, advisers, and class schedules
- Student and guardian profiles linked to role-compatible login accounts
- Enrollment lifecycle and student-to-guardian assignment workflows
- Conflict detection for schedules and duplicate active enrollments
- Administrator React screens, protected APIs, validation, and audit records

## Sprint 4 delivered

- Role-scoped class schedules, rosters, and attendance history
- Bulk attendance encoding and safe correction of existing entries
- Active-enrollment, school-year, class-day, future-date, and excuse validation
- Atomic saves and audit events for attendance changes
- React attendance workspace for administrators, teachers, students, and guardians

## Sprint 5 delivered

- Monthly attendance, absence, and punctuality summaries
- Daily distribution and rolling six-month attendance trends
- Role-scoped schedule and student filters
- Per-student attendance-event monitoring without automated risk labels
- Dashboard attendance-rate cards and seven-day overview charts

## Sprint 6 delivered

- Consent- and verification-aware guardian SMS queue
- Duplicate prevention through unique event keys
- Masked recipients, provider references, delivery states, retries, and retained errors
- Administrator queue, send, retry, search, filtering, and delivery-monitoring workspace
- Optional unexcused-absence automation with safe cancellation after attendance corrections
- Safe local provider boundary ready for an approved production SMS adapter

## Sprint 7 delivered

- Role-scoped intervention case register for Administrators, Guidance Personnel, and Teachers
- Enforced case workflow, assigned ownership, scheduling, findings, and follow-up rules
- Parent-contact attempts with linked guardian, channel, outcome, and notes
- Meeting, home-visit, follow-up, and general case activity history
- Search, status summaries, case timelines, and auditable material changes

## Sprint 8 delivered

- Transparent attendance-based early-warning scoring under a versioned draft policy
- Explainable point components for absence, consecutive absence, lateness, attendance decline, and unresolved interventions
- Required Administrator or Guidance Personnel review with retained decisions and notes
- Teacher access limited to confirmed indicators for currently assigned students
- Idempotent draft recalculation and protection for reviewed historical results
- Risk summary, filtering, generation, review, and score-explanation interface

## Sprint 9 delivered

- Consent-aware, versioned well-being support check-ins
- Strict Administrator and Guidance Personnel access to responses and private notes
- Human-selected support priority and action-planning workflow
- Immutable submitted responses and closed records
- Sanitized list views and audit metadata that exclude raw answers and private notes
- Explicit separation of sensitive responses from automated risk scoring and messaging

## Sprint 10 delivered

- Attendance, intervention and confirmed-risk reports with date/student filters
- Paginated previews and complete printable reports with explicit size limits
- Administrator-only read-only audit viewer with date/action/actor filters
- Sensitive-field exclusions and report-generation audit events

## Run locally (CMD)

### One-command launcher

From the project directory, run:

```cmd
run-system
```

The launcher installs/builds the React interface when needed, applies pending migrations, then serves the interface and API through one Django process. Open only `http://localhost:3000/`. Press `Ctrl+C` to stop it.

### Manual startup

```cmd
cd /d C:\xampp\htdocs\TARDYTRACK
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
cd react-ui
npm install --legacy-peer-deps
set NODE_OPTIONS=--openssl-legacy-provider
npm run build
cd ..
python manage.py runserver 127.0.0.1:3000
```

Open `http://localhost:3000/`. The React interface and Django API use the same origin. SQLite is used when `POSTGRES_DB` is not set.

### Template dependency note

The imported Berry template uses a legacy React 17 / Material UI beta dependency set. It builds successfully, but `npm audit` reports known transitive-package vulnerabilities. Treat the current UI as a development baseline and schedule a controlled dependency modernization before any public production deployment; do not run `npm audit fix --force` without a tested migration because it introduces breaking changes.

## Documentation

- [Sprint 10 reports and audit logs](docs/SPRINT_10_REPORTS_AND_AUDIT.md)

- [Sprint 1 requirements](docs/SPRINT_1_REQUIREMENTS.md)
- [Database design and ERD](docs/DATABASE_DESIGN.md)
- [Architecture decisions](docs/ARCHITECTURE.md)
- [Sprint 2 accounts and permissions](docs/SPRINT_2_ACCOUNTS_AND_PERMISSIONS.md)
- [Sprint 3 academic and student master data](docs/SPRINT_3_MASTER_DATA.md)
- [Sprint 4 attendance encoding](docs/SPRINT_4_ATTENDANCE.md)
- [Sprint 5 attendance summaries and dashboards](docs/SPRINT_5_ATTENDANCE_ANALYTICS.md)
- [Sprint 6 SMS notifications](docs/SPRINT_6_SMS_NOTIFICATIONS.md)
- [Sprint 7 interventions and home visits](docs/SPRINT_7_INTERVENTIONS.md)
- [Sprint 8 explainable risk assessment](docs/SPRINT_8_RISK_ASSESSMENT.md)
- [Sprint 9 restricted well-being check-ins](docs/SPRINT_9_WELL_BEING_CHECKINS.md)

## Verify

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
```
