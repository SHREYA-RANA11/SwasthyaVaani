
from fastapi import FastAPI
from app.api.auth import router as auth_router

app = FastAPI(
    title="SwasthyaVaani API",
    description="AI-Driven Multilingual Healthcare Assistance Platform",
    version="1.0.0"
)

# Register authentication routes
app.include_router(auth_router)


@app.get("/")
def root():
    return {
        "message": "Welcome to SwasthyaVaani API",
        "status": "running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }
