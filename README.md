# SaaS Project Management Platform

A production-grade, multi-tenant project management backend built with Django and Django REST Framework.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client (Postman / Frontend)              │
└───────────────────────────────┬─────────────────────────────────┘
                                │ HTTPS + JWT Bearer Token
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Django REST Framework                        │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────┐  ┌────────┐  │
│  │  Auth /JWT  │  │  Projects    │  │  Tasks   │  │ Audit  │  │
│  │  accounts   │  │  ViewSet     │  │ ViewSet  │  │  Logs  │  │
│  └──────┬──────┘  └──────┬───────┘  └────┬─────┘  └───┬────┘  │
│         │                │               │             │        │
│         └────────────────┼───────────────┼─────────────┘        │
│                          │ TenantMixin   │ (filters by company) │
│                          ▼               ▼                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                 PostgreSQL (Row-level Isolation)          │   │
│  │   companies | users | projects | tasks | audit_logs      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Celery + Redis (Async Tasks)                 │   │
│  │   • Task assignment emails    • Project member alerts    │   │
│  │   • Audit log creation        • Daily summary emails     │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Multi-Tenancy Design

**Row-level isolation** — each table has a `company` foreign key. All queries are scoped by `TenantMixin` which injects `.filter(company=request.user.company)` on every viewset. No data from Company A is ever returned to Company B.

Isolation is enforced at two layers:
1. **Database level** — FK constraints ensure data integrity
2. **API level** — `TenantMixin` + serializer validation prevent cross-tenant reads or writes

## Database Schema

```
Company ──┬── User (role: admin | manager | employee)
          ├── Project ──── ProjectMember (through)
          │       └─────── Task
          └── AuditLog
```

### Key Design Decisions
- UUID primary keys (no sequential ID leakage)
- Soft delete on all business entities (`is_deleted`, `deleted_at`)
- Immutable `AuditLog` (no soft delete, no edit permissions in admin)
- Denormalized `company` FK on `Task` for fast filtering without joins
- Compound indexes on `(company, status)` and `(company, assigned_to)` for performance

## Project Structure

```
saas-projct-management-bootcamp/
├── config/
│   ├── settings/        # base.py + development.py
│   ├── celery.py        # Celery app + beat schedule
│   └── urls.py
├── core/
│   ├── models.py        # SoftDeleteModel, BaseModel, TimeStampedModel
│   ├── mixins.py        # TenantMixin, AuditLogMixin, SoftDeleteMixin
│   ├── pagination.py    # StandardPagination
│   └── exceptions.py    # Consistent JSON error format
├── apps/
│   ├── companies/       # Company (tenant) model
│   ├── accounts/        # Custom User, JWT auth, permissions, RBAC
│   ├── projects/        # Project + ProjectMember CRUD
│   ├── tasks/           # Task CRUD with status machine
│   └── audit/           # AuditLog (read-only, admin-only)
├── docker-compose.yml   # PostgreSQL 16 + Redis 7
├── Makefile
└── requirements.txt
```

## Setup Instructions

### Prerequisites
- Python 3.12+
- Docker & Docker Compose

### 1. Clone and create environment
```bash
git clone <repo>
cd saas-projct-management-bootcamp
cp .env.example .env
# Edit .env with your values (SECRET_KEY is required!)
```

### 2. Install dependencies
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
make install
```

### 3. Start infrastructure
```bash
make up          # Starts PostgreSQL (port 5437) and Redis (port 6379)
```

### 4. Run migrations
```bash
make migrate
```

### 5. Start the server
```bash
make run         # Django dev server on http://localhost:8000
```

### 6. Start Celery (separate terminal)
```bash
make celery-worker
```

### 7. Start Celery Beat for scheduled tasks (separate terminal)
```bash
make celery-beat
```

## API Documentation

Base URL: `http://localhost:8000/api/v1/`

All protected endpoints require: `Authorization: Bearer <access_token>`

### Authentication

| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| POST | `/auth/register/` | Public | Register company + admin account |
| POST | `/auth/login/` | Public | Login, get JWT tokens |
| POST | `/auth/logout/` | Auth | Blacklist refresh token |
| POST | `/auth/refresh/` | Public | Refresh access token |
| GET/PATCH | `/auth/me/` | Auth | View/update own profile |
| POST | `/auth/change-password/` | Auth | Change password |

### Users (Admin only)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/users/` | List company users |
| POST | `/users/` | Create user |
| GET | `/users/{id}/` | User detail |
| PATCH | `/users/{id}/` | Update user |
| DELETE | `/users/{id}/` | Soft delete user |
| POST | `/users/{id}/restore/` | Restore deleted user |
| GET | `/users/deleted/` | List deleted users |

### Projects (Manager/Admin: write; all: read own)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/projects/` | List projects |
| POST | `/projects/` | Create project |
| GET | `/projects/{id}/` | Project detail |
| PATCH | `/projects/{id}/` | Update project |
| DELETE | `/projects/{id}/` | Soft delete |
| POST | `/projects/{id}/restore/` | Restore project |
| GET | `/projects/{id}/members/` | List members |
| POST | `/projects/{id}/members/` | Add member |
| DELETE | `/projects/{id}/members/{user_id}/` | Remove member |

### Tasks (Manager/Admin: write; Employee: read assigned)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tasks/` | List tasks |
| POST | `/tasks/` | Create task |
| GET | `/tasks/{id}/` | Task detail |
| PATCH | `/tasks/{id}/` | Update task |
| DELETE | `/tasks/{id}/` | Soft delete |
| POST | `/tasks/{id}/restore/` | Restore task |
| PATCH | `/tasks/{id}/status/` | Update status (assignee allowed) |

**Filters:** `?status=pending&priority=high&project={id}&assigned_to={id}&due_date_before=2026-12-31`

**Search:** `?search=homepage`

### Audit Logs (Admin only)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/audit-logs/` | List company audit logs |

**Filters:** `?action=create&resource_type=task&user_email=alice@acme.com&timestamp_after=2026-01-01`

## Example API Requests

### Register a company
```bash
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Acme Corp",
    "first_name": "Alice",
    "last_name": "Smith",
    "email": "alice@acme.com",
    "password": "SecurePass123!",
    "confirm_password": "SecurePass123!"
  }'
```

### Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@acme.com", "password": "SecurePass123!"}'
```

### Create a project
```bash
curl -X POST http://localhost:8000/api/v1/projects/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Website Redesign", "status": "active"}'
```

## Example Credentials (for testing)

After running the server, register via the API:
- **Admin:** `alice@acme.com` / `SecurePass123!` (Acme Corp)
- **Second tenant:** `bob@beta.com` / `SecurePass123!` (Beta Inc)

## Role-Based Access Control

| Action | Employee | Manager | Admin |
|--------|----------|---------|-------|
| View own tasks | ✅ | ✅ | ✅ |
| Update own task status | ✅ | ✅ | ✅ |
| Create/edit tasks | ❌ | ✅ | ✅ |
| Delete tasks | ❌ | ✅ | ✅ |
| Create/edit projects | ❌ | ✅ | ✅ |
| Manage users | ❌ | ❌ | ✅ |
| View audit logs | ❌ | ❌ | ✅ |

## Security Features

- **JWT authentication** with token blacklist on logout
- **Rotating refresh tokens** (each refresh invalidates the previous)
- **Tenant isolation** enforced on every query
- **Role-based permissions** at the API level
- **Rate limiting**: 60 req/min (anon), 300 req/min (authenticated)
- **Soft delete** — data is never permanently lost
- **Immutable audit trail** for all write operations

## Background Jobs (Celery)

| Task | Trigger | Description |
|------|---------|-------------|
| `notify_task_assigned` | Task assigned/reassigned | Email notification to assignee |
| `notify_project_member_added` | Member added to project | Email notification |
| `create_audit_log_async` | Every write operation | Async audit log creation |
| `send_daily_summary_emails` | 08:00 UTC daily | Summary email to admins |
