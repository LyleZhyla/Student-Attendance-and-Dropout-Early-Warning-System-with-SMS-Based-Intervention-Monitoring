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

## Run locally (PowerShell)

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver
```

Open `http://127.0.0.1:8000/`. SQLite is used when `POSTGRES_DB` is not set. To use PostgreSQL, copy `.env.example` values into the process environment before starting Django.

## Documentation

- [Sprint 1 requirements](docs/SPRINT_1_REQUIREMENTS.md)
- [Database design and ERD](docs/DATABASE_DESIGN.md)
- [Architecture decisions](docs/ARCHITECTURE.md)

## Verify

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
```
