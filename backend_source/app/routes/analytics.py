# backend_source/app/routes/analytics.py
from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
from app.db.models_auth import SessionLocal, AnalyticsSnapshot
from typing import List

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/{platform}/latest")
def latest(platform: str):
    db = SessionLocal()
    try:
        row = db.query(AnalyticsSnapshot).filter(AnalyticsSnapshot.platform==platform).order_by(AnalyticsSnapshot.timestamp.desc()).first()
        if not row:
            raise HTTPException(status_code=404, detail="No metrics found")
        return {
            "platform": row.platform,
            "account_id": row.account_id,
            "followers": row.followers,
            "views": row.views,
            "likes": row.likes,
            "comments": row.comments,
            "impressions": row.impressions,
            "reach": row.reach,
            "watch_time": row.watch_time,
            "timestamp": row.timestamp,
            "raw": row.raw
        }
    finally:
        db.close()

@router.get("/{platform}/history")
def history(platform: str, days: int = 30):
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        rows = db.query(AnalyticsSnapshot).filter(AnalyticsSnapshot.platform==platform, AnalyticsSnapshot.timestamp >= cutoff).order_by(AnalyticsSnapshot.timestamp).all()
        return [
            {
                "timestamp": r.timestamp,
                "followers": r.followers,
                "views": r.views,
                "impressions": r.impressions,
                "raw": r.raw
            } for r in rows
        ]
    finally:
        db.close()

@router.get("/overview")
def overview():
    db = SessionLocal()
    try:
        # quick KPIs: latest followers per platform
        platforms = ["instagram", "youtube", "facebook"]
        result = {}
        for p in platforms:
            r = db.query(AnalyticsSnapshot).filter(AnalyticsSnapshot.platform==p).order_by(AnalyticsSnapshot.timestamp.desc()).first()
            if r:
                result[p] = {"followers": r.followers, "views": r.views, "timestamp": r.timestamp}
            else:
                result[p] = None
        return result
    finally:
        db.close()
