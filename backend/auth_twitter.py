# backend/auth_twitter.py
import os
import requests
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

# Store state and code verifiers temporarily
auth_states = {}

def generate_code_verifier():
    """Generate PKCE code verifier"""
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')

def generate_code_challenge(verifier):
    """Generate PKCE code challenge"""
    digest = hashlib.sha256(verifier.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')




@router.get("/auth/twitter/login")
async def twitter_login(request: Request):
    """Initiate Twitter OAuth2 flow"""
    email = request.query_params.get("email", "")
    referral_code = request.query_params.get("ref", "")
    
    # Generate PKCE parameters
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)
    state = secrets.token_urlsafe(32)
    
    # Store state with email, verifier, and referral code
    auth_states[state] = {
        "email": email,
        "code_verifier": code_verifier,
        "referral_code": referral_code
    }
    
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
    return {"auth_url": auth_url}





@router.get("/auth/twitter/callback")
async def twitter_callback(request: Request):
    """Handle Twitter OAuth2 callback"""
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    
    if not code or not state:
        return RedirectResponse(url=f"{FRONTEND_URL}?platform=twitter&status=error")
    
    # Retrieve stored state
    if state not in auth_states:
        return RedirectResponse(url=f"{FRONTEND_URL}?platform=twitter&status=error&message=invalid_state")
    
    stored_state = auth_states[state]
    email = stored_state.get("email")
    code_verifier = stored_state.get("code_verifier")
    referral_code = stored_state.get("referral_code", "")  # GET REFERRAL CODE
    
    # Clean up state
    del auth_states[state]
    
    # Exchange code for token
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
        }
    )

    if not token_response.ok:
        print(f"Token exchange failed: {token_response.status_code} - {token_response.text}")
        redirect_url = f"{FRONTEND_URL}?platform=twitter&status=error"
        if referral_code:
            redirect_url += f"&ref={referral_code}"
        return RedirectResponse(url=redirect_url)

    token_data = token_response.json()
    user_access_token = token_data.get("access_token")

    # Get user info
    user_response = requests.get(
        "https://api.twitter.com/2/users/me",
        headers={"Authorization": f"Bearer {user_access_token}"}
    )

    if not user_response.ok:
        print(f"User fetch failed: {user_response.status_code} - {user_response.text}")
        redirect_url = f"{FRONTEND_URL}?error=user_fetch_failed"
        if referral_code:
            redirect_url += f"&ref={referral_code}"
        return RedirectResponse(url=redirect_url)

    user_data = user_response.json()["data"]
    twitter_id = user_data["id"]
    username = user_data["username"]
    
    print(f"✅ Twitter user authenticated: @{username} (ID: {twitter_id})")

    # SIMULATED FOLLOWING VERIFICATION
    is_following = True  # Always return true for demo purposes
    
    print(f"🎭 SIMULATED: User @{username} is following @{IOPN_TWITTER_USERNAME}")
    
    # FIXED: Check if this Twitter ID is already linked to another account
    try:
        existing_twitter = supabase.table("badge_users").select("*").eq("twitter_id", twitter_id).execute()
        
        if existing_twitter.data:
            # Twitter ID exists - check if it's the same user
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
            # DON'T clear twitter_id from other users - show error instead
            existing_twitter_users = supabase.table("badge_users").select("*").eq("twitter_id", twitter_id).execute()
            if existing_twitter_users.data:
                for record in existing_twitter_users.data:
                    if record.get("email") != email:
                        # Don't allow overwriting
                        other_email = record.get("email", "unknown")
                        error_msg = f"This Twitter account is already linked to {other_email[:3]}***. Use a different Twitter account."
                        encoded_msg = urllib.parse.quote(error_msg)
                        redirect_url = f"{FRONTEND_URL}?platform=twitter&status=duplicate&message={encoded_msg}"
                        if referral_code:
                            redirect_url += f"&ref={referral_code}"
                        return RedirectResponse(url=redirect_url)
            
            # Check if user exists with this email
            existing = supabase.table("badge_users").select("*").eq("email", email).execute()
            
            if existing.data:
                # Update existing record
                supabase.table("badge_users").update(basic_update).eq("email", email).execute()
                print(f"✅ Updated existing user with email: {email}")
            else:
                # Email should exist from registration - don't create new record
                print(f"⚠️ No user found with email: {email}")
                redirect_url = f"{FRONTEND_URL}?platform=twitter&status=error&message=user_not_found"
                if referral_code:
                    redirect_url += f"&ref={referral_code}"
                return RedirectResponse(url=redirect_url)
        else:
            # No email - user should register with email first
            error_msg = "Please complete email verification first"
            encoded_msg = urllib.parse.quote(error_msg)
            redirect_url = f"{FRONTEND_URL}?platform=twitter&status=error&message={encoded_msg}"
            if referral_code:
                redirect_url += f"&ref={referral_code}"
            return RedirectResponse(url=redirect_url)
                
    except Exception as e:
        print(f"❌ Database error: {str(e)}")
        if "duplicate key" in str(e) and "twitter_id" in str(e):
            error_msg = f"This Twitter account (@{username}) is already linked to another account"
            encoded_msg = urllib.parse.quote(error_msg)
            redirect_url = f"{FRONTEND_URL}?platform=twitter&status=duplicate&message={encoded_msg}&username={username}"
            if referral_code:
                redirect_url += f"&ref={referral_code}"
            return RedirectResponse(url=redirect_url)
        else:
            redirect_url = f"{FRONTEND_URL}?platform=twitter&status=error"
            if referral_code:
                redirect_url += f"&ref={referral_code}"
            return RedirectResponse(url=redirect_url)
    
    # Always redirect with success status since we're simulating
    redirect_url = f"{FRONTEND_URL}?platform=twitter&status=success&username={username}"
    if referral_code:
        redirect_url += f"&ref={referral_code}"
    
    return RedirectResponse(url=redirect_url)


    
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