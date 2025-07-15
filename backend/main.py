# backend/main.py
import os
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
from dotenv import load_dotenv

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
            "health": "/health"
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
        "timestamp": "now()"
    }

# Unified status check
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
        
        user = result.data[0]
        tasks = {
            "email": user.get("email_added", False),
            "telegram": user.get("telegram_joined", False),
            "discord": user.get("discord_joined", False),
            "twitter": user.get("twitter_followed", False)
        }
        
        return {
            "exists": True,
            "email": email,
            "tasks": tasks,
            "can_claim": all(tasks.values()),
            "badge_issued": user.get("badge_issued", False),
            "user_data": {
                "telegram_username": user.get("telegram_username"),
                "discord_username": user.get("discord_username"),
                "twitter_username": user.get("twitter_username")
            }
        }
    except Exception as e:
        logger.error(f"Error checking user status: {str(e)}")
        return {"error": str(e)}

# Issue badge endpoint
@app.post("/api/badge/claim")
async def claim_badge(request: Request):
    """Claim badge after all tasks completed"""
    data = await request.json()
    email = data.get("email")
    
    if not email:
        return {"error": "Email required"}
    
    # Check if all tasks completed
    status = await check_user_status(email)
    if not status.get("can_claim"):
        return {"error": "Not all tasks completed"}
    
    if status.get("badge_issued"):
        return {"error": "Badge already claimed"}
    
    # Issue badge
    result = supabase.table("badge_users").update({
        "badge_issued": True,
        "badge_issued_at": "now()"
    }).eq("email", email).execute()
    
    return {
        "success": True,
        "message": "Badge claimed successfully!",
        "badge_number": result.data[0].get("id")
    }

# Add startup message
@app.on_event("startup")
async def startup_message():
    logger.info("""
    ✨ IOPn Early Badge API is running!
    📍 Access the API at: http://localhost:8000
    📚 API Documentation: http://localhost:8000/docs
    """)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)