# backend/main.py
import os
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from datetime import datetime, timedelta
import random
import string
from typing import Dict, Any, Optional
import asyncio
import time

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

# Simple in-memory cache implementation
class SimpleCache:
    def __init__(self, ttl_seconds: int = 30):
        self.cache: Dict[str, tuple[Any, datetime]] = {}
        self.ttl = timedelta(seconds=ttl_seconds)
    
    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            value, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.ttl:
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any):
        self.cache[key] = (value, datetime.now())
    
    def clear_expired(self):
        now = datetime.now()
        expired_keys = [
            key for key, (_, timestamp) in self.cache.items()
            if now - timestamp >= self.ttl
        ]
        for key in expired_keys:
            del self.cache[key]

# Create cache instances
status_cache = SimpleCache(ttl_seconds=30)  # 30 second cache for status
dashboard_cache = SimpleCache(ttl_seconds=60)  # 60 second cache for dashboard

def mask_email(email):
    """Mask email for privacy - shows first 3 chars + *** + domain"""
    if not email or '@' not in email:
        return email
    
    local, domain = email.split('@', 1)
    
    if len(local) <= 3:
        # Very short email, just show first char
        masked_local = local[0] + '***'
    else:
        # Show first 3 chars
        masked_local = local[:3] + '***'
    
    return f"{masked_local}@{domain}"

# Referral system functions
def generate_referral_code():
    """Generate a unique 8-character referral code"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def calculate_drop_reward():
    """Calculate if user gets a drop and which tier"""
    # 60% chance to get a drop (increased from 40%)
    if random.random() > 0.6:
        return None
    
    # If they get a drop, determine tier
    roll = random.random()
    if roll < 0.60:  # 60% chance for Bronze (decreased from 70%)
        return {
            "tier": "bronze",
            "rep_range": {"min": 10, "max": 50},
            "color": "#CD7F32"
        }
    elif roll < 0.90:  # 30% chance for Gold (increased from 25%)
        return {
            "tier": "gold", 
            "rep_range": {"min": 100, "max": 300},
            "color": "#FFD700"
        }
    else:  # 10% chance for Platinum (increased from 5%)
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
    - Frontend URL: {os.getenv('FRONTEND_URL', 'http://badge.iopn.io')}
    - Telegram Bot: {'✅' if os.getenv('TELEGRAM_BOT_TOKEN') else '❌'}
    - Discord OAuth: {'✅' if os.getenv('DISCORD_CLIENT_ID') else '❌'}
    - Twitter OAuth: {'✅' if os.getenv('TWITTER_CLIENT_ID') else '❌'}
    - Email Service: {'✅' if os.getenv('RESEND_API_KEY') else '❌'}
    """)
    
    # Start background task for cache cleanup
    async def clear_cache_periodically():
        while True:
            await asyncio.sleep(60)  # Run every minute
            status_cache.clear_expired()
            dashboard_cache.clear_expired()
    
    asyncio.create_task(clear_cache_periodically())
    
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
        "https://api.badge.iopn.io",
        os.getenv("FRONTEND_URL", "http://localhost:3000")
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add timing middleware for debugging
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log slow requests
    if process_time > 1.0:  # Log requests taking more than 1 second
        logger.warning(f"Slow request: {request.method} {request.url.path} took {process_time:.2f}s")
    
    return response

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
        # Try to query database with timeout
        start = time.time()
        result = await asyncio.wait_for(
            asyncio.to_thread(lambda: supabase.table("badge_users").select("id").limit(1).execute()),
            timeout=5.0
        )
        db_time = time.time() - start
        db_status = f"healthy (response time: {db_time:.2f}s)"
    except asyncio.TimeoutError:
        db_status = "unhealthy: timeout"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy",
        "database": db_status,
        "timestamp": datetime.now().isoformat(),
        "cache_status": {
            "status_cache_size": len(status_cache.cache),
            "dashboard_cache_size": len(dashboard_cache.cache)
        }
    }

