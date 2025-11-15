# backend_source/app/services/analytics_fetchers.py
import requests
from datetime import datetime
from app.db.models_auth import SessionLocal, AnalyticsSnapshot, SocialAccount
import logging

logger = logging.getLogger("AnalyticsFetchers")

def fetch_instagram_metrics(acc: SocialAccount, db=None):
    """Fetch simple IG metrics and store a snapshot. acc.account_id should be IG user ID."""
    token = acc.access_token
    if not token:
        logger.warning("No token for instagram account %s", acc.account_id)
        return

    # Try to obtain followers via the IG user node or via connected page
    base = f"https://graph.facebook.com/v16.0/{acc.account_id}"
    params = {"fields": "followers_count", "access_token": token}
    # Some IG endpoints differ; attempt a few
    try:
        r = requests.get(base, params=params, timeout=15)
        data = r.json()
    except Exception as e:
        logger.error("IG request error: %s", e)
        return

    followers = None
    impressions = None
    try:
        followers = int(data.get("followers_count")) if data.get("followers_count") else None
    except Exception:
        followers = None

    # For impressions/reach, call insights endpoint if available (example)
    try:
        insights_res = requests.get(f"{base}/insights", params={"metric": "impressions,reach,engagement", "access_token": token}, timeout=15)
        insights = insights_res.json()
        impressions = None
        # Parse insights array if present
        if isinstance(insights, dict) and "data" in insights:
            # naive parse to sum values (real response needs careful parsing)
            for item in insights.get("data", []):
                if item.get("name") == "impressions":
                    vals = item.get("values", [])
                    impressions = vals[-1].get("value") if vals else None
    except Exception:
        impressions = None

    local_db = db or SessionLocal()
    try:
        snap = AnalyticsSnapshot(
            platform="instagram",
            account_id=acc.account_id,
            followers=followers,
            impressions=impressions,
            raw={"profile": data},
            timestamp=datetime.utcnow()
        )
        local_db.add(snap)
        local_db.commit()
    finally:
        if db is None:
            local_db.close()

def fetch_youtube_metrics(acc: SocialAccount, db=None):
    token = acc.access_token
    if not token:
        logger.warning("No token for youtube account %s", acc.account_id)
        return

    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(f"https://www.googleapis.com/youtube/v3/channels?part=statistics&id={acc.account_id}", headers=headers, timeout=15)
        data = r.json()
        stats = data.get("items", [])[0].get("statistics", {}) if data.get("items") else {}
    except Exception as e:
        logger.error("YT fetch error: %s", e)
        return

    subscribers = int(stats.get("subscriberCount", 0)) if stats.get("subscriberCount") else None
    views = int(stats.get("viewCount", 0)) if stats.get("viewCount") else None

    local_db = db or SessionLocal()
    try:
        snap = AnalyticsSnapshot(
            platform="youtube",
            account_id=acc.account_id,
            followers=subscribers,
            views=views,
            raw=data,
            timestamp=datetime.utcnow()
        )
        local_db.add(snap)
        local_db.commit()
    finally:
        if db is None:
            local_db.close()

def fetch_facebook_metrics(acc: SocialAccount, db=None):
    token = acc.access_token
    if not token:
        logger.warning("No token for facebook account %s", acc.account_id)
        return

    try:
        r = requests.get(f"https://graph.facebook.com/v16.0/{acc.account_id}/insights", params={"metric":"page_impressions,page_engaged_users", "access_token": token}, timeout=15)
        data = r.json()
    except Exception as e:
        logger.error("FB fetch error: %s", e)
        return

    impressions = None
    try:
        if isinstance(data, dict) and "data" in data:
            # naive parse: take first metric's last value
            first = data["data"][0]
            vals = first.get("values", [])
            impressions = vals[-1].get("value") if vals else None
    except Exception:
        impressions = None

    local_db = db or SessionLocal()
    try:
        snap = AnalyticsSnapshot(
            platform="facebook",
            account_id=acc.account_id,
            impressions=impressions,
            raw=data,
            timestamp=datetime.utcnow()
        )
        local_db.add(snap)
        local_db.commit()
    finally:
        if db is None:
            local_db.close()

def fetch_all_analytics():
    db = SessionLocal()
    try:
        accounts = db.query(SocialAccount).all()
        for acc in accounts:
            try:
                if acc.platform == "instagram":
                    fetch_instagram_metrics(acc, db)
                elif acc.platform == "youtube":
                    fetch_youtube_metrics(acc, db)
                elif acc.platform == "facebook":
                    fetch_facebook_metrics(acc, db)
            except Exception as e:
                logger.exception("Failed to fetch for %s:%s -> %s", acc.platform, acc.account_id, e)
    finally:
        db.close()
