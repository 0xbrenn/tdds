# backend/auth_telegram.py
import os
import hashlib
import hmac
import logging
from fastapi import APIRouter, Request, HTTPException, Body
from supabase_client import supabase
from dotenv import load_dotenv

load_dotenv()
router = APIRouter()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
logger = logging.getLogger(__name__)

# Import cache utilities
try:
    from redis_cache import init_cache, status_key, dashboard_key
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Get cache instance from main.py
cache = None

def verify_telegram_hash(data: dict, bot_token: str) -> bool:
    check_hash = data.pop('hash', None)
    payload = '\n'.join([f'{k}={v}' for k, v in sorted(data.items())])
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    calculated_hash = hmac.new(secret_key, payload.encode(), hashlib.sha256).hexdigest()
    return calculated_hash == check_hash

def clear_user_cache(email: str):
    """Clear cache for a specific user"""
    try:
        # Access the global cache instance
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

@router.post("/")
async def telegram_auth(request: Request):
    data = await request.json()

    # if not verify_telegram_hash(data.copy(), BOT_TOKEN):
    #     raise HTTPException(status_code=403, detail="Invalid Telegram login")

    telegram_id = str(data["id"])  # Convert to string for consistency
    username = data.get("username", "")
    first_name = data.get("first_name", "")
    last_name = data.get("last_name", "")

    # FIXED: Don't create new records here, only update if exists
    existing = supabase.table("badge_users").select("*").eq("telegram_id", telegram_id).execute()
    
    if existing.data:
        # Update existing record
        supabase.table("badge_users").update({
            "telegram_joined": True,
            "telegram_username": username,
            "username": username,
            "first_name": first_name,
            "last_name": last_name
        }).eq("telegram_id", telegram_id).execute()
        
        # Clear cache for the user
        user_email = existing.data[0].get("email")
        if user_email:
            clear_user_cache(user_email)
    else:
        # Don't create a new record - user should register with email first
        print(f"⚠️ Telegram user {telegram_id} tried to auth without email registration")
        raise HTTPException(status_code=400, detail="Please register with email first")

    return {"status": "ok", "telegram_id": telegram_id}

@router.post("/link-simple")
async def link_telegram_simple(request: Request):
    """Simple endpoint to link Telegram to existing email user"""
    data = await request.json()
    email = data.get("email")
    telegram_id = str(data.get("telegram_id"))  # Convert to string
    telegram_username = data.get("telegram_username", "")
    
    print(f"🔗 Linking Telegram {telegram_id} to email {email}")
    
    if not email:
        raise HTTPException(status_code=400, detail="Email required")
    
    # FIXED: Clear telegram_id from any other users first
    existing_telegram = supabase.table("badge_users").select("*").eq("telegram_id", telegram_id).execute()
    
    if existing_telegram.data:
        for record in existing_telegram.data:
            if record.get("email") != email:
                print(f"⚠️ Telegram ID already exists for different user, removing...")
                supabase.table("badge_users").update({
                    "telegram_id": None,
                    "telegram_username": None,
                    "telegram_joined": False
                }).eq("id", record["id"]).execute()
                
                # Clear cache for the old user
                old_email = record.get("email")
                if old_email:
                    clear_user_cache(old_email)
    
    # Now update the correct user
    result = supabase.table("badge_users").update({
        "telegram_id": telegram_id,
        "telegram_username": telegram_username,
        "telegram_joined": True
    }).eq("email", email).execute()
    
    print(f"📝 Update result: {result.data}")
    
    if result.data:
        # CLEAR THE CACHE after successful update
        clear_user_cache(email)
        return {"status": "success", "telegram_id": telegram_id}
    else:
        raise HTTPException(status_code=404, detail="User not found")