# Optimized status check with caching and timeout
@app.get("/api/status/{email}")
async def check_user_status(email: str):
    """Check all verification statuses for a user"""
    # Check cache first
    cached_result = status_cache.get(f"status:{email}")
    if cached_result is not None:
        logger.info(f"Cache hit for status:{email}")
        return cached_result
    
    try:
        # Use asyncio timeout to prevent hanging
        async def fetch_user_status():
            result = supabase.table("badge_users")\
                .select("*")\
                .eq("email", email)\
                .execute()
            return result
        
        # Set a 5-second timeout for the database query
        start_time = time.time()
        result = await asyncio.wait_for(
            asyncio.to_thread(fetch_user_status),
            timeout=5.0
        )
        query_time = time.time() - start_time
        logger.info(f"Database query for {email} took {query_time:.2f}s")
        
        if not result.data:
            response = {
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
            # Don't cache non-existent users for as long
            return response
        
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
        
        response = {
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
        
        # Cache the result
        status_cache.set(f"status:{email}", response)
        
        return response
        
    except asyncio.TimeoutError:
        logger.error(f"Database timeout for status check: {email}")
        raise HTTPException(status_code=504, detail="Database timeout - please try again")
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
    referral_code = data.get("referral_code")  # The code they used to sign up
    
    if not email:
        raise HTTPException(status_code=400, detail="Email required")
    
    try:
        # Get user with timeout
        result = await asyncio.wait_for(
            asyncio.to_thread(lambda: supabase.table("badge_users").select("*").eq("email", email).execute()),
            timeout=5.0
        )
        
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
        
        # Prepare update data
        update_data = {
            "badge_issued": True,
            "badge_issued_at": datetime.now().isoformat()
        }
        
        # Only update referred_by if user doesn't already have one and a referral code was provided
        if referral_code and not user.get("referred_by"):
            update_data["referred_by"] = referral_code
        
        # Issue badge
        update_result = await asyncio.wait_for(
            asyncio.to_thread(lambda: supabase.table("badge_users").update(update_data).eq("email", email).execute()),
            timeout=5.0
        )
        
        # Clear cache for this user
        status_cache.set(f"status:{email}", None)
        dashboard_cache.set(f"dashboard:{email}", None)
        
        # Process referral reward if applicable
        referral_reward = None
        if referral_code:  # Only process if this is a new referral
            # Find the referrer
            referrer = await asyncio.wait_for(
                asyncio.to_thread(lambda: supabase.table("badge_users").select("*").eq("referral_code", referral_code).execute()),
                timeout=5.0
            )
            
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
                    
                    await asyncio.wait_for(
                        asyncio.to_thread(lambda: supabase.table("referral_drops").insert(drop_data).execute()),
                        timeout=5.0
                    )
                    
                    # Clear referrer's dashboard cache
                    dashboard_cache.set(f"dashboard:{referrer_user['email']}", None)
                    
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
            
    except asyncio.TimeoutError:
        logger.error(f"Database timeout for badge claim: {email}")
        raise HTTPException(status_code=504, detail="Database timeout - please try again")
    except Exception as e:
        logger.error(f"Error claiming badge: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Dashboard endpoint with caching
@app.get("/api/dashboard/{email}")
async def get_user_dashboard(email: str):
    """Get user dashboard data including drops and referrals"""
    # Check cache first
    cached_result = dashboard_cache.get(f"dashboard:{email}")
    if cached_result is not None:
        logger.info(f"Cache hit for dashboard:{email}")
        return cached_result
    
    try:
        # Get user data with timeout
        start_time = time.time()
        user_result = await asyncio.wait_for(
            asyncio.to_thread(lambda: supabase.table("badge_users").select("*").eq("email", email).execute()),
            timeout=5.0
        )
        
        if not user_result.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = user_result.data[0]
        
        # Generate referral code if user doesn't have one
        if not user.get("referral_code"):
            referral_code = generate_referral_code()
            
            # Make sure it's unique
            while True:
                existing = await asyncio.wait_for(
                    asyncio.to_thread(lambda: supabase.table("badge_users").select("id").eq("referral_code", referral_code).execute()),
                    timeout=5.0
                )
                if not existing.data:
                    break
                referral_code = generate_referral_code()
            
            # Update user with referral code
            await asyncio.wait_for(
                asyncio.to_thread(lambda: supabase.table("badge_users").update({
                    "referral_code": referral_code
                }).eq("email", email).execute()),
                timeout=5.0
            )
            
            user["referral_code"] = referral_code
        
        # Get user's drops with timeout
        drops_result = await asyncio.wait_for(
            asyncio.to_thread(lambda: supabase.table("referral_drops").select("*").eq("user_email", email).order("earned_at", desc=True).execute()),
            timeout=5.0
        )
        
        # MASK EMAILS IN DROPS
        if drops_result.data:
            for drop in drops_result.data:
                if 'earned_from_email' in drop:
                    drop['earned_from_email'] = mask_email(drop['earned_from_email'])
        
        # Get users they've referred
        referred_users = await asyncio.wait_for(
            asyncio.to_thread(lambda: supabase.table("badge_users").select("email, badge_issued, created_at").eq("referred_by", user.get("referral_code", "")).execute()),
            timeout=5.0
        )
        
        # MASK EMAILS IN REFERRALS
        if referred_users.data:
            for ref_user in referred_users.data:
                if 'email' in ref_user:
                    ref_user['email'] = mask_email(ref_user['email'])
        
        # Calculate stats
        total_drops = len(drops_result.data) if drops_result.data else 0
        bronze_drops = sum(1 for d in (drops_result.data or []) if d["drop_tier"] == "bronze")
        gold_drops = sum(1 for d in (drops_result.data or []) if d["drop_tier"] == "gold")
        platinum_drops = sum(1 for d in (drops_result.data or []) if d["drop_tier"] == "platinum")
        
        # Calculate potential REP (not claimable until NFT launch)
        potential_rep_min = sum(d["rep_min"] for d in (drops_result.data or []))
        potential_rep_max = sum(d["rep_max"] for d in (drops_result.data or []))
        
        response = {
            "user": {
                "email": user["email"],  # User's own email is not masked
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
        
        query_time = time.time() - start_time
        logger.info(f"Dashboard query for {email} took {query_time:.2f}s")
        
        # Cache the result
        dashboard_cache.set(f"dashboard:{email}", response)
        
        return response
        
    except asyncio.TimeoutError:
        logger.error(f"Database timeout for dashboard: {email}")
        raise HTTPException(status_code=504, detail="Database timeout - please try again")
    except Exception as e:
        logger.error(f"Error getting dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Catch-all endpoint for dashboard without email
@app.get("/api/dashboard/")
async def dashboard_no_email():
    """Catch requests without email parameter"""
    return {
        "error": "Email parameter required",
        "message": "Use /api/dashboard/{email} instead",
        "status": 400
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)