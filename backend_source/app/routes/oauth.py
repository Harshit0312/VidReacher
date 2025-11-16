# backend_source/app/routes/oauth.py
import os
from urllib.parse import urlencode
import requests
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Query
from fastapi.responses import RedirectResponse, JSONResponse
from app.db.models_auth import SessionLocal, SocialAccount, init_auth_db

router = APIRouter(prefix="/oauth", tags=["OAuth"])
init_auth_db()

# Env
META_APP_ID = os.getenv("META_APP_ID")
META_APP_SECRET = os.getenv("META_APP_SECRET")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
OAUTH_REDIRECT_BASE = os.getenv("OAUTH_REDIRECT_BASE", "http://127.0.0.1:8000")
FRONTEND_BASE = os.getenv("FRONTEND_BASE", "http://localhost:5173")

# -------- META / FACEBOOK / INSTAGRAM OAUTH --------
@router.get("/meta/start")
def meta_start(redirect_to: str | None = None):
    """
    Start Meta (Facebook) OAuth.
    - redirect_to: optional frontend path you want to return user after success (e.g. '/dashboard')
    """
    redirect_uri = f"{OAUTH_REDIRECT_BASE}/oauth/meta/callback"
    # Minimal scopes for testing/developer accounts. Avoid scopes that require App Review.
    scopes = [
        "pages_show_list",    # list pages the user manages (useful to link a page)
        "public_profile",
        "email",
        # NOTE: do NOT add instagram_basic/pages_read_engagement/instagram_manage_insights here
        # until you've completed App Review — otherwise Facebook shows "Invalid Scopes".
    ]
    params = {
        "client_id": META_APP_ID,
        "redirect_uri": redirect_uri,
        "scope": ",".join(scopes),
        "response_type": "code",
        "state": str(int(datetime.utcnow().timestamp())),  # simple state for debugging
    }
    if redirect_to:
        # include the frontend path in a state-like query (optional)
        params["state"] = f"{params['state']}|{redirect_to}"
    auth_url = f"https://www.facebook.com/v16.0/dialog/oauth?{urlencode(params)}"
    return RedirectResponse(auth_url)

@router.get("/meta/callback")
def meta_callback(code: str | None = None, error: str | None = None, state: str | None = None):
    """
    Callback from Meta. Exchanges code for token, fetches pages, saves SocialAccount rows.
    Returns a RedirectResponse to FRONTEND_BASE with query parameters indicating success or failure.
    """
    # If provider returned an error param, forward it to frontend
    if error:
        return RedirectResponse(f"{FRONTEND_BASE}/?connected=meta&error={error}")

    if not code:
        # No code — return more debugging info to frontend
        return JSONResponse({"error": "Missing authorization code from Meta callback", "state": state}, status_code=400)

    redirect_uri = f"{OAUTH_REDIRECT_BASE}/oauth/meta/callback"

    # Exchange code for short-lived access token
    token_url = "https://graph.facebook.com/v16.0/oauth/access_token"
    params = {
        "client_id": META_APP_ID,
        "redirect_uri": redirect_uri,
        "client_secret": META_APP_SECRET,
        "code": code
    }
    try:
        r = requests.get(token_url, params=params, timeout=10)
        data = r.json()
    except Exception as e:
        return JSONResponse({"error": "Token exchange request failed", "details": str(e)}, status_code=500)

    # If exchange returned an error, pass it back
    if r.status_code != 200 or "access_token" not in data:
        return JSONResponse({"error": "Failed to obtain token", "details": data}, status_code=400)

    access_token = data.get("access_token")

    # Try to exchange short-lived for long-lived token (best-effort)
    try:
        long_url = "https://graph.facebook.com/v16.0/oauth/access_token"
        params2 = {
            "grant_type": "fb_exchange_token",
            "client_id": META_APP_ID,
            "client_secret": META_APP_SECRET,
            "fb_exchange_token": access_token
        }
        r2 = requests.get(long_url, params=params2, timeout=10)
        long_data = r2.json()
        long_token = long_data.get("access_token") or access_token
        expires_in = long_data.get("expires_in")
    except Exception:
        long_token = access_token
        expires_in = None

    # Fetch pages the user manages (may be empty)
    try:
        pages_url = f"https://graph.facebook.com/v16.0/me/accounts"
        pages_res = requests.get(pages_url, params={"access_token": long_token}, timeout=10)
        pages_json = pages_res.json()
        pages = pages_json.get("data", []) if isinstance(pages_json, dict) else []
    except Exception:
        pages = []

    saved_ids = []
    db = SessionLocal()
    try:
        # If user has no pages, still create a SocialAccount row for the user profile (facebook profile)
        if not pages:
            # Try to fetch user id as fallback
            try:
                me = requests.get("https://graph.facebook.com/v16.0/me", params={"access_token": long_token, "fields": "id,name"}, timeout=10).json()
                uid = me.get("id")
            except Exception:
                uid = None
            sa = SocialAccount(
                platform="facebook",
                account_id=str(uid) if uid else "unknown",
                access_token=long_token,
                refresh_token=None,
                token_expires_at=(datetime.utcnow() + timedelta(seconds=expires_in)) if expires_in else None,
                meta_data={"pages": [], "me": uid}
            )
            db.add(sa)
            db.commit()
            db.refresh(sa)
            saved_ids.append(sa.id)
        else:
            for page in pages:
                page_id = page.get("id")
                # Try to fetch connected IG business account if present (best-effort)
                try:
                    page_info = requests.get(
                        f"https://graph.facebook.com/v16.0/{page_id}",
                        params={"fields": "instagram_business_account", "access_token": long_token},
                        timeout=10
                    ).json()
                except Exception:
                    page_info = {}
                ig = page_info.get("instagram_business_account")
                account_id = ig.get("id") if ig else page_id
                sa = SocialAccount(
                    platform="instagram" if ig else "facebook",
                    account_id=str(account_id),
                    access_token=long_token,
                    refresh_token=None,
                    token_expires_at=(datetime.utcnow() + timedelta(seconds=expires_in)) if expires_in else None,
                    meta_data={"page": page, "page_info": page_info}
                )
                db.add(sa)
                db.commit()
                db.refresh(sa)
                saved_ids.append(sa.id)
    finally:
        db.close()

    # Redirect back to frontend with success (or list of saved ids)
    if saved_ids:
        return RedirectResponse(f"{FRONTEND_BASE}/?connected=meta&ids={','.join(map(str,saved_ids))}")
    else:
        return RedirectResponse(f"{FRONTEND_BASE}/?connected=meta&ids=")

