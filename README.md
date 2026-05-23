<div align="center">

# 🏢 Multi-Tenant SaaS Project Management API

**A production-grade, multi-tenant backend built with Django & DRF**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Django](https://img.shields.io/badge/Django-5.0-092E20?style=for-the-badge&logo=django&logoColor=white)](https://djangoproject.com)
[![DRF](https://img.shields.io/badge/DRF-3.15-ff1709?style=for-the-badge&logo=django&logoColor=white)](https://django-rest-framework.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io)
[![Celery](https://img.shields.io/badge/Celery-5.3-37814A?style=for-the-badge&logo=celery&logoColor=white)](https://celeryproject.org)
[![JWT](https://img.shields.io/badge/JWT-Auth-000000?style=for-the-badge&logo=jsonwebtokens&logoColor=white)](https://jwt.io)

---

_Multiple companies. One platform. Zero data overlap._

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Database Schema](#-database-schema)
- [Project Structure](#-project-structure)
- [Quick Start](#-quick-start)
- [API Reference](#-api-reference)
- [Role & Permission Matrix](#-role--permission-matrix)
- [Background Jobs](#-background-jobs--celery)
- [Security](#-security)
- [Configuration](#-configuration)
- [Testing](#-testing)
- [Example Credentials](#-example-credentials)

---

## 🌟 Overview

This platform enables multiple organizations (tenants) to use a single backend system while keeping their data **completely isolated and secure**. Companies can register independently, manage their own teams, projects, and tasks — with no possibility of cross-tenant data leakage.

### ✅ All Requirements Implemented

| Requirement                       | Status | Details                                                |
| --------------------------------- | ------ | ------------------------------------------------------ |
| Multi-tenant company registration | ✅     | Each company gets its own isolated workspace           |
| Role-Based Access Control         | ✅     | Admin / Manager / Employee with enforced permissions   |
| JWT Authentication + Refresh      | ✅     | Access + refresh tokens with blacklist on logout       |
| Project & Task CRUD               | ✅     | Full CRUD with assignment, status, filtering           |
| Tenant Data Isolation             | ✅     | Row-level isolation — verified cross-tenant 404s       |
| Audit Logging                     | ✅     | Every write action logged with user, action, timestamp |
| API Rate Limiting                 | ✅     | 60/min anonymous, 300/min authenticated                |
| Soft Delete + Restore             | ✅     | All business entities support soft delete & recovery   |
| Background Jobs (Celery)          | ✅     | Email notifications + daily summaries via Redis        |
| Real Email Notifications          | ✅     | Gmail SMTP — task assignment & member added            |

---

## 🚀 Features

```
 AUTHENTICATION          MULTI-TENANCY          BACKGROUND JOBS
 ─────────────          ─────────────          ───────────────
  JWT access tokens      Row-level isolation    Task assignment emails
  Rotating refresh       UUID primary keys      Member added alerts
  Token blacklist        TenantMixin auto-      Daily summary digest
  RBAC (3 roles)         scoping on all         Async audit logging
  Soft-delete users      queries                Celery + Redis queue

 PROJECTS & TASKS        AUDIT SYSTEM           QUALITY
 ────────────────        ────────────           ───────
  Full CRUD APIs         Immutable log trail    Pagination (all lists)
  Member management      Login/logout tracked   Consistent error format
  Status machine         Every write logged     Compound DB indexes
  Advanced filtering     Admin-only access      django-filter support
  Soft delete + restore  Async via Celery       Search on title/name
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       Client (Postman / Frontend)                       │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │  HTTPS + JWT Bearer Token
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Django REST Framework                            │
│                                                                         │
│  ┌───────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────┐   │
│  │  Auth / JWT   │  │   Projects   │  │    Tasks     │  │  Audit    │   │
│  │  /auth/*      │  │  /projects/* │  │  /tasks/*    │  │  /audit-  │   │
│  │  /users/*     │  │  ViewSet     │  │  ViewSet     │  │  logs/*   │   │
│  └───────┬───────┘  └──────┬───────┘  └──────┬───────┘  └─────┬─────┘   │
│          │                 │                 │                 │        │
│          └─────────────────┴────────┬────────┴─────────────────┘        │
│                                     │                                   │
│                          ┌──────────▼──────────┐                        │
│                          │    TenantMixin      │                        │
│                          │  .filter(company=   │                        │
│                          │   request.user.     │                        │
│                          │     company)        │                        │
│                          └──────────┬──────────┘                        │
│                                     │                                   │
│  ┌──────────────────────────────────▼──────────────────────────────┐    │
│  │                  PostgreSQL 16 (Row-level Isolation)            │    │
│  │       companies │ users │ projects │ tasks │ audit_logs         │    │
│  │         Every table has a company FK — no cross-tenant reads    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                   Redis + Celery (Async Layer)                  │    │
│  │  ┌─────────────────────┐    ┌──────────────────────────────┐    │    │
│  │  │   Task Queue (Redis)│    │     Celery Workers           │    │    │
│  │  │  create_audit_log   │───▶│  notify_task_assigned        │    │    │
│  │  │  notify_task_assign │    │  notify_project_member_added │    │    │
│  │  │  notify_proj_member │    │  send_daily_summary_emails   │    │    │
│  │  │  daily_summary      │    │  create_audit_log_async      │    │    │
│  │  └─────────────────────┘    └──────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

### Multi-Tenancy Design

**Row-level isolation** — every model carries a `company` foreign key. The `TenantMixin` automatically injects `.filter(company=request.user.company)` on every viewset queryset — no manual filtering required per view.

Isolation is enforced at **two independent layers**:

| Layer    | Mechanism                             | Effect                               |
| -------- | ------------------------------------- | ------------------------------------ |
| Database | FK constraints on every table         | Data integrity guaranteed            |
| API      | `TenantMixin` + serializer validation | Cross-tenant reads/writes return 404 |

> A user from Company A gets a **404** (not 403) when accessing Company B's resources — the resource simply doesn't exist in their scope.

---

## 🗄️ Database Schema

```
┌─────────────────────────────────────────────────────────────────────┐
│                           COMPANY                                   │
│  id (UUID PK) | name | slug | domain | is_active | created_at       │
└──────────┬──────────────────────────────────────────────────────────┘
           │ 1:N
    ┌──────┴─────────────────────┐
    │                            │
┌───▼─────────────────┐   ┌──────▼───────────────────────────────┐
│        USER         │   │               PROJECT                │
│ id (UUID)           │   │ id (UUID)                            │
│ company (FK)        │   │ company (FK)                         │
│ email (unique)      │   │ owner (FK → User)                    │
│ role (admin|mgr|emp)│   │ name | status | start_date | end_date│
│ is_deleted          │   │ members (M2M via ProjectMember)      │
│ is_active           │   └──────┬───────────────────────────────┘
└───────┬─────────────┘          │ 1:N
        │                 ┌──────▼─────────────────────────────────┐
        │                 │                TASK                    │
        │                 │ id (UUID)                              │
        └─────────────────│ company (FK) ← denormalized for perf   │
                          │ project (FK)                           │
                          │ assigned_to (FK → User)                │
                          │ created_by (FK → User)                 │
                          │ status | priority | due_date           │
                          │ is_deleted                             │
                          └────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│                          AUDIT LOG                                 │
│  id (UUID) | company (FK) | user | user_email | action             │
│  resource_type | resource_id | ip_address | timestamp              │
│  (Immutable — no soft delete, no updates)                          │
└────────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

| Decision                           | Reason                                                              |
| ---------------------------------- | ------------------------------------------------------------------- |
| **UUID primary keys**              | No sequential ID leakage across tenants                             |
| **Soft delete everywhere**         | Data recovery; `is_deleted` + `deleted_at` on all business entities |
| **Immutable AuditLog**             | Audit trails must not be editable or deletable                      |
| **Denormalized `company` on Task** | Fast filtering without joins through Project                        |
| **Compound DB indexes**            | `(company, status)`, `(company, assigned_to)`, `(project, status)`  |
| **Row-level isolation**            | Simpler than schema-per-tenant; works with Django ORM natively      |

---

## 📁 Project Structure

```
saas-projct-management-bootcamp/
│
├── config/
│   ├── settings/
│   │   └── base.py          # All settings — env-driven via django-environ
│   ├── celery.py            # Celery app + beat schedule (daily at 08:00 UTC)
│   └── urls.py              # Root URL configuration
│
├── core/
│   ├── models.py            # SoftDeleteModel, BaseModel (UUID PK), TimeStampedModel
│   ├── mixins.py            # TenantMixin, AuditLogMixin, get_client_ip
│   ├── pagination.py        # StandardPagination — count, total_pages, next/prev
│   └── exceptions.py        # Custom handler → {success, status_code, errors}
│
├── apps/
│   ├── companies/           # Company (tenant) — register, profile, update
│   ├── accounts/            # Custom User, JWT views, RBAC permissions
│   │   ├── models.py        # User with role field + soft delete
│   │   ├── permissions.py   # IsCompanyAdmin, IsManagerOrAdmin, IsSameTenant
│   │   ├── serializers.py   # CompanyRegistrationSerializer, JWT custom claims
│   │   └── views.py         # Register, Login (audit-logged), Logout, Me, Users CRUD
│   ├── projects/            # Project CRUD + member management
│   │   ├── tasks.py         # notify_project_member_added (Celery)
│   │   └── views.py         # ProjectViewSet with members sub-resource
│   ├── tasks/               # Task CRUD + status machine
│   │   ├── filters.py       # TaskFilter — status, priority, project, assigned_to, dates
│   │   └── tasks.py         # notify_task_assigned (Celery, max 3 retries)
│   └── audit/               # Immutable audit trail
│       ├── tasks.py         # create_audit_log_async, send_daily_summary_emails
│       └── views.py         # AuditLogListView — admin-only, filterable
│
├── docker-compose.yml       # PostgreSQL 16 (port 5437) + Redis 7 (port 6379)
├── Makefile                 # make up | migrate | run | celery-worker | celery-beat
├── requirements.txt
├── .env.example
└── postman_collection.json  # Ready-to-import API collection
```

---

## ⚡ Quick Start

### Prerequisites

- **Python 3.12+**
- **Docker & Docker Compose** (for PostgreSQL + Redis)

### 1. Clone & Set Up Environment

```bash
git clone <your-repo-url>
cd saas-projct-management-bootcamp

# Copy and configure environment
cp .env.example .env
# Edit .env — fill in SECRET_KEY and email credentials
```

### 2. Start Infrastructure

```bash
make up
# Starts PostgreSQL on port 5437 and Redis on port 6379
```

### 3. Install Dependencies & Migrate

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
make install
make migrate
```

### 4. Start All Services

Open **three terminals**:

```bash
# Terminal 1 — Django API server
make run

# Terminal 2 — Celery worker (emails + audit logs)
make celery-worker

# Terminal 3 — Celery Beat (scheduled tasks)
make celery-beat
```

### 5. Register Your First Company

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

---

## 📡 API Reference

**Base URL:** `http://localhost:8000/api/v1/`  
**Auth Header:** `Authorization: Bearer <access_token>`

All list responses use standard pagination:

```json
{
  "count": 42,
  "total_pages": 3,
  "current_page": 1,
  "next": "http://...",
  "previous": null,
  "results": [...]
}
```

All error responses follow a consistent format:

```json
{
  "success": false,
  "status_code": 400,
  "errors": { "field": ["message"] }
}
```

---

### 🔐 Authentication

| Method      | Endpoint                 | Access | Description                                   |
| ----------- | ------------------------ | ------ | --------------------------------------------- |
| `POST`      | `/auth/register/`        | Public | Register new company + admin account          |
| `POST`      | `/auth/login/`           | Public | Login, receive access + refresh tokens        |
| `POST`      | `/auth/logout/`          | Auth   | Blacklist refresh token (invalidates session) |
| `POST`      | `/auth/refresh/`         | Public | Get new access token via refresh token        |
| `GET/PATCH` | `/auth/me/`              | Auth   | View or update own profile                    |
| `POST`      | `/auth/change-password/` | Auth   | Change own password                           |

**Register request:**

```json
{
  "company_name": "Acme Corp",
  "first_name": "Alice",
  "last_name": "Smith",
  "email": "alice@acme.com",
  "password": "SecurePass123!",
  "confirm_password": "SecurePass123!"
}
```

**Login response:**

```json
{
  "access": "<jwt_access_token>",
  "refresh": "<jwt_refresh_token>",
  "user": {
    "id": "uuid",
    "email": "alice@acme.com",
    "role": "admin",
    "company_id": "uuid",
    "full_name": "Alice Smith"
  }
}
```

---

### 👥 Users

> Admin: full CRUD | Manager: list + read | Employee: no access

| Method   | Endpoint               | Description                          |
| -------- | ---------------------- | ------------------------------------ |
| `GET`    | `/users/`              | List all company users               |
| `POST`   | `/users/`              | Create new user (admin only)         |
| `GET`    | `/users/{id}/`         | User detail                          |
| `PATCH`  | `/users/{id}/`         | Update user (admin only)             |
| `DELETE` | `/users/{id}/`         | Soft delete user (admin only)        |
| `POST`   | `/users/{id}/restore/` | Restore deleted user (admin only)    |
| `GET`    | `/users/deleted/`      | List soft-deleted users (admin only) |

---

### 🏢 Company

| Method  | Endpoint    | Description                         |
| ------- | ----------- | ----------------------------------- |
| `GET`   | `/company/` | View own company profile            |
| `PATCH` | `/company/` | Update company details (admin only) |

---

### 📂 Projects

> Admin/Manager: full access | Employee: read-only (assigned projects)

| Method   | Endpoint                            | Description                                  |
| -------- | ----------------------------------- | -------------------------------------------- |
| `GET`    | `/projects/`                        | List projects (employees see only their own) |
| `POST`   | `/projects/`                        | Create project                               |
| `GET`    | `/projects/{id}/`                   | Project detail with members                  |
| `PATCH`  | `/projects/{id}/`                   | Update project                               |
| `DELETE` | `/projects/{id}/`                   | Soft delete project                          |
| `POST`   | `/projects/{id}/restore/`           | Restore deleted project                      |
| `GET`    | `/projects/deleted/`                | List deleted projects                        |
| `GET`    | `/projects/{id}/members/`           | List project members                         |
| `POST`   | `/projects/{id}/members/`           | Add member (triggers email)                  |
| `DELETE` | `/projects/{id}/members/{user_id}/` | Remove member                                |

**Create project request:**

```json
{
  "name": "Website Redesign",
  "description": "Q3 redesign initiative",
  "owner": "<user_uuid>",
  "member_ids": ["<uuid1>", "<uuid2>"]
}
```

---

### ✅ Tasks

> Admin/Manager: full CRUD | Employee: read assigned, update own status

| Method   | Endpoint               | Description                             |
| -------- | ---------------------- | --------------------------------------- |
| `GET`    | `/tasks/`              | List tasks                              |
| `POST`   | `/tasks/`              | Create task (triggers assignment email) |
| `GET`    | `/tasks/{id}/`         | Task detail                             |
| `PATCH`  | `/tasks/{id}/`         | Update task                             |
| `DELETE` | `/tasks/{id}/`         | Soft delete task                        |
| `POST`   | `/tasks/{id}/restore/` | Restore deleted task                    |
| `PATCH`  | `/tasks/{id}/status/`  | Update status (assignee can do this)    |

**Query Parameters (all optional):**

| Parameter         | Example                       | Description               |
| ----------------- | ----------------------------- | ------------------------- |
| `status`          | `?status=in_progress`         | Filter by status          |
| `priority`        | `?priority=high`              | Filter by priority        |
| `project`         | `?project=<uuid>`             | Filter by project         |
| `assigned_to`     | `?assigned_to=<uuid>`         | Filter by assignee        |
| `due_date_before` | `?due_date_before=2026-12-31` | Due date range            |
| `due_date_after`  | `?due_date_after=2026-01-01`  | Due date range            |
| `search`          | `?search=homepage`            | Full-text search on title |

**Status choices:** `pending` · `in_progress` · `in_review` · `completed` · `cancelled`  
**Priority choices:** `low` · `medium` · `high` · `critical`

---

### 📋 Audit Logs

> Admin only — read-only

| Method | Endpoint       | Description                          |
| ------ | -------------- | ------------------------------------ |
| `GET`  | `/audit-logs/` | List all audit logs for your company |

**Query Parameters:**

| Parameter         | Example                       |
| ----------------- | ----------------------------- |
| `action`          | `?action=create`              |
| `resource_type`   | `?resource_type=task`         |
| `user_email`      | `?user_email=alice@acme.com`  |
| `timestamp_after` | `?timestamp_after=2026-01-01` |

**Sample audit log entry:**

```json
{
  "id": "uuid",
  "user_email": "alice@acme.com",
  "action": "create",
  "resource_type": "project",
  "resource_id": "uuid",
  "resource_repr": "Website Redesign [active]",
  "ip_address": "127.0.0.1",
  "timestamp": "2026-05-23T14:00:00Z"
}
```

---

## 🔑 Role & Permission Matrix

| Action                   | Employee | Manager | Admin |
| ------------------------ | :------: | :-----: | :---: |
| Register company         |    ✅    |   ✅    |  ✅   |
| View own profile         |    ✅    |   ✅    |  ✅   |
| View assigned tasks      |    ✅    |   ✅    |  ✅   |
| Update own task status   |    ✅    |   ✅    |  ✅   |
| View assigned projects   |    ✅    |   ✅    |  ✅   |
| List users (own company) |    ❌    |   ✅    |  ✅   |
| Create / edit tasks      |    ❌    |   ✅    |  ✅   |
| Delete tasks             |    ❌    |   ✅    |  ✅   |
| Create / edit projects   |    ❌    |   ✅    |  ✅   |
| Manage project members   |    ❌    |   ✅    |  ✅   |
| Create users             |    ❌    |   ❌    |  ✅   |
| Delete / restore users   |    ❌    |   ❌    |  ✅   |
| Update company profile   |    ❌    |   ❌    |  ✅   |
| View audit logs          |    ❌    |   ❌    |  ✅   |

---

## ⚙️ Background Jobs & Celery

The platform uses **Celery + Redis** for all asynchronous work. No request is ever slowed down by email sending or log writing.

| Task                          | Trigger                                    | Recipient          | Description                          |
| ----------------------------- | ------------------------------------------ | ------------------ | ------------------------------------ |
| `notify_task_assigned`        | Task created/reassigned with `assigned_to` | Assignee's email   | "You have been assigned: Task Title" |
| `notify_project_member_added` | Member added to project                    | New member's email | "You've been added to: Project Name" |
| `create_audit_log_async`      | Every write operation                      | —                  | Async audit log DB write             |
| `send_daily_summary_emails`   | **Daily at 08:00 UTC**                     | Company admins     | Last 24h activity digest             |

**Retry policy:** `notify_task_assigned` and `notify_project_member_added` retry up to **3 times** with a 60-second delay on failure.

**Celery Beat schedule:**

```python
CELERY_BEAT_SCHEDULE = {
    "send-daily-summary-emails": {
        "task": "apps.audit.tasks.send_daily_summary_emails",
        "schedule": crontab(hour=8, minute=0),  # 08:00 UTC every day
    }
}
```

---

## 🔒 Security

| Feature                 | Implementation                                                                       |
| ----------------------- | ------------------------------------------------------------------------------------ |
| **JWT Authentication**  | Access tokens (60 min) + refresh tokens (7 days)                                     |
| **Token Rotation**      | Each `/auth/refresh/` issues a new refresh token and blacklists the old              |
| **Logout Invalidation** | Refresh token blacklisted on logout — session is fully terminated                    |
| **Tenant Isolation**    | `TenantMixin` on every viewset; cross-tenant = 404 (not 403)                         |
| **RBAC**                | Permissions enforced per action via `get_permissions()`                              |
| **Rate Limiting**       | 60 req/min anonymous · 300 req/min authenticated                                     |
| **Soft Delete**         | Deleted users become `is_active=False` — existing JWT tokens stop working            |
| **Audit Trail**         | Immutable — no update/delete endpoints on `AuditLog`                                 |
| **Custom Claims**       | JWT embeds `role`, `company_id`, `email`, `full_name` — no extra DB call per request |

---

## ⚙️ Configuration

Copy `.env.example` to `.env` and set the following:

```bash
# Core
SECRET_KEY=your-secret-key-here           # Generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
DEBUG=True

# Database (PostgreSQL)
DB_NAME=saas_project_management_db
DB_USER=postgres
DB_PASSWORD=yourpassword
DB_HOST=localhost
DB_PORT=5437

# Redis / Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Email (Gmail SMTP example)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=yourapp@gmail.com
EMAIL_HOST_PASSWORD=your-app-password      # Use Gmail App Password, not your account password
DEFAULT_FROM_EMAIL=Project Management <yourapp@gmail.com>

# JWT
JWT_ACCESS_TOKEN_LIFETIME_MINUTES=60
JWT_REFRESH_TOKEN_LIFETIME_DAYS=7

# Rate Limiting
RATE_LIMIT_ANON=60
RATE_LIMIT_USER=300
```

> **Gmail App Password**: Go to Google Account → Security → 2-Step Verification → App passwords.

---

## 🧪 Testing

### Run Automated API Verification (109 checks)

```bash
# Start the server first, then:
python verify.py
```

The verification script covers all 109 checks across:

- ✅ Company registration & management (5.1)
- ✅ User roles & permissions (5.2)
- ✅ Authentication flows (5.3)
- ✅ Projects & tasks CRUD (5.4)
- ✅ Multi-tenant data isolation (5.5)
- ✅ Audit logging (5.6)
- ✅ Rate limiting (8.1)
- ✅ Soft delete & restore (8.2)
- ✅ Celery background jobs (8.3)

### Postman Collection

Import `postman_collection.json` — it includes:

- Pre-request scripts that automatically capture and set JWT tokens
- All endpoints with example payloads
- Environment variables for `base_url`, `access_token`, `refresh_token`

---

## 🎯 Example Credentials

After starting the server, register two companies via the API:

**Company 1 — Acme Corp (Admin)**

```
Email:    alice@acme.com
Password: SecurePass123!
Role:     admin
```

**Company 2 — Beta Inc (Admin)**

```
Email:    bob@beta.com
Password: SecurePass123!
Role:     admin
```

**Cross-tenant isolation test:**

```bash
# Login as Alice (Acme)
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@acme.com","password":"SecurePass123!"}' | \
  python3 -c "import sys,json; print(json.load(sys.stdin)['access'])")

# Create a project under Acme
curl -s -X POST http://localhost:8000/api/v1/projects/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Acme Secret Project"}'

# Now login as Bob (Beta) and try to access Acme's project — returns 404
BOB_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"bob@beta.com","password":"SecurePass123!"}' | \
  python3 -c "import sys,json; print(json.load(sys.stdin)['access'])")

curl -s http://localhost:8000/api/v1/projects/ \
  -H "Authorization: Bearer $BOB_TOKEN"
# → {"count": 0, "results": []}  — Beta sees zero Acme projects ✅
```

---

## 📊 API Health Check

```bash
# Verify the server is running
curl http://localhost:8000/api/v1/auth/login/ \
  -X POST -H "Content-Type: application/json" \
  -d '{"email":"wrong","password":"wrong"}'
# → {"success": false, "status_code": 401, ...}
```

---

<div align="center">

**Built with ❤️ using Django, DRF, PostgreSQL, Redis & Celery**

_Multi-tenant · Secure · Scalable · Production-Ready_

</div>