@router.post("/link-with-channel-check")
async def link_with_channel_check(request: Request):
    """Link Telegram to email with channel membership check"""
    data = await request.json()
    email = data.get("email")
    telegram_id = data.get("telegram_id")
    telegram_username = data.get("telegram_username", "")
    is_channel_member = data.get("is_channel_member", False)
    referral_code = data.get("referral_code")  # Get referral code
    
    if not email or not telegram_id:
        raise HTTPException(status_code=400, detail="Email and Telegram ID required")
    
    try:
        # Check if Telegram ID is already linked to another email
        existing_telegram = supabase.table("badge_users").select("*").eq("telegram_id", str(telegram_id)).execute()
        
        if existing_telegram.data:
            for record in existing_telegram.data:
                if record.get("email") != email:
                    # Remove from other accounts
                    supabase.table("badge_users").update({
                        "telegram_id": None,
                        "telegram_username": None,
                        "telegram_joined": False
                    }).eq("id", record["id"]).execute()
                    
                    # Clear cache for the old user
                    old_email = record.get("email")
                    if old_email:
                        clear_user_cache(old_email)
        
        # Get the user record
        user_result = supabase.table("badge_users").select("*").eq("email", email).execute()
        
        if not user_result.data:
            raise HTTPException(status_code=404, detail="User not found. Please register with email first.")
        
        user_record = user_result.data[0]
        
        # Prepare update data
        update_data = {
            "telegram_id": str(telegram_id),
            "telegram_username": telegram_username,
            "telegram_joined": is_channel_member  # Only set True if in channel
        }
        
        # Add referral code if provided and user doesn't have one
        if referral_code and not user_record.get("referred_by"):
            update_data["referred_by"] = referral_code
        
        # Update the user
        result = supabase.table("badge_users").update(update_data).eq("email", email).execute()
        
        if result.data:
            # Clear cache after successful update
            clear_user_cache(email)
            return {
                "status": "success",
                "telegram_id": telegram_id,
                "is_channel_member": is_channel_member,
                "message": "Channel member! ✅" if is_channel_member else "Please join the channel"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update user record")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")

@router.post("/verify-and-update")
async def verify_and_update(request: Request):
    """Verify Telegram membership and update status - handles already linked cases"""
    data = await request.json()
    email = data.get("email")
    telegram_id = data.get("telegram_id")
    telegram_username = data.get("telegram_username", "")
    is_channel_member = data.get("is_channel_member", False)
    referral_code = data.get("referral_code")
    
    if not email or not telegram_id:
        raise HTTPException(status_code=400, detail="Email and Telegram ID required")
    
    try:
        # First, check if user exists with this email
        existing = supabase.table("badge_users").select("*").eq("email", email).execute()
        
        if not existing.data:
            raise HTTPException(status_code=404, detail="User not found. Please register with email first.")
        
        user_record = existing.data[0]
        
        # Check if this Telegram ID is already linked to another email
        telegram_check = supabase.table("badge_users").select("*").eq("telegram_id", str(telegram_id)).execute()
        
        if telegram_check.data:
            for record in telegram_check.data:
                if record.get("email") != email:
                    # This Telegram is linked to another email
                    supabase.table("badge_users").update({
                        "telegram_id": None,
                        "telegram_username": None,
                        "telegram_joined": False
                    }).eq("id", record["id"]).execute()
                    
                    # Clear cache for the old user
                    old_email = record.get("email")
                    if old_email:
                        clear_user_cache(old_email)
        
        # Update the user record
        update_data = {
            "telegram_id": str(telegram_id),
            "telegram_username": telegram_username,
            "telegram_joined": is_channel_member
        }
        
        # Add referral code if provided and user doesn't have one
        if referral_code and not user_record.get("referred_by"):
            update_data["referred_by"] = referral_code
        
        # Perform the update
        result = supabase.table("badge_users").update(update_data).eq("email", email).execute()
        
        if result.data:
            # Clear cache after successful update
            clear_user_cache(email)
            
            return {
                "status": "success",
                "telegram_id": telegram_id,
                "is_channel_member": is_channel_member,
                "message": "Telegram verified successfully!" if is_channel_member else "Please join the channel to complete verification"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update user record")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Database error in verify_and_update: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")

