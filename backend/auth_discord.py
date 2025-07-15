# backend/auth_discord.py
import os
import requests
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from supabase_client import supabase
import urllib.parse

load_dotenv()

DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
IOPN_GUILD_ID = os.getenv("IOPN_DISCORD_GUILD_ID")
DISCORD_INVITE_LINK = os.getenv("DISCORD_INVITE_LINK", "discord.gg/iopn")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

router = APIRouter()

@router.get("/auth/discord/login")
async def discord_login(request: Request):
    """Initiate Discord OAuth2 flow"""
    # Get email from query params to link accounts
    email = request.query_params.get("email", "")
    
    # Discord OAuth2 URL
    params = {
        "client_id": DISCORD_CLIENT_ID,
        "redirect_uri": DISCORD_REDIRECT_URI,
        "response_type": "code",
        "scope": "identify guilds",
        "state": email  # Pass email through state parameter
    }
    
    auth_url = f"https://discord.com/api/oauth2/authorize?{urllib.parse.urlencode(params)}"
    return {"auth_url": auth_url}

@router.get("/auth/discord/callback")
async def discord_callback(request: Request):
    """Handle Discord OAuth2 callback"""
    code = request.query_params.get("code")
    state = request.query_params.get("state", "")  # Email passed through state
    
    if not code:
        return RedirectResponse(url=f"{FRONTEND_URL}?error=no_code")

    # Exchange code for token
    token_response = requests.post(
        "https://discord.com/api/oauth2/token",
        data={
            "client_id": DISCORD_CLIENT_ID,
            "client_secret": DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": DISCORD_REDIRECT_URI,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    if not token_response.ok:
        print(f"Token exchange failed: {token_response.status_code} - {token_response.text}")
        return RedirectResponse(url=f"{FRONTEND_URL}?platform=discord&status=error&message=token_exchange_failed")

    access_token = token_response.json().get("access_token")

    # Get user info
    user_response = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    if not user_response.ok:
        print(f"User fetch failed: {user_response.status_code} - {user_response.text}")
        return RedirectResponse(url=f"{FRONTEND_URL}?platform=discord&status=error&message=user_fetch_failed")

    user_data = user_response.json()
    discord_id = user_data["id"]
    username = user_data.get("username", "")
    global_name = user_data.get("global_name", username)
    
    print(f"✅ Discord user authenticated: {global_name} (ID: {discord_id})")

    # Check if user is in IOPn Discord server
    guilds_response = requests.get(
        "https://discord.com/api/users/@me/guilds",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    is_member = False
    if guilds_response.ok:
        guilds = guilds_response.json()
        print(f"User is in {len(guilds)} guilds")
        for guild in guilds:
            if guild["id"] == IOPN_GUILD_ID:
                is_member = True
                print(f"✅ User is a member of IOPn Discord!")
                break

    # If bot token available, double-check membership
    if DISCORD_BOT_TOKEN and not is_member:
        print("Double-checking with bot token...")
        member_check = requests.get(
            f"https://discord.com/api/guilds/{IOPN_GUILD_ID}/members/{discord_id}",
            headers={"Authorization": f"Bot {DISCORD_BOT_TOKEN}"}
        )
        is_member = member_check.ok
        if is_member:
            print("✅ Confirmed via bot token")
        else:
            print("❌ Not a member (bot check)")

    # FIXED: Check if Discord ID is already linked to another account
    try:
        existing_discord = supabase.table("badge_users").select("*").eq("discord_id", discord_id).execute()
        
        if existing_discord.data:
            # Discord ID exists - check if it's the same user
            for record in existing_discord.data:
                if state and record.get("email") != state:
                    # Discord is linked to a different email
                    other_email = record.get("email", "unknown")
                    error_msg = f"This Discord account (@{global_name or username}) is already linked to another email ({other_email[:3]}***). Each Discord account can only earn one badge."
                    encoded_msg = urllib.parse.quote(error_msg)
                    return RedirectResponse(
                        url=f"{FRONTEND_URL}?platform=discord&status=duplicate&message={encoded_msg}&username={global_name or username}"
                    )
    except Exception as e:
        print(f"Error checking existing Discord account: {str(e)}")

    # Update or create user record
    try:
        if state:  # If email was provided
            # DON'T clear discord_id from other users - show error instead
            existing_discord_users = supabase.table("badge_users").select("*").eq("discord_id", discord_id).execute()
            if existing_discord_users.data:
                for record in existing_discord_users.data:
                    if record.get("email") != state:
                        # Don't allow overwriting
                        other_email = record.get("email", "unknown")
                        error_msg = f"This Discord account is already linked to {other_email[:3]}***. Use a different Discord account."
                        encoded_msg = urllib.parse.quote(error_msg)
                        return RedirectResponse(
                            url=f"{FRONTEND_URL}?platform=discord&status=duplicate&message={encoded_msg}"
                        )
            
            # Check if email user exists
            existing = supabase.table("badge_users").select("*").eq("email", state).execute()
            
            if existing.data:
                # Update existing record
                supabase.table("badge_users").update({
                    "discord_id": discord_id,
                    "discord_username": global_name or username,
                    "discord_joined": is_member
                }).eq("email", state).execute()
                print(f"✅ Updated existing user with email: {state}")
            else:
                # Email should exist from registration - don't create new record
                print(f"⚠️ No user found with email: {state}")
                return RedirectResponse(url=f"{FRONTEND_URL}?platform=discord&status=error&message=user_not_found")
        else:
            # No email provided - user should register with email first
            error_msg = "Please complete email verification first"
            encoded_msg = urllib.parse.quote(error_msg)
            return RedirectResponse(
                url=f"{FRONTEND_URL}?platform=discord&status=error&message={encoded_msg}"
            )
            
    except Exception as e:
        print(f"❌ Database error: {str(e)}")
        return RedirectResponse(url=f"{FRONTEND_URL}?platform=discord&status=error")

    # Redirect back to frontend with status
    if is_member:
        return RedirectResponse(
            url=f"{FRONTEND_URL}?platform=discord&status=success&username={global_name or username}"
        )
    else:
        error_msg = f"Please join the IOPn Discord server first. Invite link: {DISCORD_INVITE_LINK}"
        encoded_msg = urllib.parse.quote(error_msg)
        return RedirectResponse(
            url=f"{FRONTEND_URL}?platform=discord&status=not_member&message={encoded_msg}&invite={DISCORD_INVITE_LINK}"
        )

@router.get("/status/{discord_id}")
async def discord_status(discord_id: str):
    """Check badge status by Discord ID"""
    result = supabase.table("badge_users").select("*").eq("discord_id", discord_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = result.data[0]
    return {
        "discord_id": discord_id,
        "username": user.get("discord_username"),
        "discord_joined": user.get("discord_joined", False),
        "badge_issued": user.get("badge_issued", False),
        "tasks_completed": {
            "email": user.get("email_added", False),
            "telegram": user.get("telegram_joined", False),
            "discord": user.get("discord_joined", False),
            "twitter": user.get("twitter_followed", False)
        }
    }