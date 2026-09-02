# Architecture Decisions

## Django domain backend with React admin interface

The domain remains a modular Django monolith. It keeps transactions, permissions, reporting, and deployment simple while allowing each domain to remain separated. The imported Berry React template is now the operator interface, connected to the canonical Django models through a small authenticated REST API. Django Admin and the server-rendered foundation remain available for administration and fallback access.

```text
React browser UI (localhost:3000)
  -> token-authenticated Django REST endpoints (localhost:8000/api)
      -> accounts / students / academics / attendance
      -> notifications / interventions / risk / reports / audit
          -> PostgreSQL (production) or SQLite (local development)

Django Admin/templates
  -> same canonical Django models and database
```

Future integrations stay behind service boundaries:

- SMS provider calls belong in `notifications` background jobs.
- Explainable scoring and later model inference belong in `risk_assessment`.
- PDF/Excel rendering belongs in `reports`.
- Celery/Redis is introduced with asynchronous SMS, not before it is needed.

## Security decisions

- A custom user model exists before the first migration so roles can evolve safely.
- React never uses the generic API starter database; all authentication and dashboard metrics come from the canonical TardyTrack backend.
- Domain records use protective deletion where history must remain auditable.
- Environment variables carry deployment secrets and PostgreSQL credentials.
- Risk indicators are structured JSON for explainability, while access control is enforced in application views in Sprint 2.
- SQLite is a developer convenience only; PostgreSQL is the target database for pilot and production.
