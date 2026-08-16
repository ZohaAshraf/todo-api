import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from db import init_db, get_db_connection
from llm.schema import EnrichRequest, EnrichResponse, Category, QualityFlag
from llm.client import call_model_for_enrichment, call_model_for_repair
from llm.parse_and_validate import parse_and_validate, write_quarantine_entry
from llm.cost_log import log_call

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


PROMPT_VERSION = "enrich-v1"


@app.post("/enrich", response_model=EnrichResponse, summary="Enrich a scraped book record")
def enrich_book(book: EnrichRequest):
    if os.environ.get("LLM_STUB") == "1":
        # Stage 1: fixed, schema-valid fake answer. Proves the route,
        # input validation, and response shape all work correctly
        # before a single real model call is ever made.
        return EnrichResponse(
            category=Category.other,
            summary="Stub mode: no model was called for this response.",
            quality_flags=[QualityFlag.missing_description] if not book.description else [],
            confidence=0.0,
        )

    if os.environ.get("LLM_ENABLED", "true").lower() == "false":
        # Stage 4 kill switch: turn the model off without a deploy. Every
        # production AI feature needs one of these — the day the provider
        # has an outage, or the bill spikes, someone needs to be able to
        # flip this off immediately.
        return EnrichResponse(
            category=Category.other,
            summary="LLM enrichment is currently disabled; no model was called.",
            quality_flags=[],
            confidence=0.0,
        )

    if os.environ.get("LLM_FORCE_BROKEN") == "1":
        # Deterministic test hook — proves the repair/quarantine path
        # without depending on a live model actually failing, and without
        # spending any real API quota. No model call happens here at all.
        raw_output = '{"book_category": "fiction", "summary": "x", "quality_flags": [], "confidence": 0.5}'
        usage_info = {"input_tokens": 0, "output_tokens": 0, "duration_ms": 0.0}
    else:
        raw_output, usage_info = call_model_for_enrichment(
            title=book.title,
            description=book.description,
            price_gbp=book.price_gbp,
        )
    log_call(PROMPT_VERSION, os.environ.get("LLM_MODEL", "unknown"), usage_info, was_repair=False)

    validated, error = parse_and_validate(raw_output)
    if validated is not None:
        return validated

    # First attempt failed — one repair retry, handing the model its own
    # broken output plus the exact error, and nothing more.
    if os.environ.get("LLM_FORCE_BROKEN") == "1":
        repaired_output = '{"book_category": "fiction", "summary": "still wrong", "quality_flags": [], "confidence": 0.5}'
        repair_usage_info = {"input_tokens": 0, "output_tokens": 0, "duration_ms": 0.0}
    else:
        repaired_output, repair_usage_info = call_model_for_repair(
            title=book.title,
            description=book.description,
            price_gbp=book.price_gbp,
            broken_output=raw_output,
            validation_error=error,
        )
    log_call(PROMPT_VERSION, os.environ.get("LLM_MODEL", "unknown"), repair_usage_info, was_repair=True)

    validated, repair_error = parse_and_validate(repaired_output)
    if validated is not None:
        return validated

    # Still failed after one repair — give up cleanly. Never crash, never
    # return raw model text, never guess a default and pretend it worked.
    write_quarantine_entry(
        input_data=book.model_dump(),
        prompt_version=PROMPT_VERSION,
        error=repair_error,
        raw_output=repaired_output,
    )
    raise HTTPException(
        status_code=422,
        detail=f"Model could not produce a valid response after one repair attempt: {repair_error}",
    )


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