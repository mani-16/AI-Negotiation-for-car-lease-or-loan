from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import init_db
from app.core.config import settings
from app.api import auth, documents, chat, vin, compare, admin

app = FastAPI(title="Car Contract AI", version="1.0.0")

async def recover_stuck_documents():
    """
    On startup: find ALL documents stuck in 'processing' or
    'extraction_complete'. Reset them to 'sla_failed' so the
    retry button appears.
    Any background tasks from a previous server process are dead,
    so there's no risk of racing with an active task.
    """
    from sqlalchemy import update as sql_update
    from app.models.models import Document
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                sql_update(Document)
                .where(
                    Document.processing_status.in_(
                        ["processing", "extraction_complete"]
                    ),
                )
                .values(
                    processing_status="sla_failed",
                    error_message=(
                        "Analysis was interrupted. "
                        "Click Retry to try again."
                    ),
                )
            )
            await db.commit()
            count = result.rowcount
            if count > 0:
                print(
                    f"[startup] Recovered {count} stuck document(s)"
                )
        except Exception as e:
            print(f"[startup] Stuck document recovery failed: {e}")


@app.on_event("startup")
async def startup():
    init_db(settings.DATABASE_URL)
    await recover_stuck_documents()

app.add_middleware(
    CORSMiddleware,
    # allow_origins=["*"] is incompatible with allow_credentials=True.
    # List every frontend origin explicitly.
    allow_origins=list(filter(None, {
        settings.FRONTEND_URL,          # e.g. https://your-app.vercel.app
        "http://localhost:5173",         # Vite dev server
        "http://localhost:3000",         # CRA / Next dev server (if used)
    })),
    allow_credentials=True,             # needed for HTTP-only cookie
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(documents.router, prefix="/documents", tags=["Documents"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(vin.router, prefix="/vin", tags=["VIN"])
app.include_router(compare.router, prefix="/compare", tags=["Compare"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])

@app.get("/")
async def root():
    return {"status": "running", "docs": "/docs"}