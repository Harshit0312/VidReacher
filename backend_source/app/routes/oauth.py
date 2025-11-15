# backend_source/app/routes/oauth.py
import os
import time
from urllib.parse import urlencode
import requests
from datetime import datetime, timedelta
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse
from app.db.models_auth import SessionLocal, SocialAccount, init_auth_db

router = APIRouter(prefix="/oauth", tags=["OAuth"])
# initialize auth tables
init_auth_db()

META_APP_ID = os.getenv("META_APP_ID")
META_APP_SECRET = os.getenv("META_APP_SECRET")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
OAUTH_REDIRECT_BASE = os.getenv("OAUTH_REDIRECT_BASE", "http://127.0.0.1:8000")
FRONTEND_BASE = os.getenv("FRONTEND_BASE", "http://localhost:5173")

# --- Meta (Facebook / Instagram) OAuth start ---
@router.get("/meta/start")
def meta_start():
    redirect_uri = f"{OAUTH_REDIRECT_BASE}/oauth/meta/callback"
    params = {
        "client_id": META_APP_ID,
        "redirect_uri": redirect_uri,
        "scope": ",".join([
            "pages_show_list",
            "pages_read_engagement",
            "pages_read_user_content",
            "instagram_basic",
            "instagram_manage_insights"
        ]),
        "response_type": "code",
    }
    return RedirectResponse(f"https://www.facebook.com/v16.0/dialog/oauth?{urlencode(params)}")

@router.get("/meta/callback")
def meta_callback(code: str = None, error: str = None):
    if error:
        return JSONResponse({"error": error}, status_code=400)
    redirect_uri = f"{OAUTH_REDIRECT_BASE}/oauth/meta/callback"

    # Exchange code for short-lived token
    token_url = "https://graph.facebook.com/v16.0/oauth/access_token"
    params = {
        "client_id": META_APP_ID,
        "redirect_uri": redirect_uri,
        "client_secret": META_APP_SECRET,
        "code": code
    }
    r = requests.get(token_url, params=params)
    data = r.json()
    access_token = data.get("access_token")
    if not access_token:
        return JSONResponse({"error": "Failed to obtain token", "details": data}, status_code=400)

    # Exchange short-lived to long-lived token
    long_url = "https://graph.facebook.com/v16.0/oauth/access_token"
    params2 = {
        "grant_type": "fb_exchange_token",
        "client_id": META_APP_ID,
        "client_secret": META_APP_SECRET,
        "fb_exchange_token": access_token
    }
    r2 = requests.get(long_url, params=params2)
    long_data = r2.json()
    long_token = long_data.get("access_token") or access_token
    expires_in = long_data.get("expires_in")  # seconds, may be absent

    # Get pages the user manages to link to a page and IG account
    pages_url = f"https://graph.facebook.com/v16.0/me/accounts"
    pages_res = requests.get(pages_url, params={"access_token": long_token})
    pages = pages_res.json().get("data", [])

    saved = []
    db = SessionLocal()
    try:
        for page in pages:
            page_id = page.get("id")
            # Get connected IG business account id (if any)
            page_info = requests.get(
                f"https://graph.facebook.com/v16.0/{page_id}",
                params={"fields": "instagram_business_account", "access_token": long_token}
            ).json()
            ig = page_info.get("instagram_business_account")
            account_id = ig.get("id") if ig else page_id
            sa = SocialAccount(
                platform="instagram" if ig else "facebook",
                account_id=str(account_id),
                access_token=long_token,
                refresh_token=None,
                token_expires_at=datetime.utcnow() + timedelta(seconds=expires_in) if expires_in else None,
                meta_data={"page": page, "page_info": page_info}
            )
            db.add(sa)
            db.commit()
            db.refresh(sa)
            saved.append(sa.id)
    finally:
        db.close()

    # Redirect back to frontend with success
    return RedirectResponse(f"{FRONTEND_BASE}/?connected=meta&ids={','.join(map(str,saved))}")

# --- Google OAuth (YouTube) start ---
@router.get("/google/start")
def google_start():
    redirect_uri = f"{OAUTH_REDIRECT_BASE}/oauth/google/callback"
    scope = " ".join([
        "https://www.googleapis.com/auth/youtube.readonly",
        "https://www.googleapis.com/auth/yt-analytics.readonly",
        "openid", "email", "profile"
    ])
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "access_type": "offline",
        "include_granted_scopes": "true",
        "response_type": "code",
        "prompt": "consent"
    }
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}")

@router.get("/google/callback")
def google_callback(code: str = None, error: str = None):
    if error:
        return JSONResponse({"error": error}, status_code=400)
    token_url = "https://oauth2.googleapis.com/token"
    redirect_uri = f"{OAUTH_REDIRECT_BASE}/oauth/google/callback"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    r = requests.post(token_url, data=data)
    tok = r.json()
    access_token = tok.get("access_token")
    refresh_token = tok.get("refresh_token")  # keep for refresh
    expires_in = tok.get("expires_in")

    # Get channel info
    headers = {"Authorization": f"Bearer {access_token}"}
    channel_res = requests.get("https://www.googleapis.com/youtube/v3/channels?part=id,snippet&mine=true", headers=headers)
    ch = channel_res.json()
    items = ch.get("items", [])
    channel_id = items[0]["id"] if items else None

    # Save to DB
    db = SessionLocal()
    try:
        sa = SocialAccount(
            platform="youtube",
            account_id=channel_id or "unknown",
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=datetime.utcnow() + timedelta(seconds=expires_in) if expires_in else None,
            meta_data=ch
        )
        db.add(sa)
        db.commit()
        db.refresh(sa)
        saved_id = sa.id
    finally:
        db.close()

    return RedirectResponse(f"{FRONTEND_BASE}/?connected=google&id={saved_id}")