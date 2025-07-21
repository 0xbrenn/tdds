# backend/auth_telegram.py
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
    else:
        # Don't create a new record - user should register with email first
        print(f"⚠️ Telegram user {telegram_id} tried to auth without email registration")
        raise HTTPException(status_code=400, detail="Please register with email first")

    return {"status": "ok", "telegram_id": telegram_id}

# In auth_telegram.py - Add referral code handling

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
        existing_telegram = supabase.table("badge_users").select("*").eq("telegram_id", telegram_id).execute()
        
        if existing_telegram.data:
            for record in existing_telegram.data:
                if record.get("email") != email:
                    other_email = record.get("email", "unknown")
                    raise HTTPException(
                        status_code=400, 
                        detail=f"This Telegram account is already linked to {other_email[:3]}***"
                    )
        
        # Check if user exists with this email
        existing = supabase.table("badge_users").select("*").eq("email", email).execute()
        
        if existing.data:
            # Update with referral code if provided
            update_data = {
                "telegram_id": telegram_id,
                "telegram_username": telegram_username,
                "telegram_joined": is_channel_member
            }
            
            # If user doesn't have a referral code yet, add it
            if referral_code and not existing.data[0].get("referred_by"):
                update_data["referred_by"] = referral_code
            
            supabase.table("badge_users").update(update_data).eq("email", email).execute()
            return {"status": "ok", "message": "Telegram linked successfully"}
        else:
            raise HTTPException(status_code=404, detail="User not found. Please register with email first.")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")
        
                
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
async def badge_status(telegram_id: str):  # Changed to str
    result = supabase.table("badge_users").select("badge_issued").eq("telegram_id", telegram_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    return {"badge_issued": result.data[0]["badge_issued"]}

@router.post("/badge/issue")
async def issue_badge(telegram_id: str = Body(..., embed=True)):  # Changed to str
    result = supabase.table("badge_users").update({
        "badge_issued": True,
        "badge_issued_at": "now()"
    }).eq("telegram_id", telegram_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "issued", "telegram_id": telegram_id}

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
    
    # Now update the correct user
    result = supabase.table("badge_users").update({
        "telegram_id": telegram_id,
        "telegram_username": telegram_username,
        "telegram_joined": True
    }).eq("email", email).execute()
    
    print(f"📝 Update result: {result.data}")
    
    if result.data:
        return {"status": "success", "telegram_id": telegram_id}
    else:
        raise HTTPException(status_code=404, detail="User not found")


# Add this new endpoint to your auth_telegram.py file

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
        
        # Check if this Telegram ID is linked to a different email
        if user_record.get("telegram_id") and user_record.get("telegram_id") != str(telegram_id):
            # Different Telegram ID is linked to this email
            other_telegram = supabase.table("badge_users").select("*").eq("telegram_id", str(telegram_id)).execute()
            if other_telegram.data:
                other_email = other_telegram.data[0].get("email", "unknown")
                return {
                    "status": "already_linked_other", 
                    "message": f"This Telegram account is already linked to {other_email[:3]}***"
                }
        
        # Check if Telegram is already verified for this user
        if user_record.get("telegram_joined") and user_record.get("telegram_id") == str(telegram_id):
            # Already verified - just return success
            return {
                "status": "already_verified",
                "message": "Your Telegram is already verified!"
            }
        
        # Update the user record
        update_data = {
            "telegram_id": str(telegram_id),
            "telegram_username": telegram_username,
            "telegram_joined": is_channel_member
        }
        
        # Add referral code if user doesn't have one yet
        if referral_code and not user_record.get("referred_by"):
            update_data["referred_by"] = referral_code
        
        # Update the database
        result = supabase.table("badge_users").update(update_data).eq("email", email).execute()
        
        if result.data:
            return {
                "status": "success",
                "message": "Telegram verification completed successfully!"
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
            return {
                "status": "success",
                "message": "Telegram verification completed successfully!",
                "telegram_joined": True
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update user record")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error in force_verify_telegram: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/verify/{telegram_id}")
async def verify_telegram_user(telegram_id: str):  # Changed to str
    result = supabase.table("badge_users") \
        .select("username", "first_name", "last_name", "badge_issued", "discord_id", "twitter_id", "email") \
        .eq("telegram_id", telegram_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")

    return result.data[0]