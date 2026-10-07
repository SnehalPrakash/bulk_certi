# Bulk Certificate Generator — Backend API & System

A scalable, asynchronous backend API built with **FastAPI**, **SQLAlchemy**, and **Pillow** to generate bulk event and course certificates from predefined templates with job status tracking and per-recipient failure isolation.

---

## 📋 Table of Contents
- [Architecture & Design Decisions](#-architecture--design-decisions)
- [Tech Stack](#-tech-stack)
- [Quick Start](#-quick-start)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Running the API](#running-the-api)
  - [Interactive API Docs (Swagger)](#interactive-api-docs-swagger)
- [Running Automated Tests](#-running-automated-tests)
- [API Reference & Usage Examples](#-api-reference--usage-examples)
  - [1. Submit a Bulk Generation Job](#1-submit-a-bulk-generation-job)
  - [2. Track Job Progress and Status](#2-track-job-progress-and-status)
  - [3. Retrieve Individual Certificate](#3-retrieve-individual-certificate)
  - [4. Download All Certificates as ZIP](#4-download-all-certificates-as-zip)
  - [5. List Recent Jobs](#5-list-recent-jobs)
- [Failure Handling & Resilience](#-failure-handling--resilience)
- [Project Structure](#-project-structure)

---

## 🏛️ Architecture & Design Decisions

### 1. Asynchronous Background Processing
- **Problem**: Generating hundreds of high-resolution certificates takes seconds to minutes. Synchronous processing blocks HTTP connections, causes gateway timeouts (504s), and degrades API throughput.
- **Solution**: The API uses FastAPI's asynchronous `BackgroundTasks` pattern. When a batch request arrives via `POST /api/v1/jobs`, the system immediately validates input, registers records in the database, and returns **`202 Accepted`** with a tracking `job_id`. The client can poll `/api/v1/jobs/{job_id}` for real-time progress.
- **Production Scalability Note**: The architecture separates the route handlers from `services.py`. In high-load multi-node deployments, this worker function can be offloaded to Celery or Redis Queue (RQ) without altering database models or API contracts.

### 2. Per-Recipient Failure Isolation
- **Requirement**: "A failure while generating one certificate should not unnecessarily prevent other valid certificates in the same job from being generated."
- **Implementation**: Each certificate in a job is processed in an isolated `try/except` block. If an individual record fails (e.g. malformed data, rendering exceptions), that specific item is marked `FAILED` with its detailed `error_message`, while the worker continues processing the remaining valid recipients. The parent job reports `success_count`, `failed_count`, and transitions to `COMPLETED` (or `FAILED` only if all items fail).

### 3. Relational Database with SQLAlchemy
- **Database**: Relational SQLite by default (zero external configuration required for development/interview review) and fully compatible with PostgreSQL via the `DATABASE_URL` environment variable.
- **Schema**:
  - `generation_jobs`: Tracks parent job metadata, event name, status (`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`), total, success, and failure counts.
  - `certificate_items`: One-to-many relationship tracking each recipient, generation status, error message, and output file path on disk.

### 4. High-Resolution Certificate Engine (Pillow)
- Uses an elegant 1920×1080 predefined template (`backend/assets/template.png`).
- Typography is rendered with `america.ttf` and standard fonts, auto-centered and scaled for certificate presentation.

---

## 🛠️ Tech Stack
- **Language**: Python 3.10+ (tested on Python 3.13)
- **Web Framework**: [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/)
- **ORM / Database**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/) (SQLite / PostgreSQL)
- **Data Validation**: [Pydantic v2](https://docs.pydantic.dev/)
- **Image Processing**: [Pillow (PIL)](https://python-pillow.org/)
- **Testing**: [pytest](https://docs.pytest.org/) + [HTTPX](https://www.python-httpx.org/)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10 or higher
- `pip` package manager

### Installation
Clone the repository and install dependencies:
```bash
# Clone
git clone https://github.com/SnehalPrakash/bulk_certi.git
cd bulk_certificate_generator

# (Optional) Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### Running the API
Start the FastAPI server:
```bash
uvicorn backend.main:app --reload --port 8000
```
The API server will be live at: **http://127.0.0.1:8000**

### Interactive API Docs (Swagger)
FastAPI automatically generates interactive OpenAPI documentation:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🧪 Running Automated Tests

The test suite covers the complete application lifecycle:
- Creating a generation job
- Input validation (empty recipient list, blank event name, blank recipient name)
- Certificate generation & progress tracking
- Handling individual certificate failures without halting the batch
- Retrieving single certificate files
- Downloading bulk ZIP archives
- Job pagination

Run tests with `pytest`:
```bash
pytest -v
```

Output:
```text
tests/test_jobs.py::test_health_check PASSED                             [ 10%]
tests/test_jobs.py::test_create_generation_job PASSED                    [ 20%]
tests/test_jobs.py::test_input_validation_empty_recipients PASSED        [ 30%]
tests/test_jobs.py::test_input_validation_blank_event_name PASSED        [ 40%]
tests/test_jobs.py::test_input_validation_blank_recipient_name PASSED    [ 50%]
tests/test_jobs.py::test_certificate_generation_and_progress PASSED      [ 60%]
tests/test_jobs.py::test_individual_certificate_failure_isolation PASSED [ 70%]
tests/test_jobs.py::test_retrieve_single_certificate PASSED              [ 80%]
tests/test_jobs.py::test_retrieve_job_zip_download PASSED                [ 90%]
tests/test_jobs.py::test_list_jobs_endpoint PASSED                       [100%]

============================== 10 passed in 0.82s ==============================
```

---

## 📡 API Reference & Usage Examples

### 1. Submit a Bulk Generation Job
Submits a list of recipients. Returns **202 Accepted** immediately.

**Endpoint**: `POST /api/v1/jobs`

**Request**:
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "event_name": "Full Stack Engineering Bootcamp",
    "issue_date": "October 7, 2026",
    "recipients": [
      {"name": "Alexander Wright", "email": "alex@example.com"},
      {"name": "Sophia Martinez", "email": "sophia@example.com"},
      {"name": "Liam O Connor", "email": "liam@example.com"}
    ]
  }'
```

**Response (`202 Accepted`)**:
```json
{
  "id": "b3e09849-0d3d-4c3e-8488-0fe5e69bf38f",
  "event_name": "Full Stack Engineering Bootcamp",
  "issue_date": "October 7, 2026",
  "status": "PENDING",
  "total_count": 3,
  "success_count": 0,
  "failed_count": 0,
  "progress_percentage": 0.0,
  "created_at": "2026-10-07T18:15:00.000000Z",
  "completed_at": null,
  "certificates": null
}
```

---

### 2. Track Job Progress and Status
Poll job progress, view successful certificates, or check failure causes.

**Endpoint**: `GET /api/v1/jobs/{job_id}`

**Request**:
```bash
curl "http://127.0.0.1:8000/api/v1/jobs/b3e09849-0d3d-4c3e-8488-0fe5e69bf38f"
```

**Response (`200 OK`)**:
```json
{
  "id": "b3e09849-0d3d-4c3e-8488-0fe5e69bf38f",
  "event_name": "Full Stack Engineering Bootcamp",
  "issue_date": "October 7, 2026",
  "status": "COMPLETED",
  "total_count": 3,
  "success_count": 3,
  "failed_count": 0,
  "progress_percentage": 100.0,
  "created_at": "2026-10-07T18:15:00.000000Z",
  "completed_at": "2026-10-07T18:15:01.000000Z",
  "certificates": [
    {
      "id": "4691e847-f472-494b-a25a-fcce7e34ea57",
      "recipient_name": "Alexander Wright",
      "recipient_email": "alex@example.com",
      "status": "SUCCESS",
      "error_message": null,
      "download_url": "/api/v1/certificates/4691e847-f472-494b-a25a-fcce7e34ea57/download",
      "created_at": "2026-10-07T18:15:00.000000Z"
    }
  ]
}
```

---

### 3. Retrieve Individual Certificate
Downloads the PNG certificate for a specific recipient.

**Endpoint**: `GET /api/v1/certificates/{certificate_id}/download`

**Request**:
```bash
curl -O -J "http://127.0.0.1:8000/api/v1/certificates/4691e847-f472-494b-a25a-fcce7e34ea57/download"
```

---

### 4. Download All Certificates as ZIP
Streams a ZIP archive containing all successfully generated certificates for the job.

**Endpoint**: `GET /api/v1/jobs/{job_id}/download`

**Request**:
```bash
curl -O -J "http://127.0.0.1:8000/api/v1/jobs/b3e09849-0d3d-4c3e-8488-0fe5e69bf38f/download"
```

---

### 5. List Recent Jobs
Returns a paginated list of generation jobs.

**Endpoint**: `GET /api/v1/jobs?limit=10&offset=0`

---

## 🛡️ Failure Handling & Resilience

| Scenario | System Behavior |
| :--- | :--- |
| **Empty or Whitespace Name** | Rejected immediately with HTTP `422 Unprocessable Entity`. |
| **Empty Recipients List** | Rejected immediately with HTTP `422 Unprocessable Entity`. |
| **Single Recipient Error during Rendering** | The individual certificate status becomes `FAILED`, its specific error message is recorded, and processing continues for all remaining recipients. |
| **Process Interruption or Re-run** | Job worker resets counters before processing, ensuring safe idempotent execution. |
| **Download Non-Existent or Failed Certificate** | Returns clear HTTP `404` or `400` describing why the file cannot be retrieved. |

---

## 📁 Project Structure

```text
bulk_certificate_generator/
├── backend/
│   ├── assets/
│   │   ├── template.png          # Predefined certificate template
│   │   └── america.ttf           # Default typography font
│   ├── config.py                 # App settings & storage paths
│   ├── database.py               # SQLAlchemy engine & session factory
│   ├── generator.py              # Pillow certificate drawing engine
│   ├── main.py                   # FastAPI application & CORS
│   ├── models.py                 # GenerationJob & CertificateItem ORM models
│   ├── router.py                 # REST API endpoints & serialization
│   ├── schemas.py                # Pydantic v2 request/response validation
│   └── services.py               # Background task worker with failure isolation
├── tests/
│   ├── conftest.py               # Test database fixtures & isolation
│   └── test_jobs.py              # Pytest test suite (10 test cases)
├── output_certificates/          # Generated certificate storage directory
├── requirements.txt              # Pinned Python dependencies
└── README.md                     # Documentation
```

---

## 📄 License
This project is licensed under the MIT License.