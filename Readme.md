# Task API

A CRUD REST API for managing a to-do list, built with **FastAPI** and backed by a **SQLite** database. Supports full Create, Read, Update, and Delete operations with interactive Swagger documentation, parameterized SQL queries, and data that persists across server restarts.

Built for the **FlyRank Internship — Backend Track**. Originally shipped in Week 2 (Assignment A1) as an in-memory API, then upgraded in Week 3 (Assignment A2) to a real, file-backed SQLite database — the same endpoints, but now production-realistic storage.

---

## Table of contents

- [Overview](#overview)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Getting started](#getting-started)
- [API reference](#api-reference)
- [Database design](#database-design)
- [Why SQLite](#why-sqlite)
- [Testing the API](#testing-the-api)
- [Exploring the database directly](#exploring-the-database-directly)
- [Proof of persistence](#proof-of-persistence)
- [Assignment 1 → Assignment 2: what changed](#assignment-1--assignment-2-what-changed)
- [Swagger UI](#swagger-ui)
- [Future improvements](#future-improvements)

---

## Overview

This API exposes five endpoints for managing tasks: listing all tasks, fetching a single task, creating a task, updating a task, and deleting a task. Every endpoint validates its input, returns proper HTTP status codes, and reads from / writes to a real SQLite database file (`tasks.db`) rather than a temporary in-memory data structure — meaning data survives a server crash or restart.

## Tech stack

| Layer | Choice |
|---|---|
| Language | Python 3.10+ |
| Web framework | FastAPI |
| Data validation | Pydantic |
| Database | SQLite (via Python's built-in `sqlite3` module) |
| Server | Uvicorn (ASGI) |
| API docs | Auto-generated Swagger UI (`/docs`) and ReDoc (`/redoc`) |

## Project structure
todo-api/
├── main.py # FastAPI app: routes, request/response models, validation
├── db.py # Database connection, table creation, and seeding logic
├── tasks.db # SQLite database file (auto-created, git-ignored)
├── requirements.txt # Python dependencies (optional, see below)
├── .gitignore
└── Readme.md

## Getting started

### Prerequisites
- Python 3.10 or later installed
- Git installed

### Installation

1. Clone the repository:
```bash
   git clone https://github.com/ZohaAshraf/todo-api.git
   cd todo-api
```

2. Create and activate a virtual environment:
```bash
   python -m venv venv

   # Windows
   venv\Scripts\activate

   # macOS / Linux
   source venv/bin/activate
```

3. Install dependencies:
```bash
   pip install fastapi uvicorn
```

4. Start the server:
```bash
   uvicorn main:app --port 8000
```

5. Open your browser to:
   - `http://localhost:8000/` — basic API info
   - `http://localhost:8000/docs` — interactive Swagger UI (recommended for manual testing)
   - `http://localhost:8000/redoc` — alternate API documentation view

On first run, `tasks.db` is created automatically along with a `tasks` table, seeded with 3 example tasks. Restarting the server does **not** duplicate the seed data or wipe out any tasks you've added — the seed logic only runs when the table is empty.

## API reference

| Method | Path | Description | Success | Errors |
|--------|------|--------------|---------|--------|
| `GET` | `/` | Basic API info | `200` | — |
| `GET` | `/health` | Health check | `200` | — |
| `GET` | `/tasks` | List all tasks | `200` | — |
| `GET` | `/tasks/{id}` | Get one task by id | `200` | `404` if id doesn't exist |
| `POST` | `/tasks` | Create a new task | `201` | `400` if title is missing/empty |
| `PUT` | `/tasks/{id}` | Update a task's title and done status | `200` | `400` invalid body, `404` unknown id |
| `DELETE` | `/tasks/{id}` | Delete a task | `204` | `404` if id doesn't exist |

### Request/response shape

**Task object:**
```json
{
  "id": 1,
  "title": "Buy milk",
  "done": false
}
```

**Create a task**
```bash
curl -i -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"Buy milk\"}"
```
```
HTTP/1.1 201 Created
content-type: application/json

{"id":4,"title":"Buy milk","done":false}
```

**Update a task**
```bash
curl -i -X PUT http://localhost:8000/tasks/1 \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"Buy milk and eggs\",\"done\":true}"
```
```
HTTP/1.1 200 OK
content-type: application/json

{"id":1,"title":"Buy milk and eggs","done":1}
```

**Delete a task**
```bash
curl -i -X DELETE http://localhost:8000/tasks/1
```
```
HTTP/1.1 204 No Content
```

**Error response (unknown id)**
```bash
curl -i http://localhost:8000/tasks/999
```
```
HTTP/1.1 404 Not Found
content-type: application/json

{"detail":"Task 999 not found"}
```

## Database design

**Table: `tasks`**

| Column | Type | Constraints |
|---|---|---|
| `id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` — assigned automatically by SQLite |
| `title` | `TEXT` | `NOT NULL` |
| `done` | `INTEGER` | `NOT NULL DEFAULT 0` — stored as `0` (false) or `1` (true) |

The table and database file are created automatically on startup if they don't already exist (`CREATE TABLE IF NOT EXISTS`), and 3 example tasks are seeded only when the table is empty — checked with `SELECT COUNT(*) FROM tasks` before inserting.

**Security — parameterized queries:** every query that includes user-supplied input uses `?` placeholders (e.g. `SELECT * FROM tasks WHERE id = ?`) with values passed separately, rather than being interpolated directly into the SQL string. This prevents SQL injection — the classic vulnerability where malicious input could otherwise be interpreted as part of the SQL command itself.

## Why SQLite

SQLite was chosen for this project because:
- **Zero setup** — it's a single file on disk, with no separate database server to install, configure, or run.
- **Portability** — the entire database is one `.db` file, easy to inspect, back up, or share.
- **Right-sized for this project** — a small task API doesn't need the concurrency or scale of Postgres/MySQL; SQLite handles this workload comfortably.
- **Built into Python** — no external dependency needed for the database driver itself.

The trade-off: SQLite isn't ideal for high-concurrency, multi-writer production systems — a larger application would likely graduate to Postgres, but the API layer wouldn't need to change, since the storage layer is decoupled from the routes (see below).

## Testing the API

All endpoints were manually tested via `curl` and the Swagger `/docs` "Try it out" interface, covering:
- Successful list, get, create, update, and delete operations
- `404` responses for non-existent task ids
- `400` responses for empty/missing titles
- Full persistence verification: created, updated, and deleted tasks were confirmed to survive multiple server restarts

## Exploring the database directly

Opened `tasks.db` in **DB Browser for SQLite** and ran queries directly against the live database file, confirming the API and DB Browser share the exact same source of truth with no syncing step required.

```sql
SELECT COUNT(*) FROM tasks;
```
Result: `3` — matched exactly what `GET /tasks` returned through the API at the same moment.

Screenshot of the database open in DB Browser:

<img width="1570" height="989" alt="DB Browser screenshot" src="https://github.com/user-attachments/assets/44d84b6b-5ddc-4250-877b-668edd69bf5c" />

## Proof of persistence

1. Created a new task via `POST /tasks`.
2. Restarted the server (`Ctrl+C`, then `uvicorn main:app --port 8000` again).
3. Called `GET /tasks` — the created task was still present.
4. Updated a task's title/done status and deleted another task, restarted the server again, and confirmed both changes held.

This directly resolves the limitation documented in Assignment 1 (see below): previously, any data created during a session was lost the moment the server restarted.

## Assignment 1 → Assignment 2: what changed

Assignment 1 stored tasks in a Python list held in memory — meaning all data (including anything created during testing) was lost every time the server restarted. Assignment 2 replaces that storage layer with SQLite, while keeping every route, request shape, and response shape identical. Specifically:

- Tasks now live in `tasks.db` instead of an in-memory Python list.
- The database file and its `tasks` table are created automatically on first run.
- The 3 example tasks are seeded once, only when the table is empty.
- `id` values are now auto-assigned by SQLite (`AUTOINCREMENT`) rather than calculated manually in Python.
- All read/write operations use parameterized SQL queries instead of in-memory list operations.
- No endpoint URL, request body shape, response body shape, or status code changed — proving that storage is an implementation detail the API's consumers never need to know about.

## Swagger UI

Screenshot of `/docs` from Assignment 1, showing the full CRUD cycle tested via "Try it out":

<img width="934" height="439" alt="Swagger UI - list and create" src="https://github.com/user-attachments/assets/7cec6926-9ecc-4966-ac1c-a5dd2b960c77" />
<img width="937" height="446" alt="Swagger UI - update and delete" src="https://github.com/user-attachments/assets/825d5737-0279-4c75-ae48-b32ee8e3e4a6" />
<img width="941" height="444" alt="Swagger UI - error handling" src="https://github.com/user-attachments/assets/1983233e-352d-4fb4-abc1-1d7b3f1a1c33" />

## Future improvements

- Add search (`?search=`), filtering (`?done=`), and sorting query parameters using SQL `LIKE`, `WHERE`, and `ORDER BY`
- Add a `/stats` endpoint computed with `SELECT COUNT(*)` in SQL
- Add `created_at` / `updated_at` timestamp columns
- Wrap multi-step writes (like the initial seed) in an explicit transaction for atomicity
- Add an index on frequently filtered/searched columns
- Migrate to an async database driver (e.g. `aiosqlite`) for non-blocking I/O under load