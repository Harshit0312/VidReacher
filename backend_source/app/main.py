# backend_source/app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.services.background_jobs import start_scheduler
from app.routes import ai_tools, scheduler

# ✅ create FastAPI instance before adding routers
app = FastAPI(title="VidReacher Labs API")

# ✅ enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ include routers after app is defined
app.include_router(ai_tools.router)
app.include_router(scheduler.router)

# ✅ base route to verify backend is live
@app.get("/")
def root():
    return {"message": "VidReacher Labs backend is running successfully 🚀"}

# ✅ Start background scheduler on app startup
@app.on_event("startup")
def startup_event():
    start_scheduler()
