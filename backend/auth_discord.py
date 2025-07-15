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
        return RedirectResponse(url=f"{FRONTEND_URL}?error=token_exchange_failed")

    access_token = token_response.json().get("access_token")

    # Get user info
    user_response = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    if not user_response.ok:
        return RedirectResponse(url=f"{FRONTEND_URL}?error=user_fetch_failed")

    user_data = user_response.json()
    discord_id = user_data["id"]
    username = user_data.get("username", "")
    global_name = user_data.get("global_name", username)

    # Check if user is in IOPn Discord server
    guilds_response = requests.get(
        "https://discord.com/api/users/@me/guilds",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    is_member = False
    if guilds_response.ok:
        guilds = guilds_response.json()
        for guild in guilds:
            if guild["id"] == IOPN_GUILD_ID:
                is_member = True
                break

    # If bot token available, double-check membership
    if DISCORD_BOT_TOKEN and not is_member:
        member_check = requests.get(
            f"https://discord.com/api/guilds/{IOPN_GUILD_ID}/members/{discord_id}",
            headers={"Authorization": f"Bot {DISCORD_BOT_TOKEN}"}
        )
        is_member = member_check.ok

    # Update or create user record
    if state:  # If email was provided
        existing = supabase.table("badge_users").select("*").eq("email", state).execute()
        
        if existing.data:
            # Update existing record
            supabase.table("badge_users").update({
                "discord_id": discord_id,
                "discord_username": global_name or username,
                "discord_joined": is_member
            }).eq("email", state).execute()
        else:
            # Create new record
            supabase.table("badge_users").insert({
                "email": state,
                "discord_id": discord_id,
                "discord_username": global_name or username,
                "discord_joined": is_member,
                "email_added": True
            }).execute()
    else:
        # No email provided, check if discord_id exists
        existing = supabase.table("badge_users").select("*").eq("discord_id", discord_id).execute()
        
        if existing.data:
            supabase.table("badge_users").update({
                "discord_joined": is_member,
                "discord_username": global_name or username
            }).eq("discord_id", discord_id).execute()
        else:
            # Create new record with just Discord info
            supabase.table("badge_users").insert({
                "discord_id": discord_id,
                "discord_username": global_name or username,
                "discord_joined": is_member
            }).execute()

    # Redirect back to frontend with status
    if is_member:
        return RedirectResponse(url=f"{FRONTEND_URL}?platform=discord&status=success&username={urllib.parse.quote(global_name or username)}")
    else:
        invite_link = os.getenv("DISCORD_INVITE_LINK", "discord.gg/iopn")
        return RedirectResponse(url=f"{FRONTEND_URL}?platform=discord&status=not_member&invite={invite_link}")