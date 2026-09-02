# Architecture Decisions

## Modular Django monolith

Sprint 1 uses a modular Django monolith. It keeps transactions, permissions, reporting, and deployment simple while allowing each domain to remain separated. Django Templates serve the initial UI; an API or HTMX can be added when a verified use case requires it.

```text
Browser
  -> Django views/templates
      -> accounts / students / academics / attendance
      -> notifications / interventions / risk / reports / audit
          -> PostgreSQL (production) or SQLite (local development)
```

Future integrations stay behind service boundaries:

- SMS provider calls belong in `notifications` background jobs.
- Explainable scoring and later model inference belong in `risk_assessment`.
- PDF/Excel rendering belongs in `reports`.
- Celery/Redis is introduced with asynchronous SMS, not before it is needed.

## Security decisions

- A custom user model exists before the first migration so roles can evolve safely.
- Domain records use protective deletion where history must remain auditable.
- Environment variables carry deployment secrets and PostgreSQL credentials.
- Risk indicators are structured JSON for explainability, while access control is enforced in application views in Sprint 2.
- SQLite is a developer convenience only; PostgreSQL is the target database for pilot and production.
