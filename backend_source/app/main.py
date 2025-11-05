# backend_source/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create FastAPI instance
app = FastAPI(title="VidReacher Labs API", version="1.0")

# Allow all origins for testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "VidReacher Labs backend is running successfully 🚀"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
