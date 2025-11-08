# backend_source/app/routes/ai_tools.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services import ai_engine_v2 as ai_engine

router = APIRouter(prefix="/ai", tags=["AI Tools"])

# request models
class CaptionRequest(BaseModel):
    text: str
    tone: str = "neutral"
    length: str = "short"
    platform: str = "generic"

class HashtagRequest(BaseModel):
    text: str
    max_tags: int = 8

class SummaryRequest(BaseModel):
    transcript: str
    max_sentences: int = 3

@router.post("/caption")
def generate_caption(req: CaptionRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text is required")
    result = ai_engine.generate_caption(req.text, tone=req.tone, length=req.length, platform=req.platform)
    return {"caption": result}

@router.post("/tags")
def generate_tags(req: HashtagRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text is required")
    tags = ai_engine.generate_hashtags(req.text, max_tags=req.max_tags)
    return {"tags": tags}

@router.post("/summary")
def summarize_video(req: SummaryRequest):
    if not req.transcript.strip():
        raise HTTPException(status_code=400, detail="Transcript is required")
    summary = ai_engine.summarize_video(req.transcript, max_sentences=req.max_sentences)
    return {"summary": summary}