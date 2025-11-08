# backend_source/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import ai_tools

app = FastAPI(title="VidReacher Labs API")

# Allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# include routes
app.include_router(ai_tools.router)

@app.get("/")
def root():
    return {"message": "VidReacher Labs backend is running successfully 🚀"}
