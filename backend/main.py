# backend/main.py
import os
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from datetime import datetime
import random
import string

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load env variables first
load_dotenv()

# Import database initialization
try:
    from init_postgres import init_database_direct, migrate_database
    USE_POSTGRES = True
except ImportError:
    logger.warning("PostgreSQL initialization not available, using basic init")
    from init_db import init_database, check_database_health
    USE_POSTGRES = False

# Import routers
from init_db import init_database, check_database_health
from auth_telegram import router as telegram_router
from auth_discord import router as discord_router
from auth_twitter import router as twitter_router
from auth_email import router as email_router
from supabase_client import supabase

# Referral system functions
def generate_referral_code():
    """Generate a unique 8-character referral code"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def calculate_drop_reward():
    """Calculate if user gets a drop and which tier"""
    # 40% chance to get a drop
    if random.random() > 0.4:
        return None
    
    # If they get a drop, determine tier
    roll = random.random()
    if roll < 0.70:  # 70% chance for Bronze
        return {
            "tier": "bronze",
            "rep_range": {"min": 10, "max": 50},
            "color": "#CD7F32"
        }
    elif roll < 0.95:  # 25% chance for Gold
        return {
            "tier": "gold", 
            "rep_range": {"min": 100, "max": 300},
            "color": "#FFD700"
        }
    else:  # 5% chance for Platinum
        return {
            "tier": "platinum",
            "rep_range": {"min": 500, "max": 1000},
            "color": "#E5E4E2"
        }

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    # Startup
    logger.info("🚀 Starting IOPn Early Badge API...")
    
    # Initialize database
    try:
        if USE_POSTGRES:
            logger.info("🔧 Initializing database with PostgreSQL...")
            if init_database_direct():
                logger.info("✅ Database initialized successfully")
                migrate_database()
            else:
                logger.error("❌ Database initialization failed")
        else:
            logger.info("🔧 Initializing database with Supabase client...")
            if init_database():
                logger.info("✅ Database checked successfully")
                health = check_database_health()
                logger.info(f"📊 Database health: {health}")
            else:
                logger.error("❌ Database check failed")
    except Exception as e:
        logger.error(f"❌ Critical error during database initialization: {str(e)}")
        logger.info("⚠️  Continuing anyway - database might need manual setup")
    
    # Log environment info
    logger.info(f"""
    🌍 Environment Configuration:
    - Frontend URL: {os.getenv('FRONTEND_URL', 'http://localhost:3000')}
    - Telegram Bot: {'✅' if os.getenv('TELEGRAM_BOT_TOKEN') else '❌'}
    - Discord OAuth: {'✅' if os.getenv('DISCORD_CLIENT_ID') else '❌'}
    - Twitter OAuth: {'✅' if os.getenv('TWITTER_CLIENT_ID') else '❌'}
    - Email Service: {'✅' if os.getenv('RESEND_API_KEY') else '❌'}
    """)
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down IOPn Early Badge API...")

# Create FastAPI app with lifespan
app = FastAPI(
    title="IOPn Early Badge API",
    version="1.0.0",
    description="API for IOPn Early Badge verification system",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://iopn.io",
        "https://badge.iopn.io",
        os.getenv("FRONTEND_URL", "http://localhost:3000")
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(telegram_router, prefix="/auth/telegram", tags=["telegram"])
app.include_router(discord_router, tags=["discord"])
app.include_router(twitter_router, tags=["twitter"])
app.include_router(email_router, prefix="/auth/email", tags=["email"])

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "IOPn Early Badge API",
        "status": "operational",
        "version": "1.0.0",
        "endpoints": {
            "auth": {
                "email": "/auth/email/send-verification",
                "twitter": "/auth/twitter/login",
                "discord": "/auth/discord/login",
                "telegram": "/auth/telegram/login"
            },
            "status": "/api/status/{email}",
            "health": "/health",
            "dashboard": "/api/dashboard/{email}"
        }
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Try to query database
        result = supabase.table("badge_users").select("id").limit(1).execute()
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy",
        "database": db_status,
        "timestamp": datetime.now().isoformat()
    }

# Unified status check - FIXED to prevent duplicate checks
@app.get("/api/status/{email}")
async def check_user_status(email: str):
    """Check all verification statuses for a user"""
    try:
        result = supabase.table("badge_users").select("*").eq("email", email).execute()
        
        if not result.data:
            return {
                "exists": False,
                "email": email,
                "tasks": {
                    "email": False,
                    "telegram": False,
                    "discord": False,
                    "twitter": False
                },
                "can_claim": False,
                "badge_issued": False
            }
        
        user = result.data[0]  # Should only be ONE user per email
        
        # Check all tasks
        tasks = {
            "email": user.get("email_added", False),
            "telegram": user.get("telegram_joined", False),
            "discord": user.get("discord_joined", False),
            "twitter": user.get("twitter_followed", False)
        }
        
        # Can claim if all tasks complete
        can_claim = all(tasks.values())
        
        return {
            "exists": True,
            "email": email,
            "tasks": tasks,
            "can_claim": can_claim,
            "badge_issued": user.get("badge_issued", False),
            "usernames": {
                "telegram": user.get("telegram_username"),
                "discord": user.get("discord_username"),
                "twitter": user.get("twitter_username")
            }
        }
        
    except Exception as e:
        logger.error(f"Error checking user status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Badge claiming endpoint (old version - kept for compatibility)
@app.post("/api/claim-badge")
async def claim_badge(request: Request):
    """Claim the badge after completing all tasks (legacy endpoint)"""
    data = await request.json()
    email = data.get("email")
    
    # Redirect to new endpoint
    return await claim_badge_with_referral(request)

# New badge claiming endpoint with referral support
@app.post("/api/claim-badge-with-referral")
async def claim_badge_with_referral(request: Request):
    """Claim badge and process referral rewards"""
    data = await request.json()
    email = data.get("email")
    referred_by_code = data.get("referral_code")  # The code they used to sign up
    
    if not email:
        raise HTTPException(status_code=400, detail="Email required")
    
    try:
        # Get user
        result = supabase.table("badge_users").select("*").eq("email", email).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = result.data[0]
        
        # Check all tasks completed
        tasks_complete = (
            user.get("email_added", False) and
            user.get("telegram_joined", False) and
            user.get("discord_joined", False) and
            user.get("twitter_followed", False)
        )
        
        if not tasks_complete:
            raise HTTPException(status_code=400, detail="All tasks must be completed first")
        
        if user.get("badge_issued", False):
            raise HTTPException(status_code=400, detail="Badge already claimed")
        
        # Issue badge
        update_result = supabase.table("badge_users").update({
            "badge_issued": True,
            "badge_issued_at": datetime.now().isoformat(),
            "referred_by": referred_by_code  # Store who referred them
        }).eq("email", email).execute()
        
        # Process referral reward if applicable
        referral_reward = None
        if referred_by_code:
            # Find the referrer
            referrer = supabase.table("badge_users").select("*").eq("referral_code", referred_by_code).execute()
            
            if referrer.data:
                referrer_user = referrer.data[0]
                
                # Calculate drop reward
                drop = calculate_drop_reward()
                
                if drop:
                    # Create drop record
                    drop_data = {
                        "user_id": referrer_user["id"],
                        "user_email": referrer_user["email"],
                        "drop_tier": drop["tier"],
                        "rep_min": drop["rep_range"]["min"],
                        "rep_max": drop["rep_range"]["max"],
                        "earned_from_email": email,
                        "earned_at": datetime.now().isoformat(),
                        "claimed": False  # Will be claimed when NFT launches
                    }
                    
                    supabase.table("referral_drops").insert(drop_data).execute()
                    
                    # Update referrer stats
                    current_referrals = referrer_user.get("successful_referrals", 0)
                    supabase.table("badge_users").update({
                        "successful_referrals": current_referrals + 1
                    }).eq("id", referrer_user["id"]).execute()
                    
                    referral_reward = {
                        "referrer_email": referrer_user["email"],
                        "drop": drop
                    }
        
        return {
            "success": True,
            "message": "Badge claimed successfully!",
            "badge_issued": True,
            "referral_reward": referral_reward
        }
            
    except Exception as e:
        logger.error(f"Error claiming badge: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Dashboard endpoint
@app.get("/api/dashboard/{email}")
async def get_user_dashboard(email: str):
    """Get user dashboard data including drops and referrals"""
    try:
        # Get user data
        user_result = supabase.table("badge_users").select("*").eq("email", email).execute()
        
        if not user_result.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = user_result.data[0]
        
        # Generate referral code if user doesn't have one
        if not user.get("referral_code"):
            referral_code = generate_referral_code()
            
            # Make sure it's unique
            while True:
                existing = supabase.table("badge_users").select("id").eq("referral_code", referral_code).execute()
                if not existing.data:
                    break
                referral_code = generate_referral_code()
            
            # Update user with referral code
            supabase.table("badge_users").update({
                "referral_code": referral_code
            }).eq("email", email).execute()
            
            user["referral_code"] = referral_code
        
        # Get user's drops
        drops_result = supabase.table("referral_drops").select("*").eq("user_email", email).order("earned_at", desc=True).execute()
        
        # Get users they've referred
        referred_users = supabase.table("badge_users").select("email, badge_issued, created_at").eq("referred_by", user.get("referral_code", "")).execute()
        
        # Calculate stats
        total_drops = len(drops_result.data) if drops_result.data else 0
        bronze_drops = sum(1 for d in (drops_result.data or []) if d["drop_tier"] == "bronze")
        gold_drops = sum(1 for d in (drops_result.data or []) if d["drop_tier"] == "gold")
        platinum_drops = sum(1 for d in (drops_result.data or []) if d["drop_tier"] == "platinum")
        
        # Calculate potential REP (not claimable until NFT launch)
        potential_rep_min = sum(d["rep_min"] for d in (drops_result.data or []))
        potential_rep_max = sum(d["rep_max"] for d in (drops_result.data or []))
        
        return {
            "user": {
                "email": user["email"],
                "referral_code": user.get("referral_code", ""),
                "badge_issued": user.get("badge_issued", False),
                "successful_referrals": user.get("successful_referrals", 0),
                "tasks": {
                    "email": user.get("email_added", False),
                    "telegram": user.get("telegram_joined", False),
                    "discord": user.get("discord_joined", False),
                    "twitter": user.get("twitter_followed", False)
                }
            },
            "drops": {
                "total": total_drops,
                "bronze": bronze_drops,
                "gold": gold_drops,
                "platinum": platinum_drops,
                "potential_rep": {
                    "min": potential_rep_min,
                    "max": potential_rep_max
                },
                "recent": drops_result.data[:5] if drops_result.data else []
            },
            "referrals": {
                "total": len(referred_users.data) if referred_users.data else 0,
                "completed": sum(1 for r in (referred_users.data or []) if r["badge_issued"]),
                "users": referred_users.data[:10] if referred_users.data else []
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)