import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from db import init_db, get_db_connection
from llm.schema import EnrichRequest, EnrichResponse, Category, QualityFlag

load_dotenv()

app = FastAPI(
    title="Task API",
    version="1.0",
    description="A small CRUD API for managing a to-do list."
)


init_db()


class TaskCreate(BaseModel):
    title: str = ""


class TaskUpdate(BaseModel):
    title: str = ""
    done: bool = False


@app.get("/", summary="API info")
def root():
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks", "/enrich"]
    }


@app.get("/health", summary="Health check")
def health():
    return {"status": "ok"}


@app.post("/enrich", response_model=EnrichResponse, summary="Enrich a scraped book record")
def enrich_book(book: EnrichRequest):
    if os.environ.get("LLM_STUB") == "1":
        # Fixed, schema-valid fake answer — proves the route, validation,
        # and response shape all work before a single model call is made.
        return EnrichResponse(
            category=Category.other,
            summary="Stub mode: no model was called for this response.",
            quality_flags=[QualityFlag.missing_description] if not book.description else [],
            confidence=0.0,
        )

    # Real model call arrives in Stage 2 — until then, calling this
    # endpoint without LLM_STUB=1 raises on purpose so it's obvious
    # the real path isn't built yet.
    raise HTTPException(status_code=501, detail="Real model call not implemented yet (Stage 2)")


@app.get("/tasks", summary="List all tasks")
def get_tasks():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM tasks").fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/tasks/{task_id}", summary="Get one task by id")
def get_task(task_id: int):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return dict(row)


@app.post("/tasks", status_code=201, summary="Create a new task")
def create_task(new_task: TaskCreate):
    if not new_task.title.strip():
        raise HTTPException(status_code=400, detail="Title is required")

    conn = get_db_connection()
    cursor = conn.execute(
        "INSERT INTO tasks (title, done) VALUES (?, ?)",
        (new_task.title, 0)
    )
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {"id": new_id, "title": new_task.title, "done": False}


@app.put("/tasks/{task_id}", summary="Update a task")
def update_task(task_id: int, updated: TaskUpdate):
    if not updated.title.strip():
        raise HTTPException(status_code=400, detail="Title is required")

    conn = get_db_connection()
    cursor = conn.execute(
        "UPDATE tasks SET title = ?, done = ? WHERE id = ?",
        (updated.title, int(updated.done), task_id)
    )
    conn.commit()

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    return dict(row)


@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task")
def delete_task(task_id: int):
    conn = get_db_connection()
    cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")