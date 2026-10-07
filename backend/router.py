import io
import os
import zipfile
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import GenerationJob, CertificateItem, JobStatus, CertificateStatus
from backend.schemas import (
    JobCreateRequest,
    JobStatusResponse,
    CertificateResponse,
    JobListResponse
)
from backend.services import process_certificate_job

router = APIRouter(prefix="/api/v1", tags=["Certificates & Jobs"])

def serialize_job(job: GenerationJob, include_certificates: bool = True) -> JobStatusResponse:
    progress = 0.0
    if job.total_count > 0:
        processed = job.success_count + job.failed_count
        progress = round((processed / job.total_count) * 100, 1)

    certs_list = None
    if include_certificates and job.certificates:
        certs_list = []
        for c in job.certificates:
            download_url = f"/api/v1/certificates/{c.id}/download" if c.status == CertificateStatus.SUCCESS and c.file_path else None
            certs_list.append(CertificateResponse(
                id=c.id,
                recipient_name=c.recipient_name,
                recipient_email=c.recipient_email,
                status=c.status,
                error_message=c.error_message,
                download_url=download_url,
                created_at=c.created_at
            ))

    return JobStatusResponse(
        id=job.id,
        event_name=job.event_name,
        issue_date=job.issue_date,
        status=job.status,
        total_count=job.total_count,
        success_count=job.success_count,
        failed_count=job.failed_count,
        progress_percentage=progress,
        created_at=job.created_at,
        completed_at=job.completed_at,
        certificates=certs_list
    )

@router.post(
    "/jobs",
    response_model=JobStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create Bulk Certificate Generation Job"
)
def create_generation_job(
    payload: JobCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Submits a batch of recipients for certificate generation.
    Returns 202 Accepted immediately with job details while generation runs in the background.
    """
    job = GenerationJob(
        event_name=payload.event_name,
        issue_date=payload.issue_date,
        status=JobStatus.PENDING,
        total_count=len(payload.recipients),
        success_count=0,
        failed_count=0
    )
    db.add(job)
    db.flush()

    # Pre-populate certificate records in PENDING status
    for item in payload.recipients:
        cert = CertificateItem(
            job_id=job.id,
            recipient_name=item.name,
            recipient_email=item.email,
            status=CertificateStatus.PENDING
        )
        db.add(cert)

    db.commit()
    db.refresh(job)

    # Dispatch to non-blocking background worker
    background_tasks.add_task(process_certificate_job, job.id)

    return serialize_job(job, include_certificates=False)

@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    summary="Get Job Status and Progress"
)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """
    Checks the status and detailed progress of a certificate generation job.
    Includes itemized successful and failed recipient reports.
    """
    job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return serialize_job(job, include_certificates=True)

@router.get(
    "/jobs/{job_id}/certificates",
    response_model=List[CertificateResponse],
    summary="List Certificates for Job"
)
def list_job_certificates(job_id: str, db: Session = Depends(get_db)):
    """
    Lists all certificate items for a specific job with statuses and download URLs.
    """
    job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    items = db.query(CertificateItem).filter(CertificateItem.job_id == job_id).all()
    results = []
    for c in items:
        download_url = f"/api/v1/certificates/{c.id}/download" if c.status == CertificateStatus.SUCCESS and c.file_path else None
        results.append(CertificateResponse(
            id=c.id,
            recipient_name=c.recipient_name,
            recipient_email=c.recipient_email,
            status=c.status,
            error_message=c.error_message,
            download_url=download_url,
            created_at=c.created_at
        ))
    return results

@router.get(
    "/certificates/{certificate_id}/download",
    summary="Download Individual Certificate"
)
def download_certificate(certificate_id: str, db: Session = Depends(get_db)):
    """
    Retrieves and downloads an individual generated certificate PNG file.
    """
    cert = db.query(CertificateItem).filter(CertificateItem.id == certificate_id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")

    if cert.status != CertificateStatus.SUCCESS or not cert.file_path or not os.path.exists(cert.file_path):
        raise HTTPException(
            status_code=400,
            detail=f"Certificate cannot be downloaded (Status: {cert.status}, Error: {cert.error_message or 'File not found on disk'})"
        )

    filename = os.path.basename(cert.file_path)
    return FileResponse(
        path=cert.file_path,
        media_type="image/png",
        filename=filename
    )

@router.get(
    "/jobs/{job_id}/download",
    summary="Download All Job Certificates as ZIP"
)
def download_job_zip(job_id: str, db: Session = Depends(get_db)):
    """
    Bundles all successfully generated certificates for a job into a downloadable ZIP archive.
    """
    job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    successful_certs = db.query(CertificateItem).filter(
        CertificateItem.job_id == job_id,
        CertificateItem.status == CertificateStatus.SUCCESS
    ).all()

    if not successful_certs:
        raise HTTPException(
            status_code=400,
            detail="No successfully generated certificates available to download for this job."
        )

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for c in successful_certs:
            if c.file_path and os.path.exists(c.file_path):
                zf.write(c.file_path, arcname=os.path.basename(c.file_path))

    zip_buffer.seek(0)
    safe_event_name = "".join(ch for ch in job.event_name if ch.isalnum() or ch in ("_", "-")).strip() or "certificates"
    zip_filename = f"{safe_event_name}_{job.id[:8]}.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'}
    )

@router.get(
    "/jobs",
    response_model=JobListResponse,
    summary="List Recent Generation Jobs"
)
def list_jobs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Lists recent certificate generation jobs with pagination.
    """
    total = db.query(GenerationJob).count()
    jobs = db.query(GenerationJob).order_by(GenerationJob.created_at.desc()).offset(offset).limit(limit).all()
    return JobListResponse(
        jobs=[serialize_job(j, include_certificates=False) for j in jobs],
        total=total
    )
