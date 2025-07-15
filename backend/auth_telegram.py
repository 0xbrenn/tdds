import os
import hashlib
import hmac
from fastapi import APIRouter, Request, HTTPException, Body
from supabase_client import supabase
from dotenv import load_dotenv

load_dotenv()
router = APIRouter()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def verify_telegram_hash(data: dict, bot_token: str) -> bool:
    check_hash = data.pop('hash', None)
    payload = '\n'.join([f'{k}={v}' for k, v in sorted(data.items())])
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    calculated_hash = hmac.new(secret_key, payload.encode(), hashlib.sha256).hexdigest()
    return calculated_hash == check_hash

@router.post("/")
async def telegram_auth(request: Request):
    data = await request.json()

    # if not verify_telegram_hash(data.copy(), BOT_TOKEN):
    #     raise HTTPException(status_code=403, detail="Invalid Telegram login")

    telegram_id = int(data["id"])
    username = data.get("username", "")
    first_name = data.get("first_name", "")
    last_name = data.get("last_name", "")

    existing = supabase.table("badge_users").select("id").eq("telegram_id", telegram_id).execute()
    if not existing.data:
        supabase.table("badge_users").insert({
            "telegram_id": telegram_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "badge_issued": False
        }).execute()

    supabase.table("badge_users").update({"telegram_joined": True}).eq("telegram_id", telegram_id).execute()
    return {"status": "ok", "telegram_id": telegram_id}


@router.post("/link-simple")
async def link_telegram_simple(request: Request):
    """Simple endpoint to link Telegram to existing email user"""
    data = await request.json()
    email = data.get("email")
    telegram_id = data.get("telegram_id")
    telegram_username = data.get("telegram_username", "")
    
    print(f"🔗 Linking Telegram {telegram_id} to email {email}")
    
    if not email:
        raise HTTPException(status_code=400, detail="Email required")
    
    # First, check if this telegram_id already exists elsewhere
    existing_telegram = supabase.table("badge_users").select("*").eq("telegram_id", telegram_id).execute()
    
    if existing_telegram.data:
        # If it exists and it's not the same email, we need to remove it first
        existing_record = existing_telegram.data[0]
        if existing_record.get("email") != email:
            print(f"⚠️ Telegram ID already exists for different user, removing...")
            # Delete the old record (or you could just clear the telegram_id)
            supabase.table("badge_users").update({
                "telegram_id": None,
                "telegram_username": None,
                "telegram_joined": False
            }).eq("telegram_id", telegram_id).execute()
    
    # Now update the user's telegram status
    result = supabase.table("badge_users").update({
        "telegram_id": telegram_id,
        "telegram_username": telegram_username,
        "telegram_joined": True
    }).eq("email", email).execute()
    
    print(f"📝 Update result: {result.data}")
    
    if result.data:
        return {"status": "success"}
    else:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Add these to auth_telegram.py

@router.post("/link-with-channel-check")
async def link_with_channel_check(request: Request):
    """Link Telegram to email with channel membership check"""
    data = await request.json()
    email = data.get("email")
    telegram_id = data.get("telegram_id")
    telegram_username = data.get("telegram_username", "")
    is_channel_member = data.get("is_channel_member", False)
    
    print(f"🔗 Linking Telegram {telegram_id} to email {email} (channel member: {is_channel_member})")
    
    if not email:
        raise HTTPException(status_code=400, detail="Email required")
    
    # Clear any existing telegram_id first
    existing_telegram = supabase.table("badge_users").select("*").eq("telegram_id", telegram_id).execute()
    if existing_telegram.data:
        existing_record = existing_telegram.data[0]
        if existing_record.get("email") != email:
            supabase.table("badge_users").update({
                "telegram_id": None,
                "telegram_username": None,
                "telegram_joined": False
            }).eq("telegram_id", telegram_id).execute()
    
    # Update user - only set telegram_joined=True if they're in the channel
    result = supabase.table("badge_users").update({
        "telegram_id": telegram_id,
        "telegram_username": telegram_username,
        "telegram_joined": is_channel_member  # Only true if in channel!
    }).eq("email", email).execute()
    
    if result.data:
        return {"status": "success", "is_member": is_channel_member}
    else:
        raise HTTPException(status_code=404, detail="User not found")

@router.post("/update-channel-status")
async def update_channel_status(request: Request):
    """Update channel membership status after user joins"""
    data = await request.json()
    telegram_id = str(data.get("telegram_id"))
    is_channel_member = data.get("is_channel_member", False)
    
    if not telegram_id:
        raise HTTPException(status_code=400, detail="Telegram ID required")
    
    result = supabase.table("badge_users").update({
        "telegram_joined": is_channel_member
    }).eq("telegram_id", telegram_id).execute()
    
    if result.data:
        return {"status": "success"}
    else:
        raise HTTPException(status_code=404, detail="User not found")
    
    
@router.get("/badge/status/{telegram_id}")
async def badge_status(telegram_id: int):
    result = supabase.table("badge_users").select("badge_issued").eq("telegram_id", telegram_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    return {"badge_issued": result.data[0]["badge_issued"]}

@router.post("/badge/issue")
async def issue_badge(telegram_id: int = Body(..., embed=True)):
    result = supabase.table("badge_users").update({"badge_issued": True}).eq("telegram_id", telegram_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "issued", "telegram_id": telegram_id}

@router.post("/link-account")
async def link_accounts(telegram_id: int = Body(...), twitter_id: str = Body(...)):
    tg_user = supabase.table("badge_users").select("id").eq("telegram_id", telegram_id).execute()
    tw_user = supabase.table("badge_users").select("id").eq("twitter_id", twitter_id).execute()
 
    if not tg_user.data or not tw_user.data:
        raise HTTPException(status_code=404, detail="User(s) not found")

    supabase.table("badge_users").delete().eq("id", tw_user.data[0]["id"]).execute()
    supabase.table("badge_users").update({"twitter_id": twitter_id}).eq("telegram_id", telegram_id).execute()

    return {
        "status": "linked",
        "telegram_id": telegram_id,
        "twitter_id": twitter_id
    }

@router.get("/verify/{telegram_id}")
async def verify_telegram_user(telegram_id: int):
    result = supabase.table("badge_users") \
        .select("username", "first_name", "last_name", "badge_issued", "discord_id", "twitter_id") \
        .eq("telegram_id", telegram_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")

    return result.data[0]
