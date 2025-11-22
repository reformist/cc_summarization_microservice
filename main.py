from __future__ import annotations

import os
import socket
from datetime import datetime

from typing import Dict, List
from uuid import UUID

from fastapi import FastAPI, HTTPException
from fastapi import Query, Path
from typing import Optional

from models.person import PersonCreate, PersonRead, PersonUpdate
from models.address import AddressCreate, AddressRead, AddressUpdate
from models.health import Health
from models.product import Product
from models.service import Service
from models.summarization import SummarizationCreate, SummarizationRead, SummarizationDelete, SummarizationUpdate, AsyncRequest
import pymysql
from pymysql.cursors import DictCursor
import uuid
import threading
import time
port = int(os.environ.get("FASTAPIPORT", 8000))

# -----------------------------------------------------------------------------
# Fake in-memory "databases"
# -----------------------------------------------------------------------------
# persons: Dict[UUID, PersonRead] = {}
# addresses: Dict[UUID, AddressRead] = {}
# products: Dict[UUID, Product] = {}




summarizations: Dict[UUID, SummarizationRead] = {}

app = FastAPI(
    title="Summarization Microservice",
    description="Integrates transcription audio into a summarized text format",
    version="0.1.0",
)

conn = pymysql.connect(
    host="127.0.0.1",  # or Cloud SQL private/public IP
    user="test",
    password="1234",
    database="summarization-microservice-cloudsql",
    cursorclass=pymysql.cursors.DictCursor
)
# -----------------------------------------------------------------------------
# Address endpoints
# -----------------------------------------------------------------------------
# test
def create_summarization(summarization: SummarizationCreate):
    new_summarization = summarization.text[:5]
    return SummarizationCreate(
        patient_id=42,
        text=new_summarization
    )
# def delete_summarization(summarization: SummarizationDelete):



# def make_health(echo: Optional[str], path_echo: Optional[str]=None) -> Health:
#     return Health(
#         status=200,
#         status_message="OK",
#         timestamp=datetime.utcnow().isoformat() + "Z",
#         ip_address=socket.gethostbyname(socket.gethostname()),
#         echo=echo,
#         path_echo=path_echo
#     )


# def make_product(echo: Optional[str], path_echo: Optional[str]=None) -> Product:
#     return Product(
#         status=200,
#         status_message="OK",
#         timestamp=datetime.utcnow().isoformat() + "Y",
#         ip_address=socket.gethostbyname(socket.gethostname()),
#         echo=echo,
#         path_echo=path_echo
#     )


@app.get("/summarizations/{summarization_id}")
def get_summarization(summarization_id: int):
    with conn.cursor() as cursor:
        sql = "SELECT id, input_text, summary FROM summaries WHERE id=%s"
        cursor.execute(sql, (summarization_id,))
        row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Summarization not found")

    # Return linked-data response
    return {
        "summarization_id": row["id"],
        "input_text": row["input_text"],
        "summary": row["summary"],
        "links": [
            {"rel": "self", "href": f"/summarizations/{row['id']}"},
            {"rel": "collection", "href": "/summarizations"},
            {"rel": "update", "href": f"/summarizations/{row['id']}"},
            {"rel": "delete", "href": f"/summarizations/{row['id']}"}
        ]
    }

# POST endpoint
@app.post("/summarizations", response_model=dict, status_code=201)
def create_summarization(input_text: str, summary: str):
    with conn.cursor() as cursor:
        sql = "INSERT INTO summaries (input_text, summary) VALUES (%s, %s)"
        cursor.execute(sql, (input_text, summary))
        new_id = cursor.lastrowid
        conn.commit()

    return {
        "summarization_id": new_id,
        "input_text": input_text,
        "summary": summary,
        "links": [
            {"rel": "self", "href": f"/summarizations/{new_id}"},
            {"rel": "collection", "href": "/summarizations"},
            {"rel": "update", "href": f"/summarizations/{new_id}"},
            {"rel": "delete", "href": f"/summarizations/{new_id}"}
        ]
    }
