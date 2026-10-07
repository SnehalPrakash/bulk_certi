import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models import GenerationJob, CertificateItem, JobStatus, CertificateStatus
from backend.generator import generate_certificate_image

logger = logging.getLogger("certificate_service")

def process_certificate_job(job_id: str, db: Session = None):
    """
    Background worker task to process a certificate generation job.
    Provides strict per-recipient failure isolation so one broken record
    never cancels or halts the remaining certificates in the job.
    """
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True
    try:
        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found for background execution.")
            return

        job.status = JobStatus.PROCESSING
        job.success_count = 0
        job.failed_count = 0
        db.commit()

        certificates = db.query(CertificateItem).filter(CertificateItem.job_id == job_id).all()

        for cert in certificates:
            try:
                # Additional per-recipient defensive validation check
                if not cert.recipient_name or not cert.recipient_name.strip():
                    raise ValueError("Recipient name cannot be blank or whitespace.")

                # If name contains synthetic test trigger for failure simulation
                if cert.recipient_name.lower().startswith("__fail__"):
                    raise RuntimeError("Simulated processing error for recipient.")

                # Generate certificate
                file_path = generate_certificate_image(
                    job_id=job.id,
                    cert_id=cert.id,
                    recipient_name=cert.recipient_name,
                    event_name=job.event_name,
                    issue_date=job.issue_date
                )

                cert.status = CertificateStatus.SUCCESS
                cert.file_path = file_path
                job.success_count += 1

            except Exception as e:
                logger.warning(f"Failed generating certificate for {cert.recipient_name}: {e}")
                cert.status = CertificateStatus.FAILED
                cert.error_message = str(e)
                job.failed_count += 1

            db.commit()

        # Update final job state
        job.completed_at = datetime.now(timezone.utc)
        if job.failed_count == job.total_count and job.total_count > 0:
            job.status = JobStatus.FAILED
        else:
            job.status = JobStatus.COMPLETED

        db.commit()
        logger.info(f"Job {job_id} completed: {job.success_count} succeeded, {job.failed_count} failed.")

    except Exception as e:
        logger.error(f"Fatal error processing job {job_id}: {e}", exc_info=True)
        try:
            job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
            if job:
                job.status = JobStatus.FAILED
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            pass
    finally:
        if should_close:
            db.close()
