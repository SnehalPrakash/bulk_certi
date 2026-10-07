from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import engine, Base
from backend.router import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Automatically ensure database tables are created on startup
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title="Bulk Certificate Generator API",
    description="Production-grade asynchronous backend for bulk certificate generation, failure isolation, and retrieval.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for browser frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "service": "bulk-certificate-generator"}
