# TardyTrack

TardyTrack is a student attendance and dropout early-warning system with a planned SMS-based intervention workflow. Sprint 1 establishes the approved requirements, database design, and a runnable Django foundation.

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

## Run locally (CMD)

```cmd
cd /d C:\xampp\htdocs\TARDYTRACK
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

In a second CMD window, run the React interface:

```cmd
cd /d C:\xampp\htdocs\TARDYTRACK\react-ui
npm install --legacy-peer-deps
set NODE_OPTIONS=--openssl-legacy-provider
npm start
```

Open `http://localhost:3000/`. Django runs at `http://127.0.0.1:8000/` and remains the canonical backend. SQLite is used when `POSTGRES_DB` is not set.

The imported `api-server-django/` directory belongs to the original UI starter and is retained locally as reference only. It is Git-ignored: do not run or publish it for TardyTrack because it has a separate generic user model that is not connected to the approved schema.

### Template dependency note

The imported Berry template uses a legacy React 17 / Material UI beta dependency set. It builds successfully, but `npm audit` reports known transitive-package vulnerabilities. Treat the current UI as a development baseline and schedule a controlled dependency modernization before any public production deployment; do not run `npm audit fix --force` without a tested migration because it introduces breaking changes.

## Documentation

- [Sprint 1 requirements](docs/SPRINT_1_REQUIREMENTS.md)
- [Database design and ERD](docs/DATABASE_DESIGN.md)
- [Architecture decisions](docs/ARCHITECTURE.md)
- [Sprint 2 accounts and permissions](docs/SPRINT_2_ACCOUNTS_AND_PERMISSIONS.md)

## Verify

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
```
