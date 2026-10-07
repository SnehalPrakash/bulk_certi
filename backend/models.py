import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from backend.database import Base

class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class CertificateStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_name = Column(String(200), nullable=False)
    issue_date = Column(String(50), nullable=True)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False, index=True)
    
    total_count = Column(Integer, default=0, nullable=False)
    success_count = Column(Integer, default=0, nullable=False)
    failed_count = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime, nullable=True)

    certificates = relationship(
        "CertificateItem",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="CertificateItem.created_at"
    )

class CertificateItem(Base):
    __tablename__ = "certificate_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(36), ForeignKey("generation_jobs.id"), nullable=False, index=True)
    
    recipient_name = Column(String(150), nullable=False)
    recipient_email = Column(String(150), nullable=True)
    
    status = Column(Enum(CertificateStatus), default=CertificateStatus.PENDING, nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    file_path = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    job = relationship("GenerationJob", back_populates="certificates")
