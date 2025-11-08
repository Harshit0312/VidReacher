# backend_source/app/services/background_jobs.py
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from app.db.models import SessionLocal, ScheduledPost
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VidReacherScheduler")

def process_scheduled_posts():
    """Check DB for due posts and mark them as posted."""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        due_posts = db.query(ScheduledPost).filter(
            ScheduledPost.status == "pending",
            ScheduledPost.scheduled_time <= now
        ).all()

        for post in due_posts:
            post.status = "posted"
            db.commit()
            logger.info(f"[✅ POSTED] {post.platform.upper()} - {post.caption[:50]}... at {now}")
    except Exception as e:
        logger.error(f"Error processing scheduled posts: {e}")
    finally:
        db.close()

def start_scheduler():
    """Starts the background scheduler that runs every 60 seconds."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(process_scheduled_posts, "interval", seconds=60, id="post_checker")
    scheduler.start()
    logger.info("✅ Background Scheduler started (checks every 60 seconds)")