# -------- GOOGLE (YouTube) OAUTH (unchanged) --------
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
def google_callback(code: str | None = None, error: str | None = None):
    if error:
        return JSONResponse({"error": error}, status_code=400)
    if not code:
        return JSONResponse({"error": "Missing authorization code from Google callback"}, status_code=400)

    token_url = "https://oauth2.googleapis.com/token"
    redirect_uri = f"{OAUTH_REDIRECT_BASE}/oauth/google/callback"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    try:
        r = requests.post(token_url, data=data, timeout=10)
        tok = r.json()
    except Exception as e:
        return JSONResponse({"error": "Google token exchange failed", "details": str(e)}, status_code=500)

    access_token = tok.get("access_token")
    refresh_token = tok.get("refresh_token")
    expires_in = tok.get("expires_in")

    if not access_token:
        return JSONResponse({"error": "Failed to obtain Google token", "details": tok}, status_code=400)

    # Get channel info
    headers = {"Authorization": f"Bearer {access_token}"}
    channel_res = requests.get("https://www.googleapis.com/youtube/v3/channels?part=id,snippet&mine=true", headers=headers, timeout=10)
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
            token_expires_at=(datetime.utcnow() + timedelta(seconds=expires_in)) if expires_in else None,
            meta_data=ch
        )
        db.add(sa)
        db.commit()
        db.refresh(sa)
        saved_id = sa.id
    finally:
        db.close()

    return RedirectResponse(f"{FRONTEND_BASE}/?connected=google&id={saved_id}")

#------------LIST ACCOUNT ------------------------#
@router.get("/accounts")
def list_accounts():
    db = SessionLocal()
    try:
        accounts = db.query(SocialAccount).all()
        return {"accounts": [a.to_dict() for a in accounts]}
    finally:
        db.close()

#-----------DISCONNECT ACCOUNT--------------#
@router.delete("/disconnect/{account_id}")
def disconnect(account_id: int):
    db = SessionLocal()
    try:
        acc = db.query(SocialAccount).filter(SocialAccount.id == account_id).first()
        if not acc:
            return {"error": "Account not found"}
        db.delete(acc)
        db.commit()
        return {"success": True}
    finally:
        db.close()

#-----------------Refresh Google / YouTube token -----------#
@router.get("/refresh/{account_id}")
def refresh_youtube_token(account_id: int):
    db = SessionLocal()
    acc = db.query(SocialAccount).filter(SocialAccount.id == account_id).first()
    if not acc:
        return {"error": "Account not found"}

    if acc.platform != "youtube":
        return {"error": "Only YouTube accounts can refresh token"}

    refresh_token = acc.refresh_token
    if not refresh_token:
        return {"error": "No refresh token available"}

    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }

    r = requests.post(token_url, data=data)
    tok = r.json()

    new_access = tok.get("access_token")
    expires = tok.get("expires_in")

    if not new_access:
        return {"error": "Failed to refresh token", "details": tok}

    acc.access_token = new_access
    if expires:
        acc.token_expires_at = datetime.utcnow() + timedelta(seconds=expires)

    db.commit()
    db.close()

    return {"success": True}