# PUT endpoint
@app.put("/summarizations/{summarization_id}", response_model=dict)
def update_summarization(summarization_id: int, s: SummarizationUpdate):
    with conn.cursor() as cursor:
        cursor.execute("SELECT id FROM summaries WHERE id=%s", (summarization_id,))
        exists = cursor.fetchone()

        if not exists:
            raise HTTPException(status_code=404, detail="Summarization not found")

        sql = "UPDATE summaries SET input_text=%s, summary=%s WHERE id=%s"
        cursor.execute(sql, (s.input_text, s.summary, summarization_id))
        conn.commit()

    return {
        "summarization_id": summarization_id,
        "input_text": s.input_text,
        "summary": s.summary,
        "links": [
            {"rel": "self", "href": f"/summarizations/{summarization_id}"},
            {"rel": "collection", "href": "/summarizations"},
            {"rel": "update", "href": f"/summarizations/{summarization_id}"},
            {"rel": "delete", "href": f"/summarizations/{summarization_id}"}
        ]
    }

# DELETE endpoint
@app.delete("/summarizations/{summarization_id}", response_model=dict)
def delete_summarization(summarization_id: int):
    with conn.cursor() as cursor:
        cursor.execute("SELECT id FROM summaries WHERE id=%s", (summarization_id,))
        exists = cursor.fetchone()

        if not exists:
            raise HTTPException(status_code=404, detail="Summarization not found")

        cursor.execute("DELETE FROM summaries WHERE id=%s", (summarization_id,))
        conn.commit()

    return {
        "message": f"Summarization {summarization_id} deleted",
        "links": [
            {"rel": "collection", "href": "/summarizations"}
        ]
    }


    # UPDATE endpoint
@app.put("/summarizations/{summarization_id}", response_model=SummarizationRead)
def update_summarization(summarization_id: int, summarization: SummarizationUpdate):
    with conn.cursor() as cursor:
        # Check if row exists
        cursor.execute("SELECT id FROM summaries WHERE id=%s", (summarization_id,))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Summarization not found")

        # Update the row
        sql = "UPDATE summaries SET input_text=%s, summary=%s WHERE id=%s"
        cursor.execute(sql, (summarization.input_text, summarization.summary, summarization_id))
        conn.commit()

    return SummarizationRead(
        summarization_id=summarization_id,
        summary=summarization.summary
    )


jobs = {}

# ---- BACKGROUND WORKER ----
def run_summarization_job(job_id: str, input_text: str):
    try:
        jobs[job_id]["status"] = "processing"

        # Simulate slow summarization (replace with real model)
        time.sleep(20)
        summary = input_text[:5]  # pretend this is the summarizer

        # Save into the database
        with conn.cursor() as cursor:
            sql = "INSERT INTO summaries (input_text, summary) VALUES (%s, %s)"
            cursor.execute(sql, (input_text, summary))
            conn.commit()

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["summary"] = summary

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)

# ------------------------------
# 1️⃣  ASYNC SUMMARIZATION ENDPOINT (returns 202)
# ------------------------------
@app.post("/summarizations/async", status_code=202)
def create_async_summarization(input_text: str):

    job_id = str(uuid.uuid4())

    jobs[job_id] = {
        "status": "pending",
        "summary": None
    }

    # Launch background worker
    thread = threading.Thread(
        target=run_summarization_job,
        args=(job_id, input_text)
    )
    thread.start()

    return {
        "job_id": job_id,
        "status": "pending",
        "links": [
            {"rel": "self", "href": f"/jobs/{job_id}"}
        ]
    }

# ------------------------------
# 2️⃣  JOB STATUS POLLING
# ------------------------------
@app.get("/jobs/{job_id}")
def get_job_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    response = {
        "job_id": job_id,
        "status": job["status"],
        "links": [{"rel": "self", "href": f"/jobs/{job_id}"}]
    }

    if job["status"] == "completed":
        response["summary"] = job["summary"]

    if job["status"] == "failed":
        response["error"] = job.get("error")

    return response

# -----------------------------------------------------------------------------
# Root
# -----------------------------------------------------------------------------
@app.get("/")
def root():
    return {"message": "Welcome to the Person/Address API. See /docs for OpenAPI UI."}

# -----------------------------------------------------------------------------
# Entrypoint for `python main.py`
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
