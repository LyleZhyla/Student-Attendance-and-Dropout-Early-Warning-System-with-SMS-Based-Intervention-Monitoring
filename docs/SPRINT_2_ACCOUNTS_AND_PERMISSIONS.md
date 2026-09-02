# Sprint 2 — Accounts, Roles, and Permissions

Status: implemented.

## Delivered workflows

- Administrator-only user directory with search and role filtering
- Account creation with a temporary password and forced first-login password change
- Editing of names, username, email, and role
- Account activation and deactivation with immediate token revocation
- Administrator password reset with token revocation
- Self-service password change with password validation and token rotation
- Role-filtered React navigation
- Role-scoped dashboard metrics
- Audit records for account creation, updates, status changes, password events, login, and logout

## Permission matrix

| Capability | Admin | Teacher | Student | Parent | Guidance |
|---|---:|---:|---:|---:|---:|
| Manage user accounts | Yes | No | No | No | No |
| Change own password | Yes | Yes | Yes | Yes | Yes |
| View global dashboard totals | Yes | No | No | No | Limited |
| View assigned-student dashboard data | Yes | Yes | Own only | Linked children | Authorized monitoring |
| Encode attendance (planned Sprint 4 UI) | Yes | Yes | No | No | No |
| Review sensitive risk data (planned workflow) | Yes | No | No | No | Yes |

All restrictions are enforced by the Django API. Hiding a React menu item is a usability measure, not the security boundary.

## Safety rules

- An administrator cannot deactivate their own account.
- The last active administrator cannot be deactivated or reassigned.
- A non-superuser administrator cannot modify a Django superuser.
- Deactivation and administrator password reset revoke all current API tokens.
- New and reset passwords must pass Django password validation.
- Passwords and temporary passwords are never written to audit metadata.
- Account deletion is intentionally unavailable; deactivation preserves audit and historical references.

## Deferred items

- Email-based forgot-password delivery requires a validated school email provider and sender identity.
- Teacher-to-section and student-to-parent assignment interfaces are delivered with Sprint 3 master-data workflows; their database relationships already exist.
- Fine-grained sensitive-record viewing is completed with the corresponding risk and intervention sprints.
