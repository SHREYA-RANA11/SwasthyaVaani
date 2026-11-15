from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.admin import router as admin_router
from app.api.prescriptions import router as prescriptions_router
from app.api.doses import router as doses_router
from app.core.config import settings

app = FastAPI(
    title="SwasthyaVaani API",
    description="AI-Driven Multilingual Healthcare Assistance Platform",
    version="1.0.0"
)

# Allow the React dev server (Vite) to call this API from the browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(admin_router)
app.include_router(prescriptions_router)
app.include_router(doses_router)


@app.get("/")
def root():
    return {"message": "Welcome to SwasthyaVaani API", "status": "running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
