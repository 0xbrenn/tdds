# backend/auth_twitter.py
import os
import base64
import requests
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from supabase_client import supabase
import urllib.parse
import secrets
from datetime import datetime, timedelta

load_dotenv()

router = APIRouter()

TWITTER_CLIENT_ID = os.getenv("TWITTER_CLIENT_ID")
TWITTER_CLIENT_SECRET = os.getenv("TWITTER_CLIENT_SECRET")
TWITTER_REDIRECT_URI = os.getenv("TWITTER_REDIRECT_URI")
IOPN_TWITTER_ID = os.getenv("IOPN_TWITTER_ID") 
IOPN_TWITTER_USERNAME = os.getenv("IOPN_TWITTER_USERNAME", "IOPn_io")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

AUTH_URL = "https://twitter.com/i/oauth2/authorize"
TOKEN_URL = "https://api.twitter.com/2/oauth2/token"
USERINFO_URL = "https://api.twitter.com/2/users/me"

# OAuth 2.0 with PKCE
SCOPES = "tweet.read users.read follows.read"

# Store code verifiers temporarily (in production, use Redis or similar)
code_verifiers = {}

@router.get("/auth/twitter/login")
async def twitter_login(request: Request):
    """Initiate Twitter OAuth2 flow"""
    email = request.query_params.get("email", "")
    
    # Generate code verifier and challenge for PKCE
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    code_challenge = code_verifier  # For simplicity, using plain method
    
    # Store code verifier with email as key
    state = f"{email}:{secrets.token_urlsafe(16)}"
    code_verifiers[state] = code_verifier
    
    params = {
        "response_type": "code",
        "client_id": TWITTER_CLIENT_ID,
        "redirect_uri": TWITTER_REDIRECT_URI,
        "scope": SCOPES,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "plain"
    }
    
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
    return {"auth_url": auth_url}

@router.get("/auth/twitter/callback")
async def twitter_callback(request: Request):
    """Handle Twitter OAuth2 callback with simulated following verification"""
    code = request.query_params.get("code")
    state = request.query_params.get("state", "")
    
    if not code:
        return RedirectResponse(url=f"{FRONTEND_URL}?error=no_code")
    
    # Extract email from state
    email = state.split(":")[0] if ":" in state else ""
    
    # Get code verifier
    code_verifier = code_verifiers.pop(state, "challenge")  # Fallback for testing
    
    # Exchange code for token
    basic_auth = base64.b64encode(f"{TWITTER_CLIENT_ID}:{TWITTER_CLIENT_SECRET}".encode()).decode()
    
    token_response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": TWITTER_REDIRECT_URI,
            "code_verifier": code_verifier
        },
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {basic_auth}"
        }
    )

    if not token_response.ok:
        print(f"Token exchange failed: {token_response.status_code} - {token_response.text}")
        return RedirectResponse(url=f"{FRONTEND_URL}?error=token_exchange_failed")

    # Get the USER's access token
    user_access_token = token_response.json()["access_token"]
    print(f"✅ Got user access token")

    # Get user info
    user_response = requests.get(
        USERINFO_URL,
        headers={"Authorization": f"Bearer {user_access_token}"}
    )

    if not user_response.ok:
        print(f"User fetch failed: {user_response.status_code} - {user_response.text}")
        return RedirectResponse(url=f"{FRONTEND_URL}?error=user_fetch_failed")

    user_data = user_response.json()["data"]
    twitter_id = user_data["id"]
    username = user_data["username"]
    
    print(f"✅ Twitter user authenticated: @{username} (ID: {twitter_id})")

    # SIMULATED FOLLOWING VERIFICATION
    is_following = True  # Always return true for demo purposes
    
    print(f"🎭 SIMULATED: User @{username} is following @{IOPN_TWITTER_USERNAME}")
    
    # Check if this Twitter ID is already linked to another account
    try:
        existing_twitter = supabase.table("badge_users").select("*").eq("twitter_id", twitter_id).execute()
        
        if existing_twitter.data:
            existing_user = existing_twitter.data[0]
            existing_email = existing_user.get("email", "Unknown")
            
            # Check if it's the same user (by email)
            if email and existing_email != email:
                # Twitter account is linked to a different email
                error_msg = f"This Twitter account (@{username}) is already linked to another account"
                encoded_msg = urllib.parse.quote(error_msg)
                return RedirectResponse(
                    url=f"{FRONTEND_URL}?platform=twitter&status=duplicate&message={encoded_msg}&username={username}"
                )
            elif not email:
                # No email provided, can't verify if it's the same user
                error_msg = f"This Twitter account (@{username}) is already registered"
                encoded_msg = urllib.parse.quote(error_msg)
                return RedirectResponse(
                    url=f"{FRONTEND_URL}?platform=twitter&status=duplicate&message={encoded_msg}&username={username}"
                )
    except Exception as e:
        print(f"Error checking existing Twitter account: {str(e)}")
    
    # Update or create user record
    basic_update = {
        "twitter_id": twitter_id,
        "twitter_username": username,
        "twitter_followed": is_following,
    }
    
    # Handle database update
    try:
        if email:
            # Check if user exists with this email
            existing = supabase.table("badge_users").select("*").eq("email", email).execute()
            
            if existing.data:
                # Update existing record
                supabase.table("badge_users").update(basic_update).eq("email", email).execute()
                print(f"✅ Updated existing user with email: {email}")
            else:
                # Create new record with email
                basic_update["email"] = email
                basic_update["email_added"] = True
                supabase.table("badge_users").insert(basic_update).execute()
                print(f"✅ Created new user with email: {email}")
        else:
            # No email - shouldn't happen in normal flow
            error_msg = "Please complete email verification first"
            encoded_msg = urllib.parse.quote(error_msg)
            return RedirectResponse(
                url=f"{FRONTEND_URL}?platform=twitter&status=error&message={encoded_msg}"
            )
                
    except Exception as e:
        print(f"❌ Database error: {str(e)}")
        if "duplicate key" in str(e) and "twitter_id" in str(e):
            error_msg = f"This Twitter account (@{username}) is already linked to another account"
            encoded_msg = urllib.parse.quote(error_msg)
            return RedirectResponse(
                url=f"{FRONTEND_URL}?platform=twitter&status=duplicate&message={encoded_msg}&username={username}"
            )
        else:
            return RedirectResponse(url=f"{FRONTEND_URL}?platform=twitter&status=error")
    
    # Always redirect with success status since we're simulating
    return RedirectResponse(url=f"{FRONTEND_URL}?platform=twitter&status=success&username={username}")
@router.get("/auth/twitter/status/{twitter_id}")
async def twitter_status(twitter_id: str):
    """Check badge status by Twitter ID"""
    result = supabase.table("badge_users").select("*").eq("twitter_id", twitter_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = result.data[0]
    return {
        "twitter_id": twitter_id,
        "username": user.get("twitter_username"),
        "twitter_followed": user.get("twitter_followed", False),
        "badge_issued": user.get("badge_issued", False),
        "tasks_completed": {
            "email": user.get("email_added", False),
            "telegram": user.get("telegram_joined", False),
            "discord": user.get("discord_joined", False),
            "twitter": user.get("twitter_followed", False)
        }
    }