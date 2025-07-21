# backend/auth_discord.py
import os
import requests
import logging
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
logger = logging.getLogger(__name__)

def clear_user_cache(email):
    """Clear cache for a specific user"""
    try:
        # Import cache utilities
        from main import cache, REDIS_AVAILABLE, status_cache, dashboard_cache
        
        if REDIS_AVAILABLE and cache:
            # Clear Redis cache
            cache.delete(f"status:{email}")
            cache.delete(f"dashboard:{email}")
            logger.info(f"🗑️ Cleared Redis cache for {email}")
        
        # Also clear in-memory cache if available
        if status_cache:
            status_cache.delete(f"status:{email}")
        if dashboard_cache:
            dashboard_cache.delete(f"dashboard:{email}")
            
    except Exception as e:
        logger.error(f"Failed to clear cache for {email}: {e}")

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

    # If email is provided, check if user exists
    if email:
        existing_user = supabase.table("badge_users").select("*").eq("email", email).execute()
        
        if existing_user.data:
            # Update existing user
            user_record = existing_user.data[0]
            
            # Check if Discord ID is already linked to another account
            discord_check = supabase.table("badge_users").select("*").eq("discord_id", discord_id).execute()
            
            if discord_check.data:
                for record in discord_check.data:
                    if record.get("email") != email:
                        # Clear Discord from other accounts
                        supabase.table("badge_users").update({
                            "discord_id": None,
                            "discord_username": None,
                            "discord_joined": False
                        }).eq("id", record["id"]).execute()
                        
                        # Clear cache for the old user
                        old_email = record.get("email")
                        if old_email:
                            clear_user_cache(old_email)
            
            # Update with Discord info
            update_data = {
                "discord_id": discord_id,
                "discord_username": global_name,
                "discord_joined": is_member  # Set based on guild membership
            }
            
            # Add referral code if provided and user doesn't have one
            if referral_code and not user_record.get("referred_by"):
                update_data["referred_by"] = referral_code
            
            result = supabase.table("badge_users").update(update_data).eq("email", email).execute()
            
            if result.data:
                print(f"✅ Updated user record for {email} with Discord ID {discord_id}")
                # CLEAR THE CACHE after successful update
                clear_user_cache(email)
            else:
                print(f"❌ Failed to update user record for {email}")
        else:
            print(f"⚠️ User with email {email} not found. They should register first.")
            redirect_url = f"{FRONTEND_URL}?platform=discord&status=error&message=email_not_found"
            if referral_code:
                redirect_url += f"&ref={referral_code}"
            return RedirectResponse(url=redirect_url)
    else:
        # No email provided - check if Discord ID exists anywhere
        existing_discord = supabase.table("badge_users").select("*").eq("discord_id", discord_id).execute()
        
        if existing_discord.data:
            # Update their guild membership status
            user_record = existing_discord.data[0]
            result = supabase.table("badge_users").update({
                "discord_joined": is_member,
                "discord_username": global_name
            }).eq("discord_id", discord_id).execute()
            
            if result.data:
                # Clear cache for this user
                user_email = user_record.get("email")
                if user_email:
                    clear_user_cache(user_email)
        else:
            print(f"⚠️ Discord user {discord_id} not linked to any account")

    # Determine redirect status
    if is_member:
        redirect_url = f"{FRONTEND_URL}?platform=discord&status=success"
    else:
        redirect_url = f"{FRONTEND_URL}?platform=discord&status=not_in_server&invite={DISCORD_INVITE_LINK}"
    
    # Always preserve referral code in redirect
    if referral_code:
        redirect_url += f"&ref={referral_code}"
    
    return RedirectResponse(url=redirect_url)

@router.get("/status/{discord_id}")
async def get_discord_status(discord_id: str):
    """Check Discord verification status"""
    result = supabase.table("badge_users").select("*").eq("discord_id", discord_id).execute()
    
    if result.data:
        user = result.data[0]
        return {
            "verified": True,
            "discord_id": discord_id,
            "username": user.get("discord_username"),
            "discord_joined": user.get("discord_joined", False),
            "badge_issued": user.get("badge_issued", False)
        }
    
    return {
        "verified": False,
        "discord_id": discord_id,
        "discord_joined": False,
        "badge_issued": False
    }