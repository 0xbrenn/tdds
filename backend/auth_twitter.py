# backend/auth_twitter.py
import os
import requests
import logging
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from supabase_client import supabase
import urllib.parse
import hashlib
import base64
import secrets

load_dotenv()

TWITTER_CLIENT_ID = os.getenv("TWITTER_CLIENT_ID")
TWITTER_CLIENT_SECRET = os.getenv("TWITTER_CLIENT_SECRET")
TWITTER_REDIRECT_URI = os.getenv("TWITTER_REDIRECT_URI")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://badge.iopn.io")
IOPN_TWITTER_USERNAME = os.getenv("IOPN_TWITTER_USERNAME", "IOPn_IO")
IOPN_TWITTER_ID = os.getenv("IOPN_TWITTER_ID", "1838656657332682752")

router = APIRouter()
logger = logging.getLogger(__name__)

def clear_user_cache(email):
    """Clear cache for a specific user"""
    try:
        from main import cache, REDIS_AVAILABLE, status_cache, dashboard_cache
        
        if REDIS_AVAILABLE and cache:
            cache.delete(f"status:{email}")
            cache.delete(f"dashboard:{email}")
            logger.info(f"🗑️ Cleared Redis cache for {email}")
        
        if status_cache:
            status_cache.delete(f"status:{email}")
        if dashboard_cache:
            dashboard_cache.delete(f"dashboard:{email}")
            
    except Exception as e:
        logger.error(f"Failed to clear cache for {email}: {e}")

def generate_code_verifier():
    """Generate PKCE code verifier"""
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')

def generate_code_challenge(verifier):
    """Generate PKCE code challenge"""
    digest = hashlib.sha256(verifier.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')

@router.get("/auth/twitter/login")
async def twitter_login(request: Request):
    """Initiate Twitter OAuth2 flow - STATELESS VERSION"""
    email = request.query_params.get("email", "")
    referral_code = request.query_params.get("ref", "")
    
    # Generate PKCE parameters
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)
    
    # Create state data with all necessary info
    state_data = {
        "email": email,
        "code_verifier": code_verifier,
        "referral_code": referral_code,
        "timestamp": int(datetime.now().timestamp())
    }
    
    # Encode state data as base64 URL-safe string
    state_json = json.dumps(state_data)
    state_bytes = state_json.encode('utf-8')
    state = base64.urlsafe_b64encode(state_bytes).decode('utf-8').rstrip('=')
    
    # Build authorization URL
    params = {
        "response_type": "code",
        "client_id": TWITTER_CLIENT_ID,
        "redirect_uri": TWITTER_REDIRECT_URI,
        "scope": "tweet.read users.read follows.read offline.access",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256"
    }
    
    auth_url = f"https://twitter.com/i/oauth2/authorize?{urllib.parse.urlencode(params)}"
    
    logger.info(f"Generated Twitter auth URL for email: {email}")
    return {"auth_url": auth_url}

@router.get("/auth/twitter/callback")
async def twitter_callback(request: Request):
    """Handle Twitter OAuth2 callback - STATELESS VERSION"""
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    
    logger.info(f"Twitter callback received - code: {'present' if code else 'missing'}, state: {'present' if state else 'missing'}")
    
    if not code or not state:
        logger.error("Missing code or state in callback")
        return RedirectResponse(url=f"{FRONTEND_URL}?platform=twitter&status=error&message=missing_parameters")
    
    # Decode state from base64
    try:
        # Add padding if needed
        padding = 4 - (len(state) % 4)
        if padding != 4:
            state += '=' * padding
        
        # Decode base64
        state_bytes = base64.urlsafe_b64decode(state)
        state_json = state_bytes.decode('utf-8')
        state_data = json.loads(state_json)
        
        # Check timestamp (10 minute expiry)
        current_timestamp = int(datetime.now().timestamp())
        state_timestamp = state_data.get("timestamp", 0)
        
        if current_timestamp - state_timestamp > 600:  # 10 minutes
            logger.warning("State timestamp expired")
            error_msg = "Session expired. Please try logging in again."
            encoded_msg = urllib.parse.quote(error_msg)
            return RedirectResponse(url=f"{FRONTEND_URL}?platform=twitter&status=error&message={encoded_msg}")
        
        # Extract data from state
        email = state_data.get("email", "")
        code_verifier = state_data.get("code_verifier", "")
        referral_code = state_data.get("referral_code", "")
        
        logger.info(f"Decoded state successfully for email: {email}")
        
    except Exception as e:
        logger.error(f"Failed to decode state: {e}")
        error_msg = "Invalid session. Please try logging in again."
        encoded_msg = urllib.parse.quote(error_msg)
        return RedirectResponse(url=f"{FRONTEND_URL}?platform=twitter&status=error&message={encoded_msg}")
    
    # Exchange code for token
    try:
        token_response = requests.post(
            "https://api.twitter.com/2/oauth2/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": TWITTER_REDIRECT_URI,
                "client_id": TWITTER_CLIENT_ID,
                "code_verifier": code_verifier
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {base64.b64encode(f'{TWITTER_CLIENT_ID}:{TWITTER_CLIENT_SECRET}'.encode()).decode()}"
            },
            timeout=30
        )

        if not token_response.ok:
            logger.error(f"Token exchange failed: {token_response.status_code} - {token_response.text}")
            redirect_url = f"{FRONTEND_URL}?platform=twitter&status=error&message=auth_failed"
            if referral_code:
                redirect_url += f"&ref={referral_code}"
            return RedirectResponse(url=redirect_url)

        token_data = token_response.json()
        user_access_token = token_data.get("access_token")

    except Exception as e:
        logger.error(f"Token exchange error: {e}")
        redirect_url = f"{FRONTEND_URL}?platform=twitter&status=error&message=token_exchange_failed"
        if referral_code:
            redirect_url += f"&ref={referral_code}"
        return RedirectResponse(url=redirect_url)

    # Get user info
    try:
        user_response = requests.get(
            "https://api.twitter.com/2/users/me",
            headers={"Authorization": f"Bearer {user_access_token}"},
            timeout=30
        )

        if not user_response.ok:
            logger.error(f"User fetch failed: {user_response.status_code}")
            redirect_url = f"{FRONTEND_URL}?platform=twitter&status=error&message=user_fetch_failed"
            if referral_code:
                redirect_url += f"&ref={referral_code}"
            return RedirectResponse(url=redirect_url)

        user_data = user_response.json()["data"]
        twitter_id = user_data["id"]
        username = user_data["username"]
        
        logger.info(f"✅ Twitter user authenticated: @{username} (ID: {twitter_id})")

    except Exception as e:
        logger.error(f"User fetch error: {e}")
        redirect_url = f"{FRONTEND_URL}?platform=twitter&status=error&message=user_data_error"
        if referral_code:
            redirect_url += f"&ref={referral_code}"
        return RedirectResponse(url=redirect_url)

    # SIMULATED FOLLOWING VERIFICATION
    is_following = True  # Always return true for demo purposes
    
    # Check if this Twitter ID is already linked to another account
    try:
        existing_twitter = supabase.table("badge_users").select("*").eq("twitter_id", twitter_id).execute()
        
        if existing_twitter.data:
            for record in existing_twitter.data:
                if email and record.get("email") != email:
                    # Twitter is linked to a different email
                    other_email = record.get("email", "unknown")
                    error_msg = f"This Twitter account (@{username}) is already linked to another email ({other_email[:3]}***). Each Twitter account can only earn one badge."
                    encoded_msg = urllib.parse.quote(error_msg)
                    redirect_url = f"{FRONTEND_URL}?platform=twitter&status=duplicate&message={encoded_msg}&username={username}"
                    if referral_code:
                        redirect_url += f"&ref={referral_code}"
                    return RedirectResponse(url=redirect_url)
                    
                # Clear any other users with this Twitter ID
                if not email or record.get("email") != email:
                    supabase.table("badge_users").update({
                        "twitter_id": None,
                        "twitter_username": None,
                        "twitter_followed": False
                    }).eq("id", record["id"]).execute()
                    
                    old_email = record.get("email")
                    if old_email:
                        clear_user_cache(old_email)
                        
    except Exception as e:
        logger.error(f"Error checking existing Twitter account: {str(e)}")
    
    # Update user record
    basic_update = {
        "twitter_id": twitter_id,
        "twitter_username": username,
        "twitter_followed": is_following,
    }
    
    # Handle database update
    try:
        if email:
            existing = supabase.table("badge_users").select("*").eq("email", email).execute()
            
            if existing.data:
                user_record = existing.data[0]
                
                if referral_code and not user_record.get("referred_by"):
                    basic_update["referred_by"] = referral_code
                
                result = supabase.table("badge_users").update(basic_update).eq("email", email).execute()
                
                if result.data:
                    logger.info(f"✅ Updated user with email: {email}")
                    clear_user_cache(email)
            else:
                logger.warning(f"No user found with email: {email}")
                redirect_url = f"{FRONTEND_URL}?platform=twitter&status=error&message=email_not_found"
                if referral_code:
                    redirect_url += f"&ref={referral_code}"
                return RedirectResponse(url=redirect_url)
        else:
            # No email - find by Twitter ID
            existing_twitter = supabase.table("badge_users").select("*").eq("twitter_id", twitter_id).execute()
            
            if existing_twitter.data:
                user_record = existing_twitter.data[0]
                result = supabase.table("badge_users").update(basic_update).eq("twitter_id", twitter_id).execute()
                
                if result.data:
                    user_email = user_record.get("email")
                    if user_email:
                        clear_user_cache(user_email)
            else:
                logger.warning(f"No existing user for Twitter ID: {twitter_id}")
                redirect_url = f"{FRONTEND_URL}?platform=twitter&status=error&message=no_account"
                if referral_code:
                    redirect_url += f"&ref={referral_code}"
                return RedirectResponse(url=redirect_url)
                
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        redirect_url = f"{FRONTEND_URL}?platform=twitter&status=error&message=database_error"
        if referral_code:
            redirect_url += f"&ref={referral_code}"
        return RedirectResponse(url=redirect_url)

    # Success redirect
    redirect_url = f"{FRONTEND_URL}?platform=twitter&status=success&username={username}"
    if referral_code:
        redirect_url += f"&ref={referral_code}"
    
    return RedirectResponse(url=redirect_url)

@router.get("/auth/twitter/status/{twitter_id}")
async def twitter_status(twitter_id: str):
    """Check Twitter user badge status"""
    result = supabase.table("badge_users").select("*").eq("twitter_id", twitter_id).execute()
    
    if result.data:
        user = result.data[0]
        return {
            "has_badge": user.get("badge_issued", False),
            "twitter_verified": user.get("twitter_followed", False),
            "twitter_username": user.get("twitter_username"),
            "email": user.get("email"),
            "telegram_verified": bool(user.get("telegram_id"))
        }
    
    return {
        "has_badge": False,
        "twitter_verified": False,
        "twitter_username": None
    }