# backend_source/app/services/oauth_utils.py
import os
import requests
from datetime import datetime, timedelta
from app.db.models_auth import SessionLocal, SocialAccount
from typing import Optional

META_APP_ID = os.getenv("META_APP_ID")
META_APP_SECRET = os.getenv("META_APP_SECRET")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

def refresh_google_token(sa: SocialAccount) -> Optional[str]:
    """Use refresh_token to get a new access token for Google. Returns new access_token or None."""
    if not sa.refresh_token:
        return None
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "refresh_token": sa.refresh_token,
        "grant_type": "refresh_token"
    }
    r = requests.post(token_url, data=data)
    if r.status_code != 200:
        return None
    tok = r.json()
    access_token = tok.get("access_token")
    expires_in = tok.get("expires_in")
    # update DB
    db = SessionLocal()
    try:
        obj = db.query(SocialAccount).filter(SocialAccount.id == sa.id).first()
        if obj:
            obj.access_token = access_token
            obj.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in) if expires_in else None
            db.commit()
    finally:
        db.close()
    return access_token

def refresh_meta_token_if_needed(sa: SocialAccount) -> Optional[str]:
    """Meta tokens are long-lived. If token_expires_at is near, you may want to re-exchange. For now, return current token."""
    if not sa.access_token:
        return None
    # Placeholder — in production we might re-exchange or prompt user to reconnect.
    return sa.access_token

def get_social_account_by_id(sa_id: int):
    db = SessionLocal()
    try:
        return db.query(SocialAccount).filter(SocialAccount.id == sa_id).first()
    finally:
        db.close()
