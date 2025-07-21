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

# Try to import Redis cache - graceful fallback if not available
try:
    from redis_cache import init_cache, RedisCache, status_key, dashboard_key, rate_limit, cache_result
    REDIS_AVAILABLE = True
    cache = None  # Will be initialized in lifespan
except ImportError:
    logger.warning("Redis cache module not available, using in-memory cache")
    REDIS_AVAILABLE = False
    cache = None

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

# Simple in-memory cache implementation (fallback when Redis not available)
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
    
    def delete(self, key: str):
        if key in self.cache:
            del self.cache[key]
            return True
        return False
    
    async def get_async(self, key: str) -> Optional[Any]:
        return self.get(key)
    
    async def set_async(self, key: str, value: Any, ttl: int = None):
        # If a specific TTL is provided, we could implement per-key TTL
        # For now, we'll use the instance TTL
        self.set(key, value)
    
    async def delete_async(self, key: str):
        return self.delete(key)
    
    def clear_expired(self):
        now = datetime.now()
        expired_keys = [
            key for key, (_, timestamp) in self.cache.items()
            if now - timestamp >= self.ttl
        ]
        for key in expired_keys:
            del self.cache[key]
        
        return len(expired_keys)
    
    def clear_all(self):
        """Clear all cached items"""
        count = len(self.cache)
        self.cache.clear()
        return count

# Create cache instances with shorter TTL
if not REDIS_AVAILABLE:
    status_cache = SimpleCache(ttl_seconds=30)  # 30 second cache for status
    dashboard_cache = SimpleCache(ttl_seconds=30)  # 30 second cache for dashboard
