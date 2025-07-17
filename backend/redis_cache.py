# redis_cache.py - Add to your backend
import redis
import json
import asyncio
from typing import Optional, Any
from datetime import timedelta
import pickle

class RedisCache:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(redis_url, decode_responses=False)
        
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            data = self.redis.get(key)
            if data:
                return pickle.loads(data)
        except Exception as e:
            print(f"Cache get error: {e}")
        return None
    
    def set(self, key: str, value: Any, ttl: int = 300):
        """Set value in cache with TTL in seconds"""
        try:
            self.redis.setex(key, ttl, pickle.dumps(value))
        except Exception as e:
            print(f"Cache set error: {e}")
    
    def delete(self, key: str):
        """Delete key from cache"""
        try:
            self.redis.delete(key)
        except Exception:
            pass
    
    def clear_pattern(self, pattern: str):
        """Clear all keys matching pattern"""
        try:
            for key in self.redis.scan_iter(match=pattern):
                self.redis.delete(key)
        except Exception:
            pass

# Initialize cache
cache = RedisCache(os.getenv("REDIS_URL", "redis://localhost:6379"))

# Updated main.py endpoints with caching

@app.get("/api/status/{email}")
async def check_user_status(email: str):
    """Check all verification statuses for a user"""
    # Check Redis cache first
    cache_key = f"status:{email}"
    cached_result = cache.get(cache_key)
    
    if cached_result is not None:
        logger.info(f"Redis cache hit for {cache_key}")
        return cached_result
    
    try:
        # Your existing database query code...
        result = await asyncio.wait_for(
            asyncio.to_thread(
                lambda: supabase.table("badge_users")
                .select("*")
                .eq("email", email)
                .execute()
            ),
            timeout=5.0
        )
        
        # Process result...
        response = {
            "exists": bool(result.data),
            # ... rest of your response
        }
        
        # Cache for 5 minutes
        cache.set(cache_key, response, ttl=300)
        
        return response
        
    except Exception as e:
        logger.error(f"Error checking user status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/dashboard/{email}")
async def get_user_dashboard(email: str):
    """Get user dashboard data with Redis caching"""
    # Check cache first
    cache_key = f"dashboard:{email}"
    cached_result = cache.get(cache_key)
    
    if cached_result is not None:
        logger.info(f"Redis cache hit for {cache_key}")
        return cached_result
    
    # Your existing dashboard code...
    # After getting all data:
    
    dashboard_data = {
        "user": user_data,
        "drops": drops_data,
        "referrals": referrals_data
    }
    
    # Cache for 10 minutes
    cache.set(cache_key, dashboard_data, ttl=600)
    
    return dashboard_data

# Add cache invalidation when data changes
@app.post("/api/claim-badge-with-referral")
async def claim_badge_with_referral(request: Request):
    # Your existing code...
    
    # After successful badge claim:
    cache.delete(f"status:{email}")
    cache.delete(f"dashboard:{email}")
    
    # Also clear referrer's cache if applicable
    if referrer_email:
        cache.delete(f"dashboard:{referrer_email}")