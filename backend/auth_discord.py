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
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://badge.iopn.io")

router = APIRouter()

@router.get("/auth/discord/login")
async def discord_login(request: Request):
    """Initiate Discord OAuth2 flow"""
    email = request.query_params.get("email", "")
    referral_code = request.query_params.get("ref", "")
    
    # Combine email and referral code in state
    state = f"{email}|{referral_code}"
    
    # Discord OAuth2 URL
    params = {
        "client_id": DISCORD_CLIENT_ID,
        "redirect_uri": DISCORD_REDIRECT_URI,
        "response_type": "code",
        "scope": "identify guilds",
        "state": state
    }
    
    auth_url = f"https://discord.com/api/oauth2/authorize?{urllib.parse.urlencode(params)}"
    return {"auth_url": auth_url}

@router.get("/auth/discord/callback")
async def discord_callback(request: Request):
    """Handle Discord OAuth2 callback"""
    code = request.query_params.get("code")
    state = request.query_params.get("state", "")

    # Extract email and referral code from state
    state_parts = state.split("|")
    email = state_parts[0] if len(state_parts) > 0 else ""
    referral_code = state_parts[1] if len(state_parts) > 1 else ""

    if not code:
        redirect_url = f"{FRONTEND_URL}?platform=discord&status=error"
        if referral_code:
            redirect_url += f"&ref={referral_code}"
        return RedirectResponse(url=redirect_url)
        
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
        redirect_url = f"{FRONTEND_URL}?platform=discord&status=error&message=token_exchange_failed"
        if referral_code:
            redirect_url += f"&ref={referral_code}"
        return RedirectResponse(url=redirect_url)

    access_token = token_response.json().get("access_token")

    # Get user info
    user_response = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    if not user_response.ok:
        print(f"User fetch failed: {user_response.status_code} - {user_response.text}")
        redirect_url = f"{FRONTEND_URL}?platform=discord&status=error&message=user_fetch_failed"
        if referral_code:
            redirect_url += f"&ref={referral_code}"
        return RedirectResponse(url=redirect_url)

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

    # Check if Discord ID is already linked to another account
    try:
        existing_discord = supabase.table("badge_users").select("*").eq("discord_id", discord_id).execute()
        
        if existing_discord.data:
            # Discord ID exists - check if it's the same user
            for record in existing_discord.data:
                if email and record.get("email") != email:
                    # Discord is linked to a different email
                    other_email = record.get("email", "unknown")
                    error_msg = f"This Discord account (@{global_name or username}) is already linked to another email ({other_email[:3]}***). Each Discord account can only earn one badge."
                    encoded_msg = urllib.parse.quote(error_msg)
                    redirect_url = f"{FRONTEND_URL}?platform=discord&status=duplicate&message={encoded_msg}&username={global_name or username}"
                    if referral_code:
                        redirect_url += f"&ref={referral_code}"
                    return RedirectResponse(url=redirect_url)
    except Exception as e:
        print(f"Error checking existing Discord account: {str(e)}")

    # Update or create user record
    try:
        if email:
            # Check if email user exists
            existing = supabase.table("badge_users").select("*").eq("email", email).execute()
            
            if existing.data:
                # Update existing record
                supabase.table("badge_users").update({
                    "discord_id": discord_id,
                    "discord_username": global_name or username,
                    "discord_joined": is_member
                }).eq("email", email).execute()
                print(f"✅ Updated existing user with email: {email}")
            else:
                # Email should exist from registration - don't create new record
                print(f"⚠️ No user found with email: {email}")
                redirect_url = f"{FRONTEND_URL}?platform=discord&status=error&message=user_not_found"
                if referral_code:
                    redirect_url += f"&ref={referral_code}"
                return RedirectResponse(url=redirect_url)
        else:
            # No email provided - user should register with email first
            error_msg = "Please complete email verification first"
            encoded_msg = urllib.parse.quote(error_msg)
            redirect_url = f"{FRONTEND_URL}?platform=discord&status=error&message={encoded_msg}"
            if referral_code:
                redirect_url += f"&ref={referral_code}"
            return RedirectResponse(url=redirect_url)
            
    except Exception as e:
        print(f"❌ Database error: {str(e)}")
        redirect_url = f"{FRONTEND_URL}?platform=discord&status=error"
        if referral_code:
            redirect_url += f"&ref={referral_code}"
        return RedirectResponse(url=redirect_url)

    # Redirect back to frontend with status
    if is_member:
        redirect_url = f"{FRONTEND_URL}?platform=discord&status=success&username={global_name or username}"
        if referral_code:
            redirect_url += f"&ref={referral_code}"
        return RedirectResponse(url=redirect_url)
    else:
        error_msg = f"Please join the IOPn Discord server first. Invite link: {DISCORD_INVITE_LINK}"
        encoded_msg = urllib.parse.quote(error_msg)
        redirect_url = f"{FRONTEND_URL}?platform=discord&status=not_member&message={encoded_msg}&invite={DISCORD_INVITE_LINK}"
        if referral_code:
            redirect_url += f"&ref={referral_code}"
        return RedirectResponse(url=redirect_url)

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