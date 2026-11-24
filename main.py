"""AI Support Ticket Triage API (FastAPI + SQLite)."""
import os
import sqlite3
from contextlib import closing

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from triage import triage_message

DB_PATH = os.getenv("TICKETS_DB", "tickets.db")
app = FastAPI(title="Ticket Triage API")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with closing(get_conn()) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer TEXT NOT NULL,
                message TEXT NOT NULL,
                category TEXT, priority TEXT, summary TEXT,
                draft_reply TEXT, source TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        conn.commit()


init_db()


class TicketIn(BaseModel):
    customer: str = Field(min_length=1)
    message: str = Field(min_length=1)


@app.post("/tickets", status_code=201)
def create_ticket(ticket: TicketIn):
    result = triage_message(ticket.message)
    with closing(get_conn()) as conn:
        cur = conn.execute(
            """INSERT INTO tickets
               (customer, message, category, priority, summary, draft_reply, source)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (ticket.customer, ticket.message, result["category"], result["priority"],
             result["summary"], result["draft_reply"], result["source"]),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


@app.get("/tickets")
def list_tickets(category: str | None = None, priority: str | None = None):
    query, params = "SELECT * FROM tickets WHERE 1=1", []
    if category:
        query += " AND category = ?"
        params.append(category)
    if priority:
        query += " AND priority = ?"
        params.append(priority)
    with closing(get_conn()) as conn:
        rows = conn.execute(query + " ORDER BY id DESC", params).fetchall()
    return [dict(r) for r in rows]


@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: int):
    with closing(get_conn()) as conn:
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return dict(row)
