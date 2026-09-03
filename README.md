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

- [Sprint 1 requirements](docs/SPRINT_1_REQUIREMENTS.md)
- [Database design and ERD](docs/DATABASE_DESIGN.md)
- [Architecture decisions](docs/ARCHITECTURE.md)
- [Sprint 2 accounts and permissions](docs/SPRINT_2_ACCOUNTS_AND_PERMISSIONS.md)
- [Sprint 3 academic and student master data](docs/SPRINT_3_MASTER_DATA.md)

## Verify

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
```
