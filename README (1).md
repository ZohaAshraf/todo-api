# Task API

A small CRUD API for managing a to-do list, built with **FastAPI**. Supports creating, reading, updating, and deleting tasks, with interactive Swagger docs. Data is stored in memory (it resets when the server restarts).

Built for FlyRank Internship — Backend Track, Week 2, Assignment A1.

## How to run it

1. Clone this repo and open a terminal inside the project folder.
2. Create and activate a virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate        # Windows
   source venv/bin/activate     # Mac/Linux
   ```
3. Install dependencies:
   ```
   pip install fastapi uvicorn
   ```
4. Start the server:
   ```
   uvicorn main:app --port 8000
   ```
5. Open your browser to `http://localhost:8000/` to see it running, or `http://localhost:8000/docs` for the interactive Swagger UI.

## Endpoints

| Method | Path             | Description                     | Success code | Error codes |
|--------|------------------|----------------------------------|---------------|-------------|
| GET    | `/`              | API info                         | 200           | -           |
| GET    | `/health`        | Health check                     | 200           | -           |
| GET    | `/tasks`         | List all tasks                   | 200           | -           |
| GET    | `/tasks/{id}`    | Get one task by id                | 200           | 404         |
| POST   | `/tasks`         | Create a new task                 | 201           | 400         |
| PUT    | `/tasks/{id}`    | Update a task's title/done        | 200           | 400, 404    |
| DELETE | `/tasks/{id}`    | Delete a task                     | 204           | 404         |

## Example request

```
curl -i -X POST http://localhost:8000/tasks -H "Content-Type: application/json" -d "{\"title\":\"Buy milk\"}"
```

```
HTTP/1.1 201 Created
content-type: application/json

{"id":4,"title":"Buy milk","done":false}
```

## Swagger UI

Screenshot of `/docs` showing the full CRUD cycle tested via "Try it out":

![Swagger UI screenshot](swagger-screenshot.png)

## The mortality experiment

Tasks are stored in memory — if the server restarts, all tasks (including any created during testing) are lost and reset back to the original 3 example tasks. This is expected: a real database (coming next week) is what would make the data persist.
