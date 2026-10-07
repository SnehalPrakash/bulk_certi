import io
import time
import zipfile
from backend.services import process_certificate_job

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_create_generation_job(client):
    """Test creating a valid certificate generation job returns 202 Accepted."""
    payload = {
        "event_name": "Full Stack Web Development Bootcamp",
        "issue_date": "October 7, 2026",
        "recipients": [
            {"name": "Alice Johnson", "email": "alice@example.com"},
            {"name": "Bob Smith", "email": "bob@example.com"}
        ]
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert "id" in data
    assert data["event_name"] == payload["event_name"]
    assert data["total_count"] == 2
    assert data["status"] in ["PENDING", "PROCESSING", "COMPLETED"]

def test_input_validation_empty_recipients(client):
    """Test rejecting job requests with empty recipients list."""
    payload = {
        "event_name": "AI Workshop",
        "recipients": []
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422

def test_input_validation_blank_event_name(client):
    """Test rejecting job requests with empty or blank event name."""
    payload = {
        "event_name": "   ",
        "recipients": [{"name": "Charlie"}]
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422

def test_input_validation_blank_recipient_name(client):
    """Test rejecting job requests where a recipient has an empty name."""
    payload = {
        "event_name": "AI Workshop",
        "recipients": [{"name": "   "}]
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422

def test_certificate_generation_and_progress(client):
    """Test certificate generation, progress tracking, and final completion."""
    payload = {
        "event_name": "Cloud Architecture Masterclass",
        "issue_date": "2026-10-07",
        "recipients": [
            {"name": "Diana Prince", "email": "diana@themyscira.com"},
            {"name": "Bruce Wayne", "email": "bruce@wayne.com"}
        ]
    }
    create_res = client.post("/api/v1/jobs", json=payload)
    assert create_res.status_code == 202
    job_id = create_res.json()["id"]

    # In TestClient, background tasks run synchronously during request lifecycle,
    # or we can invoke directly to verify
    process_certificate_job(job_id)

    # Check status
    status_res = client.get(f"/api/v1/jobs/{job_id}")
    assert status_res.status_code == 200
    job_data = status_res.json()

    assert job_data["status"] == "COMPLETED"
    assert job_data["total_count"] == 2
    assert job_data["success_count"] == 2
    assert job_data["failed_count"] == 0
    assert job_data["progress_percentage"] == 100.0
    assert len(job_data["certificates"]) == 2

    # Check that certificates have download URLs
    for cert in job_data["certificates"]:
        assert cert["status"] == "SUCCESS"
        assert cert["download_url"] is not None

def test_individual_certificate_failure_isolation(client):
    """
    CRITICAL REQUIREMENT:
    Verify that a failure generating one certificate does not prevent other
    valid certificates in the same job from being generated successfully.
    """
    payload = {
        "event_name": "Data Science Summit",
        "issue_date": "2026-10-07",
        "recipients": [
            {"name": "Valid Recipient One"},
            {"name": "__fail__ Corrupted Data"},  # Triggers simulated processing error
            {"name": "Valid Recipient Two"}
        ]
    }
    create_res = client.post("/api/v1/jobs", json=payload)
    assert create_res.status_code == 202
    job_id = create_res.json()["id"]

    # Run processing
    process_certificate_job(job_id)

    status_res = client.get(f"/api/v1/jobs/{job_id}")
    assert status_res.status_code == 200
    job_data = status_res.json()

    # Job is COMPLETED with partial successes
    assert job_data["status"] == "COMPLETED"
    assert job_data["total_count"] == 3
    assert job_data["success_count"] == 2
    assert job_data["failed_count"] == 1

    # Verify per-certificate breakdown
    certs = job_data["certificates"]
    assert len(certs) == 3

    successes = [c for c in certs if c["status"] == "SUCCESS"]
    failures = [c for c in certs if c["status"] == "FAILED"]

    assert len(successes) == 2
    assert len(failures) == 1

    failed_cert = failures[0]
    assert failed_cert["recipient_name"] == "__fail__ Corrupted Data"
    assert "Simulated processing error" in failed_cert["error_message"]

def test_retrieve_single_certificate(client):
    """Test retrieving and downloading an individual certificate file."""
    payload = {
        "event_name": "Cybersecurity Fundamentals",
        "recipients": [{"name": "Neo Anderson"}]
    }
    create_res = client.post("/api/v1/jobs", json=payload)
    job_id = create_res.json()["id"]
    process_certificate_job(job_id)

    status_res = client.get(f"/api/v1/jobs/{job_id}")
    cert_id = status_res.json()["certificates"][0]["id"]

    download_res = client.get(f"/api/v1/certificates/{cert_id}/download")
    assert download_res.status_code == 200
    assert download_res.headers["content-type"] == "image/png"
    assert len(download_res.content) > 0

def test_retrieve_job_zip_download(client):
    """Test downloading all certificates in a job as a valid ZIP archive."""
    payload = {
        "event_name": "DevOps Intensive",
        "recipients": [
            {"name": "Grace Hopper"},
            {"name": "Ada Lovelace"}
        ]
    }
    create_res = client.post("/api/v1/jobs", json=payload)
    job_id = create_res.json()["id"]
    process_certificate_job(job_id)

    zip_res = client.get(f"/api/v1/jobs/{job_id}/download")
    assert zip_res.status_code == 200
    assert zip_res.headers["content-type"] == "application/zip"

    # Verify ZIP validity
    zip_bytes = io.BytesIO(zip_res.content)
    with zipfile.ZipFile(zip_bytes, "r") as zf:
        file_list = zf.namelist()
        assert len(file_list) == 2
        assert any("Grace_Hopper" in f for f in file_list)
        assert any("Ada_Lovelace" in f for f in file_list)

def test_list_jobs_endpoint(client):
    """Test listing recent jobs with pagination."""
    res = client.get("/api/v1/jobs?limit=10&offset=0")
    assert res.status_code == 200
    data = res.json()
    assert "jobs" in data
    assert "total" in data
    assert isinstance(data["jobs"], list)
