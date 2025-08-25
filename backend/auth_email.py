# backend/auth_email.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from supabase_client import supabase
import os
import random
import string
from datetime import datetime, timedelta
import resend
import json

router = APIRouter()

# Initialize Resend
resend.api_key = os.getenv("RESEND_API_KEY")

class EmailRequest(BaseModel):
    email: EmailStr

class VerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str

class EmailRequestWithReferral(BaseModel):
    email: EmailStr
    referral_code: str = None

def generate_verification_code():
    """Generate a 6-digit verification code"""
    return ''.join(random.choices(string.digits, k=6))

def generate_referral_code():
    """Generate a unique 8-character referral code"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def store_verification_code(email: str, code: str):
    """Store verification code in database"""
    try:
        # Delete any existing codes for this email
        supabase.table("verification_codes").delete().eq("email", email).execute()
        
        # Store new code with expiration
        expires_at = (datetime.now() + timedelta(minutes=5)).isoformat()
        supabase.table("verification_codes").insert({
            "email": email,
            "code": code,
            "expires_at": expires_at,
            "created_at": datetime.now().isoformat()
        }).execute()
        
        return True
    except Exception as e:
        print(f"Error storing verification code: {e}")
        # Fallback to creating the table if it doesn't exist
        try:
            # Try to create the table
            supabase.rpc("create_verification_codes_table", {}).execute()
            # Retry the insert
            expires_at = (datetime.now() + timedelta(minutes=5)).isoformat()
            supabase.table("verification_codes").insert({
                "email": email,
                "code": code,
                "expires_at": expires_at,
                "created_at": datetime.now().isoformat()
            }).execute()
            return True
        except:
            return False

def get_verification_code(email: str) -> dict:
    """Get verification code from database"""
    try:
        result = supabase.table("verification_codes").select("*").eq("email", email).execute()
        
        if result.data and len(result.data) > 0:
            code_data = result.data[0]
            # Check if expired
            expires_at = datetime.fromisoformat(code_data["expires_at"].replace('Z', '+00:00').replace('+00:00', ''))
            if datetime.now() > expires_at:
                # Code expired, delete it
                supabase.table("verification_codes").delete().eq("email", email).execute()
                return None
            return code_data
        return None
    except Exception as e:
        print(f"Error getting verification code: {e}")
        return None

@router.post("/send-verification")
async def send_verification(request: EmailRequest):
    """Send verification code to email"""
    try:
        # Check if this email exists in our system
        existing = supabase.table("badge_users").select("*").eq("email", request.email).execute()
        
        if existing.data and len(existing.data) > 0:
            user = existing.data[0]
            # User exists - this is a login, not a new registration
            print(f"✅ Existing user logging in: {request.email}")
        
        # Generate code
        code = generate_verification_code()
        
        # Store code in database
        if not store_verification_code(request.email, code):
            # If database storage fails, use Redis if available
            try:
                from main import cache, REDIS_AVAILABLE
                if REDIS_AVAILABLE and cache:
                    cache.set(f"verify_code:{request.email}", code, ttl=300)
                    print(f"Stored code in Redis for {request.email}")
            except:
                raise HTTPException(status_code=500, detail="Failed to store verification code")
        
        # Send email
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f4f4f4;
                    margin: 0;
                    padding: 0;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: #ffffff;
                }}
                .header {{
                    background-color: #000000;
                    color: #ffffff;
                    padding: 40px;
                    text-align: center;
                }}
                .content {{
                    padding: 40px;
                    text-align: center;
                }}
                .code-box {{
                    background-color: #f8f8f8;
                    border: 2px solid #e0e0e0;
                    border-radius: 8px;
                    padding: 30px;
                    margin: 30px 0;
                    font-size: 36px;
                    letter-spacing: 10px;
                    font-weight: bold;
                    color: #333333;
                }}
                .footer {{
                    padding: 20px;
                    text-align: center;
                    color: #666666;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0; font-size: 32px;">IOPn Early Badge</h1>
                    <p style="margin: 10px 0 0 0; font-size: 16px;">Email Verification</p>
                </div>
                <div class="content">
                    <h2 style="color: #333;">Verify Your Email Address</h2>
                    <p style="color: #666; font-size: 16px; line-height: 24px;">
                        Thank you for joining IOPn! Please enter the verification code below to continue earning your Early n-Badge.
                    </p>
                    <div class="code-box">
                        {code}
                    </div>
                    <p style="color: #999; font-size: 14px;">
                        This code will expire in 5 minutes.
                    </p>
                </div>
                <div class="footer">
                    <p>If you didn't request this verification, please ignore this email.</p>
                    <p>&copy; 2025 IOPn. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Send email via Resend
        response = resend.Emails.send({
            "from": "IOPn Early Badge <noreply@iopn.io>",
            "to": request.email,
            "subject": "Verify Your Email - IOPn Early Badge",
            "html": html_content
        })
        
        print(f"✅ Email sent to {request.email} with code: {code}")
        print(f"📧 Resend response: {response}")
        
        return {
            "success": True,
            "message": "Verification code sent to your email"
        }
        
    except Exception as e:
        print(f"❌ Error sending email: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/verify-code")
async def verify_code(request: VerifyCodeRequest):
    """Verify the email code"""
    try:
        # Check database first
        code_data = get_verification_code(request.email)
        
        if not code_data:
            # Try Redis as fallback
            try:
                from main import cache, REDIS_AVAILABLE
                if REDIS_AVAILABLE and cache:
                    stored_code = cache.get(f"verify_code:{request.email}")
                    if stored_code and stored_code == request.code:
                        # Code is valid in Redis
                        code_data = {"code": stored_code}
            except:
                pass
        
        if not code_data:
            raise HTTPException(status_code=400, detail="No verification code found. Please request a new one.")
        
        # Verify code matches
        if code_data["code"] != request.code:
            raise HTTPException(status_code=400, detail="Invalid verification code")
        
        # Code is valid - update user as verified
        result = supabase.table("badge_users").select("*").eq("email", request.email).execute()
        
        if result.data and len(result.data) > 0:
            # Existing user - update email_added to true
            supabase.table("badge_users").update({
                "email_added": True
            }).eq("email", request.email).execute()
            
            # Delete the used code
            supabase.table("verification_codes").delete().eq("email", request.email).execute()
            
            # Also try to delete from Redis
            try:
                from main import cache, REDIS_AVAILABLE
                if REDIS_AVAILABLE and cache:
                    cache.delete(f"verify_code:{request.email}")
            except:
                pass
            
            return {
                "success": True,
                "message": "Email verified successfully",
                "existing_user": True
            }
        else:
            # This shouldn't happen - user should exist from send-verification
            raise HTTPException(status_code=404, detail="User not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/resend-code")
async def resend_code(request: EmailRequest):
    """Resend verification code"""
    return await send_verification(request)

@router.post("/register")
async def register_email(request: EmailRequest):
    """Alternative endpoint for backwards compatibility"""
    return await send_verification(request)

@router.get("/status/{email}")
async def email_status(email: str):
    """Check badge status by email"""
    result = supabase.table("badge_users").select("*").eq("email", email).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = result.data[0]
    return {
        "email": email,
        "email_added": user.get("email_added", False),
        "badge_issued": user.get("badge_issued", False),
        "tasks_completed": {
            "email": user.get("email_added", False),
            "telegram": user.get("telegram_joined", False),
            "discord": user.get("discord_joined", False),
            "twitter": user.get("twitter_followed", False)
        }
    }

@router.post("/register-instant")
async def register_instant(request: EmailRequestWithReferral):
    """Instant registration without email verification for new users"""
    try:
        # Check if user already exists
        existing = supabase.table("badge_users").select("*").eq("email", request.email).execute()
        
        if existing.data and len(existing.data) > 0:
            raise HTTPException(status_code=400, detail="Email already registered. Please login instead.")
        
        # Generate a unique referral code for this user
        user_referral_code = generate_referral_code()
        
        # Create new user
        new_user = {
            "email": request.email,
            "email_added": True,  # Mark as verified immediately
            "referral_code": user_referral_code,
            "telegram_joined": False,
            "discord_joined": False,
            "twitter_followed": False,
            "badge_issued": False,
            "created_at": datetime.now().isoformat()
        }
        
        # Add referral info if provided
        if request.referral_code:
            new_user["referred_by"] = request.referral_code
        
        result = supabase.table("badge_users").insert(new_user).execute()
        
        if result.data:
            return {
                "success": True,
                "message": "Registration successful",
                "email": request.email,
                "referral_code": user_referral_code
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create user")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Registration error: {str(e)}")
        raise HTTPException(status_code=500, detail="Registration failed")

# SQL to create the verification_codes table in Supabase:
"""
CREATE TABLE IF NOT EXISTS verification_codes (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    code VARCHAR(6) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_verification_codes_email ON verification_codes(email);
CREATE INDEX idx_verification_codes_expires_at ON verification_codes(expires_at);

-- Auto-delete expired codes
CREATE OR REPLACE FUNCTION delete_expired_codes() RETURNS void AS $$
BEGIN
    DELETE FROM verification_codes WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql;
"""