else:
    # These will be used as fallback if Redis fails
    status_cache = SimpleCache(ttl_seconds=30)
    dashboard_cache = SimpleCache(ttl_seconds=30)

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
    
    # Initialize Redis cache if available
    global cache  # Important!
    redis_available = False
    if REDIS_AVAILABLE:
        try:
            cache = init_cache()  # Assign the cache instance!
            logger.info("✅ Redis cache initialized")
            redis_available = True
        except Exception as e:
            logger.error(f"❌ Redis initialization failed: {e}")
            logger.info("⚠️  Running without Redis cache - performance will be limited")
    
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
    - Cache: {'✅ Redis' if redis_available else '⚠️ In-Memory (Limited)'}
    - Telegram Bot: {'✅' if os.getenv('TELEGRAM_BOT_TOKEN') else '❌'}
    - Discord OAuth: {'✅' if os.getenv('DISCORD_CLIENT_ID') else '❌'}
    - Twitter OAuth: {'✅' if os.getenv('TWITTER_CLIENT_ID') else '❌'}
    - Email Service: {'✅' if os.getenv('RESEND_API_KEY') else '❌'}
    """)
    
    # Start background task for cache cleanup (only for in-memory cache)
    if not REDIS_AVAILABLE:
        async def clear_cache_periodically():
            while True:
                await asyncio.sleep(60)  # Run every minute
                if status_cache:
                    status_cache.clear_expired()
                if dashboard_cache:
                    dashboard_cache.clear_expired()
        
        asyncio.create_task(clear_cache_periodically())
    
    yield
    
    # Shutdown
    if REDIS_AVAILABLE and cache and hasattr(cache, 'redis_client'):
        cache.redis_client.close()
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
        "cache": "Redis" if (REDIS_AVAILABLE and cache) else "In-Memory",
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
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
    }
    
    # Check database
    try:
        start = time.time()
        result = await asyncio.wait_for(
            asyncio.to_thread(lambda: supabase.table("badge_users").select("id").limit(1).execute()),
            timeout=5.0
        )
        db_time = time.time() - start
        health_status["database"] = f"healthy (response time: {db_time:.2f}s)"
    except asyncio.TimeoutError:
        health_status["database"] = "unhealthy: timeout"
    except Exception as e:
        health_status["database"] = f"unhealthy: {str(e)}"
    
    # Check cache status
    if REDIS_AVAILABLE and cache:
        try:
            cache.redis_client.ping()
            health_status["cache"] = "Redis: healthy"
            # Get cache stats
            info = cache.redis_client.info()
            health_status["cache_stats"] = {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "0"),
                "total_commands_processed": info.get("total_commands_processed", 0)
            }
        except Exception as e:
            health_status["cache"] = f"Redis: unhealthy - {str(e)}"
    else:
        health_status["cache"] = "In-Memory"
        if status_cache and dashboard_cache:
            health_status["cache_status"] = {
                "status_cache_size": len(status_cache.cache),
                "dashboard_cache_size": len(dashboard_cache.cache)
            }
    
    return health_status

# Optimized status check with caching and timeout
@app.get("/api/status/{email}")
async def check_user_status(request: Request, email: str):
    """Check all verification statuses for a user"""
    # Rate limiting if Redis available
    if REDIS_AVAILABLE and cache:
        try:
            # Simple rate limit check
            rate_key = f"ratelimit:status:{request.client.host}"
            current = cache.increment(rate_key)
            if current == 1:
                cache.redis_client.expire(rate_key, 60)
            if current > 1000:  # 30 requests per minute
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
        except HTTPException:
            raise
        except Exception:
            pass  # Don't fail on rate limit errors
    
    # Check cache first
    if REDIS_AVAILABLE and cache:
        cached_result = await cache.get_async(f"status:{email}")
    else:
        cached_result = status_cache.get(f"status:{email}")
    
    if cached_result is not None:
        logger.info(f"Cache hit for status:{email}")
        return cached_result
    
    try:
        # Since supabase methods are synchronous, use a lambda with asyncio.to_thread
        start_time = time.time()
        result = await asyncio.wait_for(
            asyncio.to_thread(
                lambda: supabase.table("badge_users")
                .select("*")
                .eq("email", email)
                .execute()
            ),
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
            # Cache non-existent users for shorter time (30 seconds)
            if REDIS_AVAILABLE and cache:
                await cache.set_async(f"status:{email}", response, ttl=30)
            else:
                status_cache.set(f"status:{email}", response)
            return response
        
        user = result.data[0]
        
        # Build response
        tasks = {
            "email": True,  # They're in the database, so email is verified
            "telegram": bool(user.get("telegram_joined")),
            "discord": bool(user.get("discord_id")),
            "twitter": bool(user.get("twitter_id"))
        }
        
        # User can claim if all tasks are complete and badge not issued
        can_claim = all(tasks.values()) and not user.get("badge_issued", False)
        
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
        
        # Cache with shorter TTL (30 seconds instead of 300)
        if REDIS_AVAILABLE and cache:
            await cache.set_async(f"status:{email}", response, ttl=30)
        else:
            status_cache.set(f"status:{email}", response)
            
        return response
        
    except asyncio.TimeoutError:
        logger.error(f"Database timeout for email: {email}")
        raise HTTPException(status_code=504, detail="Database query timeout")
    except Exception as e:
        logger.error(f"Error checking status for {email}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Badge claiming endpoint (old version - kept for compatibility)
@app.post("/api/claim-badge")
async def claim_badge(request: Request):
    """Claim the badge after completing all tasks (legacy endpoint)"""
    data = await request.json()
    email = data.get("email")
    
    # Redirect to new endpoint
    return await claim_badge_with_referral(request)

@app.post("/api/clear-cache/{email}")
async def clear_user_cache(email: str):
    """Clear cache for a specific user"""
    cleared = False
    cleared_types = []
    
    if REDIS_AVAILABLE and cache:
        try:
            # Clear both status and dashboard cache
            status_deleted = cache.delete(f"status:{email}")
            dashboard_deleted = cache.delete(f"dashboard:{email}")
            
            if status_deleted or dashboard_deleted:
                cleared = True
                cleared_types.append("Redis")
                
            logger.info(f"Cleared Redis cache for {email} - Status: {status_deleted}, Dashboard: {dashboard_deleted}")
        except Exception as e:
            logger.error(f"Failed to clear Redis cache: {e}")
    
    # Also clear in-memory cache if using it
    if status_cache:
        status_cache.delete(f"status:{email}")
        cleared = True
        cleared_types.append("In-Memory Status")
        
    if dashboard_cache:
        dashboard_cache.delete(f"dashboard:{email}")
        cleared = True
        cleared_types.append("In-Memory Dashboard")
    
    return {
        "email": email,
        "cleared": cleared,
        "cache_types": cleared_types,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/cache-stats")
async def get_cache_stats():
    """Get cache statistics"""
    stats = {
        "timestamp": datetime.now().isoformat(),
        "cache_type": "Redis" if (REDIS_AVAILABLE and cache) else "In-Memory"
    }
    
    if REDIS_AVAILABLE and cache:
        try:
            # Get Redis info
            info = cache.redis_client.info()
            stats["redis"] = {
                "connected": True,
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "0"),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace": {}
            }
            
            # Get keyspace info
            for db, data in info.items():
                if db.startswith("db"):
                    stats["redis"]["keyspace"][db] = data
                    
        except Exception as e:
            stats["redis"] = {"connected": False, "error": str(e)}
    
    # Add in-memory cache stats
    if status_cache:
        stats["in_memory_status"] = {
            "size": len(status_cache.cache),
            "ttl_seconds": status_cache.ttl.total_seconds()
        }
        
    if dashboard_cache:
        stats["in_memory_dashboard"] = {
            "size": len(dashboard_cache.cache),
            "ttl_seconds": dashboard_cache.ttl.total_seconds()
        }
    
    return stats



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
        if REDIS_AVAILABLE and cache:
            await cache.delete_async(f"status:{email}")
            await cache.delete_async(f"dashboard:{email}")
        else:
            status_cache.delete(f"status:{email}")
            dashboard_cache.delete(f"dashboard:{email}")
        
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
                    if REDIS_AVAILABLE and cache:
                        await cache.delete_async(f"dashboard:{referrer_user['email']}")
                    else:
                        dashboard_cache.delete(f"dashboard:{referrer_user['email']}")
                    
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
    if REDIS_AVAILABLE and cache:
        cached_result = await cache.get_async(f"dashboard:{email}")
    else:
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
        if REDIS_AVAILABLE and cache:
            await cache.set_async(f"dashboard:{email}", response, ttl=600)
        else:
            dashboard_cache.set(f"dashboard:{email}", response)
        
        return response
        
    except asyncio.TimeoutError:
        logger.error(f"Database timeout for dashboard: {email}")
        raise HTTPException(status_code=504, detail="Database timeout - please try again")
    except Exception as e:
        logger.error(f"Error getting dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Cache management endpoint (useful for testing/debugging)
@app.post("/api/clear-cache/{email}")
async def clear_user_cache(email: str):
    """Clear all cached data for a user - useful after updates"""
    cleared = 0
    
    if REDIS_AVAILABLE and cache:
        # Clear specific cache keys
        if await cache.delete_async(f"status:{email}"):
            cleared += 1
        if await cache.delete_async(f"dashboard:{email}"):
            cleared += 1
        
        # Clear any other related cache keys
        pattern_cleared = cache.delete_pattern(f"*:{email}")
        cleared += pattern_cleared
        
        return {
            "message": f"Cleared {cleared} Redis cache entries for {email}",
            "cache_type": "Redis",
            "cleared": cleared
        }
    else:
        # Clear in-memory cache
        if f"status:{email}" in status_cache.cache:
            status_cache.delete(f"status:{email}")
            cleared += 1
        if f"dashboard:{email}" in dashboard_cache.cache:
            dashboard_cache.delete(f"dashboard:{email}")
            cleared += 1
        
        return {
            "message": f"Cleared {cleared} in-memory cache entries for {email}",
            "cache_type": "In-Memory",
            "cleared": cleared
        }

# Cache statistics endpoint (useful for monitoring)
@app.get("/api/cache-stats")
async def get_cache_stats():
    """Get cache statistics"""
    if REDIS_AVAILABLE and cache:
        try:
            info = cache.redis_client.info()
            return {
                "cache_type": "Redis",
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "hit_rate": round(info.get("keyspace_hits", 0) / 
                                (info.get("keyspace_hits", 0) + info.get("keyspace_misses", 1)) * 100, 2),
                "memory_used": info.get("used_memory_human", "0"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands": info.get("total_commands_processed", 0)
            }
        except Exception as e:
            return {"error": f"Failed to get Redis stats: {str(e)}"}
    else:
        return {
            "cache_type": "In-Memory",
            "status_cache_size": len(status_cache.cache) if status_cache else 0,
            "dashboard_cache_size": len(dashboard_cache.cache) if dashboard_cache else 0,
            "message": "Limited statistics available for in-memory cache"
        }

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
    # Use multiple workers only if not using in-memory cache
    workers = 4 if REDIS_AVAILABLE else 1
    uvicorn.run(app, host="0.0.0.0", port=8000, workers=workers)