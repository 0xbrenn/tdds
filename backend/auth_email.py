from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from supabase_client import supabase
import os
import random
import string
from datetime import datetime, timedelta
import resend

router = APIRouter()

# Initialize Resend
resend.api_key = os.getenv("RESEND_API_KEY")

# Store verification codes temporarily (use Redis in production)
verification_codes = {}

class EmailRequest(BaseModel):
    email: EmailStr

class VerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str

def generate_verification_code():
    """Generate a 6-digit verification code"""
    return ''.join(random.choices(string.digits, k=6))

@router.post("/send-verification")
async def send_verification(request: EmailRequest):
    """Send verification code to email"""
    try:
        # Generate code
        code = generate_verification_code()
        
        # Store code with expiration (5 minutes)
        verification_codes[request.email] = {
            "code": code,
            "expires": datetime.now() + timedelta(minutes=5)
        }
        
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
           "from": "IOPn Early Badge <noreply@mail.cor3innovations.io>",
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
        # Check if code exists
        if request.email not in verification_codes:
            raise HTTPException(status_code=400, detail="No verification code found. Please request a new one.")
        
        stored = verification_codes[request.email]
        
        # Check expiration
        if datetime.now() > stored["expires"]:
            del verification_codes[request.email]
            raise HTTPException(status_code=400, detail="Code expired. Please request a new one.")
        
        # Check code
        if stored["code"] != request.code:
            raise HTTPException(status_code=400, detail="Invalid code. Please try again.")
        
        # Code is valid! Clean up and save to database
        del verification_codes[request.email]
        
        # Save to database
        try:
            existing = supabase.table("badge_users").select("*").eq("email", request.email).execute()
            
            if existing.data:
                # Update existing record
                supabase.table("badge_users").update({
                    "email_added": True,
                    "email_verified_at": datetime.now().isoformat()
                }).eq("email", request.email).execute()
            else:
                # Create new record
                supabase.table("badge_users").insert({
                    "email": request.email,
                    "email_added": True,
                    "email_verified_at": datetime.now().isoformat(),
                    "badge_issued": False
                }).execute()
        except Exception as e:
            print(f"Database error (continuing anyway): {e}")
        
        return {
            "success": True,
            "email": request.email,
            "message": "Email verified successfully"
        }
        
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