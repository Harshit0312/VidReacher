from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.models import SessionLocal, ScheduledPost, init_db

router = APIRouter(prefix="/scheduler", tags=["Scheduler"])

# Initialize DB
init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ScheduleRequest(BaseModel):
    platform: str
    caption: str
    scheduled_time: datetime  # ISO format e.g. 2025-11-09T14:30:00Z

@router.post("/create")
def create_schedule(req: ScheduleRequest, db: Session = Depends(get_db)):
    post = ScheduledPost(
        platform=req.platform,
        caption=req.caption,
        scheduled_time=req.scheduled_time
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return {"message": "Post scheduled successfully", "id": post.id}

@router.get("/list")
def list_schedules(db: Session = Depends(get_db)):
    posts = db.query(ScheduledPost).order_by(ScheduledPost.scheduled_time).all()
    return [
        {
            "id": p.id,
            "platform": p.platform,
            "caption": p.caption,
            "scheduled_time": p.scheduled_time,
            "status": p.status
        }
        for p in posts
    ]

@router.delete("/delete/{post_id}")
def delete_schedule(post_id: int, db: Session = Depends(get_db)):
    post = db.query(ScheduledPost).filter(ScheduledPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    db.delete(post)
    db.commit()
    return {"message": "Post deleted successfully"}