@router.post("/force-verify-telegram")
async def force_verify_telegram(request: Request):
    """Force verify Telegram for users already in channel - used when creating new badges"""
    data = await request.json()
    email = data.get("email")
    telegram_id = data.get("telegram_id")
    telegram_username = data.get("telegram_username", "")
    referral_code = data.get("referral_code")
    
    if not email or not telegram_id:
        raise HTTPException(status_code=400, detail="Email and Telegram ID required")
    
    try:
        # Check if user exists with this email
        existing = supabase.table("badge_users").select("*").eq("email", email).execute()
        
        if not existing.data:
            raise HTTPException(status_code=404, detail="User not found. Please register with email first.")
        
        user_record = existing.data[0]
        
        # First, clear any existing telegram_id from other users
        # This handles the case where your Telegram was linked to a previous badge
        other_users = supabase.table("badge_users").select("*").eq("telegram_id", str(telegram_id)).execute()
        
        if other_users.data:
            for other_user in other_users.data:
                if other_user.get("email") != email:
                    # Clear the telegram from the other user
                    logger.info(f"Clearing telegram_id {telegram_id} from user {other_user.get('email')}")
                    supabase.table("badge_users").update({
                        "telegram_id": None,
                        "telegram_username": None,
                        "telegram_joined": False
                    }).eq("id", other_user["id"]).execute()
                    
                    # Clear cache for the old user
                    old_email = other_user.get("email")
                    if old_email:
                        clear_user_cache(old_email)
        
        # Now update the current user with the Telegram info
        update_data = {
            "telegram_id": str(telegram_id),
            "telegram_username": telegram_username,
            "telegram_joined": True  # Force this to True since they're already in channel
        }
        
        # Add referral code if user doesn't have one yet
        if referral_code and not user_record.get("referred_by"):
            update_data["referred_by"] = referral_code
        
        # Update the database
        result = supabase.table("badge_users").update(update_data).eq("email", email).execute()
        
        if result.data:
            logger.info(f"Force verified Telegram {telegram_id} for email {email}")
            
            # Clear cache after successful update
            clear_user_cache(email)
            
            return {
                "status": "success",
                "message": "Telegram verification completed successfully!",
                "telegram_id": telegram_id
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update user record")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error in force_verify: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")

@router.get("/verify/{telegram_id}")
async def verify_telegram(telegram_id: str):
    result = supabase.table("badge_users").select("*").eq("telegram_id", telegram_id).execute()
    if result.data:
        return {"verified": True, "telegram_id": telegram_id}
    return {"verified": False, "telegram_id": telegram_id}

@router.post("/link-account")
async def link_telegram_twitter(request: Request):
    data = await request.json()
    telegram_id = data.get("telegram_id")
    twitter_id = data.get("twitter_id")
    
    # Link by updating the same row - find by telegram_id and update twitter_id
    result = supabase.table("badge_users").update({
        "twitter_id": twitter_id
    }).eq("telegram_id", telegram_id).execute()
    
    if result.data:
        # Clear cache for the user
        user_email = result.data[0].get("email")
        if user_email:
            clear_user_cache(user_email)
        return {"status": "linked"}
    else:
        raise HTTPException(status_code=404, detail="Telegram user not found")

@router.get("/badge/status/{telegram_id}")
async def badge_status(telegram_id: str):
    result = supabase.table("badge_users").select("*").eq("telegram_id", telegram_id).execute()
    if result.data:
        user = result.data[0]
        return {
            "has_badge": user.get("badge_issued", False),
            "telegram_verified": user.get("telegram_joined", False),
            "twitter_verified": bool(user.get("twitter_id")),
            "discord_verified": bool(user.get("discord_id"))
        }
    return {"has_badge": False, "telegram_verified": False, "twitter_verified": False, "discord_verified": False}

@router.post("/badge/issue")
async def issue_badge(request: Request):
    data = await request.json()
    telegram_id = data.get("telegram_id")
    
    if not telegram_id:
        raise HTTPException(status_code=400, detail="telegram_id required")
    
    result = supabase.table("badge_users").update({
        "badge_issued": True,
        "badge_issued_at": "now()"
    }).eq("telegram_id", telegram_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Clear cache for the user
    user_email = result.data[0].get("email")
    if user_email:
        clear_user_cache(user_email)
        
    return {"status": "issued", "telegram_id": telegram_id}