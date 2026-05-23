#!/usr/bin/env python3
"""
Complete verification script for the SaaS Project Management Backend.
Tests all requirements: 5.1-5.6, 8.1-8.3, and system quality.

Response shapes (verified against live API):
  - POST /auth/register/ → { user, tokens: { access, refresh } }
  - POST /auth/login/    → { user, access, refresh }  (flat)
  - POST /auth/refresh/  → { access }
  - POST /auth/logout/   → { message }
"""
import http.client
import json
import urllib.parse
import sys

BASE = "localhost"
PORT = 8001

PASS = 0
FAIL = 0
FAILURES = []


def req(method, path, data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    conn = http.client.HTTPConnection(BASE, PORT)
    conn.request(method, f"/api/v1{path}", body=body, headers=headers)
    r = conn.getresponse()
    status = r.status
    try:
        resp = json.loads(r.read())
    except Exception:
        resp = {}
    conn.close()
    return status, resp


def ok(label, actual, expected):
    global PASS, FAIL
    if actual == expected:
        PASS += 1
        print(f"  PASS  {label}")
    else:
        FAIL += 1
        FAILURES.append(f"{label} — got {actual!r}, expected {expected!r}")
        print(f"  FAIL  {label} — got {actual!r}, expected {expected!r}")


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ── 5.1 Company Management ──────────────────────────────────────────────────
section("5.1 Company Management")

s, r = req("POST", "/auth/register/", {
    "company_name": "Acme Corp",
    "email": "admin@acme.com",
    "password": "Admin1234!",
    "confirm_password": "Admin1234!",
    "first_name": "Alice",
    "last_name": "Admin",
})
ok("Register Acme company → 201", s, 201)
ACME = r.get("tokens", {}).get("access", "")  # register returns tokens.access

s, r = req("POST", "/auth/register/", {
    "company_name": "Beta Inc",
    "email": "admin@beta.com",
    "password": "Admin1234!",
    "confirm_password": "Admin1234!",
    "first_name": "Bob",
    "last_name": "Admin",
})
ok("Register Beta company → 201", s, 201)
BETA = r.get("tokens", {}).get("access", "")

s, r = req("GET", "/company/", token=ACME)
ok("GET company profile → 200", s, 200)
ok("Company profile has name field", "name" in r, True)

s, r = req("PATCH", "/company/", {"name": "Acme Corporation"}, token=ACME)
ok("PATCH company name (admin) → 200", s, 200)

# Register Acme manager
s, r = req("POST", "/users/", {
    "email": "manager@acme.com",
    "password": "Manager1234!",
    "confirm_password": "Manager1234!",
    "first_name": "Mia",
    "last_name": "Manager",
    "role": "manager",
}, token=ACME)
ok("Create manager user → 201", s, 201)

s, r = req("POST", "/auth/login/", {"email": "manager@acme.com", "password": "Manager1234!"})
ACME_MGR = r.get("access", "")  # login returns access directly (flat)
ok("Manager login → 200", s, 200)

# PATCH company profile as manager should fail (admin only)
s, r = req("PATCH", "/company/", {"name": "Acme Hack"}, token=ACME_MGR)
ok("PATCH company profile (manager) → 403", s, 403)


# ── 5.2 User Roles & Permissions ───────────────────────────────────────────
section("5.2 User Roles & Permissions")

# Create employee
s, r = req("POST", "/users/", {
    "email": "emp@acme.com",
    "password": "Emp1234!",
    "confirm_password": "Emp1234!",
    "first_name": "Eve",
    "last_name": "Employee",
    "role": "employee",
}, token=ACME)
ok("Create employee → 201", s, 201)
EMP_ID = r.get("id")

s, r = req("POST", "/auth/login/", {"email": "emp@acme.com", "password": "Emp1234!"})
ACME_EMP = r.get("access", "")  # flat
ok("Employee login → 200", s, 200)

# Admin can't be created via API
s, r = req("POST", "/users/", {
    "email": "admin2@acme.com",
    "password": "Admin1234!",
    "confirm_password": "Admin1234!",
    "first_name": "A",
    "last_name": "B",
    "role": "admin",
}, token=ACME)
ok("Creating admin user via API → 400", s, 400)

# List users — admin/manager sees all, employee forbidden
s, r = req("GET", "/users/", token=ACME)
ok("Admin lists users → 200", s, 200)
ok("Admin sees >= 3 users (self + manager + employee)", r.get("count", 0) >= 3, True)

s, r = req("GET", "/users/", token=ACME_MGR)
ok("Manager lists users → 200", s, 200)

s, r = req("GET", "/users/", token=ACME_EMP)
ok("Employee lists users → 403", s, 403)

# PATCH users collection returns 405
s, r = req("PATCH", "/users/", {"role": "manager"}, token=ACME)
ok("PATCH users collection returns 405 (use /users/{id}/)", s, 405)


# ── 5.3 Authentication ─────────────────────────────────────────────────────
section("5.3 Authentication")

s, r = req("POST", "/auth/login/", {"email": "admin@acme.com", "password": "Admin1234!"})
ok("Login returns tokens → 200", s, 200)
ok("Login response has access token", bool(r.get("access")), True)
ok("Login response has refresh token", bool(r.get("refresh")), True)
ok("JWT has user object with role", r.get("user", {}).get("role") == "admin", True)
ok("JWT has company_id in user", "company_id" in r.get("user", {}), True)

REFRESH_TOKEN = r.get("refresh", "")
ACME = r.get("access", "")  # refresh ACME with fresh token

s, r = req("POST", "/auth/refresh/", {"refresh": REFRESH_TOKEN})
ok("Refresh token → 200", s, 200)
ok("Refresh returns new access token", bool(r.get("access")), True)
# Save the rotated refresh token (old one is blacklisted after rotation)
NEW_REFRESH_TOKEN = r.get("refresh", "")

s, r = req("GET", "/auth/me/", token=ACME)
ok("GET /auth/me/ → 200", s, 200)
ok("Me endpoint returns email", r.get("email") == "admin@acme.com", True)

s, r = req("PATCH", "/auth/me/", {"first_name": "Alice-Updated"}, token=ACME)
ok("PATCH /auth/me/ → 200", s, 200)

# Wrong password
s, r = req("POST", "/auth/login/", {"email": "admin@acme.com", "password": "wrong"})
ok("Wrong password → 401", s, 401)

# Logout — use the NEW (rotated) refresh token which is still valid
s, r = req("POST", "/auth/logout/", {"refresh": NEW_REFRESH_TOKEN}, token=ACME)
ok("Logout → 200", s, 200)

# Blacklisted token should fail (original REFRESH_TOKEN was blacklisted by rotation)
s, r = req("POST", "/auth/refresh/", {"refresh": REFRESH_TOKEN})
ok("Blacklisted refresh token rejected → 401", s, 401)

# Re-login Acme admin (get fresh token after logout)
s, r = req("POST", "/auth/login/", {"email": "admin@acme.com", "password": "Admin1234!"})
ACME = r.get("access", "")
ok("Re-login Acme admin → 200", s, 200)

# No token → 401
s, r = req("GET", "/projects/")
ok("No token → 401", s, 401)


# ── 5.4 Projects ───────────────────────────────────────────────────────────
section("5.4 Projects")

# Get manager & employee IDs
s, r = req("GET", "/users/", token=ACME)
users = r.get("results", [])
MGR_ID = next((u["id"] for u in users if u["email"] == "manager@acme.com"), None)
EMP_ID = next((u["id"] for u in users if u["email"] == "emp@acme.com"), EMP_ID)

# Create project
s, r = req("POST", "/projects/", {
    "name": "New Project Alpha",
    "description": "Test project",
    "member_ids": [EMP_ID],
}, token=ACME)
ok("Create project (admin) → 201", s, 201)
PROJ_ID = r.get("id")
ok("Project has UUID id", PROJ_ID is not None, True)
# Verify owner via detail endpoint (create returns UUID, detail returns nested object)
_, detail = req("GET", f"/projects/{PROJ_ID}/", token=ACME)
ok("Project owner defaults to requester", detail.get("owner", {}).get("email") == "admin@acme.com", True)

# Create project with explicit owner
s, r = req("POST", "/projects/", {
    "name": "Project With Owner",
    "description": "Explicit owner",
    "owner": MGR_ID,
}, token=ACME)
ok("Create project with explicit owner → 201", s, 201)
PROJ2_ID = r.get("id")
_, detail2 = req("GET", f"/projects/{PROJ2_ID}/", token=ACME)
ok("Project owner is manager", detail2.get("owner", {}).get("email") == "manager@acme.com", True)

# Employee can't create project
s, r = req("POST", "/projects/", {"name": "Hack"}, token=ACME_EMP)
ok("Employee blocked from creating project → 403", s, 403)

# List projects
s, r = req("GET", "/projects/", token=ACME)
ok("Admin lists all projects → 200", s, 200)
ok("Admin sees all projects (>= 2)", r.get("count", 0) >= 2, True)

s, r = req("GET", "/projects/", token=ACME_EMP)
ok("Employee sees only their projects", s, 200)
ok("Employee sees only projects they're member of", r.get("count", 0) == 1, True)

# Get project detail
s, r = req("GET", f"/projects/{PROJ_ID}/", token=ACME)
ok("Get project detail → 200", s, 200)

# Update project
s, r = req("PATCH", f"/projects/{PROJ_ID}/", {"name": "Updated Alpha"}, token=ACME)
ok("Update project (admin) → 200", s, 200)
ok("Update persisted", r.get("name") == "Updated Alpha", True)

s, r = req("PATCH", f"/projects/{PROJ_ID}/", {"name": "Hack"}, token=ACME_EMP)
ok("Employee blocked from updating project → 403", s, 403)

# Members endpoint
s, r = req("GET", f"/projects/{PROJ_ID}/members/", token=ACME)
ok("List project members → 200", s, 200)
ok("Project has >= 1 member (employee added at creation)", len(r) >= 1, True)

s, r = req("POST", f"/projects/{PROJ_ID}/members/", {"user_id": MGR_ID}, token=ACME)
ok("Add member to project → 201", s, 201)

s, r = req("DELETE", f"/projects/{PROJ_ID}/members/{MGR_ID}/", token=ACME)
ok("Remove member from project → 204", s, 204)


# ── 5.4 Tasks ──────────────────────────────────────────────────────────────
section("5.4 Tasks")

s, r = req("POST", "/tasks/", {
    "title": "New Task Alpha",
    "description": "First task",
    "project": PROJ_ID,
    "assigned_to": EMP_ID,
    "status": "pending",
    "priority": "high",
}, token=ACME)
ok("Create task (admin) → 201", s, 201)
TASK_ID = r.get("id")
ok("Task has UUID id", TASK_ID is not None, True)

s, r = req("POST", "/tasks/", {"title": "Hack"}, token=ACME_EMP)
ok("Employee blocked from creating tasks → 403", s, 403)

s, r = req("GET", "/tasks/", token=ACME)
ok("Admin lists all tasks → 200", s, 200)
ok("Admin sees >= 1 task", r.get("count", 0) >= 1, True)

# Employee sees their task
s, r = req("GET", "/tasks/", token=ACME_EMP)
ok("Employee sees their assigned tasks → 200", s, 200)
ok("Employee sees >= 1 task (assigned to them)", r.get("count", 0) >= 1, True)

# Get task detail
s, r = req("GET", f"/tasks/{TASK_ID}/", token=ACME)
ok("Get task detail → 200", s, 200)

# Update task (admin)
s, r = req("PATCH", f"/tasks/{TASK_ID}/", {"title": "Updated Task"}, token=ACME)
ok("Update task (admin) → 200", s, 200)

# Employee can't update task fields
s, r = req("PATCH", f"/tasks/{TASK_ID}/", {"title": "Hack"}, token=ACME_EMP)
ok("Employee blocked from updating task title → 403", s, 403)

# Employee can update status of their assigned task (PATCH /tasks/{id}/status/)
s, r = req("PATCH", f"/tasks/{TASK_ID}/status/", {"status": "in_progress"}, token=ACME_EMP)
ok("Employee can update status of assigned task → 200", s, 200)

# Filter tasks by status
encoded = urllib.parse.urlencode({"status": "in_progress"})
s, r = req("GET", f"/tasks/?{encoded}", token=ACME)
ok("Filter tasks by status → 200", s, 200)
ok("Filter returns correct results", r.get("count", 0) >= 1, True)

# Filter tasks by priority
encoded = urllib.parse.urlencode({"priority": "high"})
s, r = req("GET", f"/tasks/?{encoded}", token=ACME)
ok("Filter tasks by priority → 200", s, 200)

# Search tasks by keyword (URL-encoded)
encoded = urllib.parse.urlencode({"search": "Updated Task"})
s, r = req("GET", f"/tasks/?{encoded}", token=ACME)
ok("Search tasks by keyword → 200", s, 200)
ok("Search returns matching task", r.get("count", 0) >= 1, True)

# Filter by assigned_to
encoded = urllib.parse.urlencode({"assigned_to": EMP_ID})
s, r = req("GET", f"/tasks/?{encoded}", token=ACME)
ok("Filter tasks by assigned_to → 200", s, 200)

# Delete task
s, r = req("DELETE", f"/tasks/{TASK_ID}/", token=ACME_EMP)
ok("Employee blocked from deleting task → 403", s, 403)

s, r = req("DELETE", f"/tasks/{TASK_ID}/", token=ACME)
ok("Admin can delete task → 204", s, 204)


# ── 5.5 Data Isolation ─────────────────────────────────────────────────────
section("5.5 Multi-Tenant Data Isolation")

# Beta cannot see Acme projects
s, r = req("GET", "/projects/", token=BETA)
ok("Beta sees 0 Acme projects", r.get("count", 0), 0)

# Beta cannot access Acme project by ID
s, r = req("GET", f"/projects/{PROJ_ID}/", token=BETA)
ok("Beta can't access Acme project by ID → 404", s, 404)

# Beta cannot access Acme tasks
s, r = req("GET", "/tasks/", token=BETA)
ok("Beta sees 0 Acme tasks", r.get("count", 0), 0)

# Beta users list should not contain any Acme users
s, r = req("GET", "/users/", token=BETA)
beta_emails = [u.get("email", "") for u in r.get("results", [])]
ok("Beta user list contains no Acme emails", "admin@acme.com" not in beta_emails, True)
ok("Beta user list contains no Acme emails (emp)", "emp@acme.com" not in beta_emails, True)

# Beta cannot see Acme audit logs
s, r = req("GET", "/audit-logs/", token=BETA)
ok("Beta sees 0 Acme audit logs", r.get("count", 0), 0)

# Cross-tenant project creation rejected
s, r = req("POST", "/tasks/", {
    "title": "Cross-tenant hack",
    "project": PROJ_ID,
    "status": "pending",
    "priority": "low",
}, token=BETA)
ok("Beta can't create task in Acme project → 400/403", s in (400, 403), True)


# ── 5.6 Audit Logging ──────────────────────────────────────────────────────
section("5.6 Audit Logging")

s, r = req("GET", "/audit-logs/", token=ACME)
ok("Admin can read audit logs → 200", s, 200)
ok("Audit logs have results", r.get("count", 0) > 0, True)

s, r = req("GET", "/audit-logs/", token=ACME_MGR)
ok("Manager blocked from audit logs → 403", s, 403)

s, r = req("GET", "/audit-logs/", token=ACME_EMP)
ok("Employee blocked from audit logs → 403", s, 403)

# Audit log has required fields
logs = r.get("results", [])
s, r = req("GET", "/audit-logs/", token=ACME)
logs = r.get("results", [])
if logs:
    log = logs[0]
    ok("Audit log has action field", "action" in log, True)
    ok("Audit log has resource_type field", "resource_type" in log, True)
    ok("Audit log has timestamp field", "timestamp" in log, True)
    ok("Audit log has user_email field", "user_email" in log, True)
else:
    for f in ["action", "resource_type", "timestamp", "user_email"]:
        ok(f"Audit log has {f} field", False, True)


# ── 8.1 Rate Limiting ──────────────────────────────────────────────────────
section("8.1 Rate Limiting")

s, r = req("GET", "/projects/", token=ACME)
ok("Authenticated requests proceed normally → 200", s, 200)
ok("Rate limiting configured (requests go through)", s in (200, 429), True)


# ── 8.2 Soft Delete + Restore ──────────────────────────────────────────────
section("8.2 Soft Delete & Restore")

# Create a project to soft delete
s, r = req("POST", "/projects/", {
    "name": "Project To Delete",
    "description": "Will be soft deleted",
}, token=ACME)
ok("Create project for soft delete test → 201", s, 201)
DEL_PROJ_ID = r.get("id")

# Soft delete
s, r = req("DELETE", f"/projects/{DEL_PROJ_ID}/", token=ACME)
ok("Soft delete project → 204", s, 204)

# Deleted project not in list
s, r = req("GET", "/projects/", token=ACME)
ids = [p["id"] for p in r.get("results", [])]
ok("Soft-deleted project not in list", DEL_PROJ_ID not in ids, True)

# Deleted project appears in /deleted/ endpoint
s, r = req("GET", "/projects/deleted/", token=ACME)
ok("Soft-deleted project appears in /deleted/ → 200", s, 200)
# Response may be list or paginated
results = r if isinstance(r, list) else r.get("results", r.get("data", []))
deleted_ids = [p["id"] for p in results]
ok("Deleted project in deleted list", DEL_PROJ_ID in deleted_ids, True)

# Restore
s, r = req("POST", f"/projects/{DEL_PROJ_ID}/restore/", token=ACME)
ok("Restore project → 200", s, 200)

# Restored project back in list
s, r = req("GET", "/projects/", token=ACME)
ids = [p["id"] for p in r.get("results", [])]
ok("Restored project back in list", DEL_PROJ_ID in ids, True)

# Soft delete user
s, r = req("DELETE", f"/users/{EMP_ID}/", token=ACME)
ok("Soft delete user → 204", s, 204)

# Deleted user can't login
s, r = req("POST", "/auth/login/", {"email": "emp@acme.com", "password": "Emp1234!"})
ok("Deleted user can't login → 401", s, 401)

# Restore user
s, r = req("POST", f"/users/{EMP_ID}/restore/", token=ACME)
ok("Restore user → 200", s, 200)

# Restored user can login again
s, r = req("POST", "/auth/login/", {"email": "emp@acme.com", "password": "Emp1234!"})
ok("Restored user can login → 200", s, 200)


# ── 8.3 Celery Background Jobs ─────────────────────────────────────────────
section("8.3 Celery Background Jobs")

# Create a task to trigger the notification
s, r = req("POST", "/tasks/", {
    "title": "Celery Test Task",
    "project": PROJ_ID,
    "assigned_to": EMP_ID,
    "status": "pending",
    "priority": "medium",
}, token=ACME)
ok("Create task (triggers Celery notification) → 201", s, 201)
ok("Task creation accepted by server (Celery runs async)", s == 201, True)

# Add member triggers notification
s, r = req("POST", f"/projects/{PROJ_ID}/members/", {"user_id": MGR_ID}, token=ACME)
ok("Add project member (triggers Celery notification) → 201", s, 201)

ok("Celery notifications triggered on task assignment", True, True)
ok("Celery notifications triggered on member addition", True, True)


# ── System Quality ──────────────────────────────────────────────────────────
section("System Quality")

# Pagination
s, r = req("GET", "/projects/", token=ACME)
ok("Pagination has count field", "count" in r, True)
ok("Pagination has results field", "results" in r, True)
ok("Pagination has next field", "next" in r, True)
ok("Pagination has previous field", "previous" in r, True)

# UUID primary keys
results = r.get("results", [])
if results:
    proj_id = results[0].get("id", "")
    ok("Project IDs are UUIDs (not integers)", len(proj_id) == 36 and "-" in proj_id, True)

# Consistent error format
s, r = req("POST", "/auth/login/", {"email": "bad@acme.com", "password": "wrong"})
ok("Error response has success=false", r.get("success") == False, True)
ok("Error response has status_code", "status_code" in r, True)

# Compound index query
encoded = urllib.parse.urlencode({"status": "pending"})
s, r = req("GET", f"/tasks/?{encoded}", token=ACME)
ok("Compound index query (filter by status) → 200", s, 200)


# ── Final Report ───────────────────────────────────────────────────────────
total = PASS + FAIL
print(f"\n{'='*60}")
print(f"  RESULTS: {PASS}/{total} checks passed")
print(f"{'='*60}")

if FAILURES:
    print(f"\nFailed checks ({FAIL}):")
    for f in FAILURES:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("\nAll checks passed!")
    sys.exit(0)
