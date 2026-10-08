"""
StudyLens AI - Academic AI Tutor Backend
FastAPI application entrypoint with centralized routing, OpenAPI documentation,
structured logging middleware, and error taxonomy handlers.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.core.errors import AppException
from backend.app.core.logging import RequestLoggingMiddleware
from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.documents import router as documents_router, upload_document
from backend.app.api.routes.chat import router as chat_router
from backend.app.api.routes.study_tools import router as study_tools_router
from backend.app.api.routes.conversations import router as conversations_router

TAGS_METADATA = [
    {
        "name": "Health",
        "description": "Liveness and operational readiness verification endpoints.",
    },
    {
        "name": "Documents",
        "description": "PDF ingestion, page text extraction, vector indexing, metadata inspection, and safe deletion.",
    },
    {
        "name": "Chat",
        "description": "Grounded academic tutoring powered by Nemotron 3 Nano 30B Cloud via Ollama Cloud with page-level citations.",
    },
    {
        "name": "Study Tools",
        "description": "Document-grounded structured summaries, revision notes, and interactive MCQ quizzes with weak topic analysis.",
    },
    {
        "name": "Conversations",
        "description": "Persistent multi-turn chat sessions with automatic titles, message history, and document-level isolation.",
    },
]

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "**StudyLens AI** is an academic AI tutor service that allows students to upload PDFs, "
        "indexes chunks with dense vector embeddings, and generates strictly grounded answers "
        "using Nemotron 3 Nano 30B Cloud via Ollama Cloud."
    ),
    openapi_tags=TAGS_METADATA,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Request tracing & performance logging middleware
app.add_middleware(RequestLoggingMiddleware)

# CORS Middleware configured for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Standardized Error Taxonomy Handlers
@app.exception_handler(AppException)
async def app_exception_handler(_request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException):
    code = "VALIDATION_ERROR" if exc.status_code == 422 else "REQUEST_ERROR"
    detail_msg = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": detail_msg,
            "error": {
                "code": code,
                "message": detail_msg,
            },
        },
    )


# Include API Routers under /api
app.include_router(health_router, prefix=settings.API_V1_PREFIX)
app.include_router(documents_router, prefix=settings.API_V1_PREFIX)
app.include_router(chat_router, prefix=settings.API_V1_PREFIX)
app.include_router(study_tools_router, prefix=settings.API_V1_PREFIX)
app.include_router(conversations_router, prefix=settings.API_V1_PREFIX)

# Alias for backwards compatibility
app.post("/api/upload", include_in_schema=False)(upload_document)


@app.get("/", include_in_schema=False)
def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": f"{settings.API_V1_PREFIX}/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
