# backend/redis_cache.py
import redis
import json
import asyncio
from typing import Optional, Any, Union
from datetime import timedelta
import pickle
import logging
from functools import wraps
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class RedisCache:
    def __init__(self, redis_url: str = None):
        """Initialize Redis cache with connection pool"""
        if redis_url is None:
            # Default to local Redis or use environment variable
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        
        # Parse Redis URL and create connection pool
        self.pool = redis.ConnectionPool.from_url(
            redis_url,
            max_connections=50,  # Support many concurrent connections
            decode_responses=True  # Automatically decode responses to strings
        )
        self.redis_client = redis.Redis(connection_pool=self.pool)
        
        # Test connection
        try:
            self.redis_client.ping()
            logger.info(f"✅ Redis connected successfully to {redis_url}")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            raise

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            value = self.redis_client.get(key)
            if value is None:
                return None
            
            # Try to deserialize JSON, fallback to string
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        except Exception as e:
            logger.error(f"Redis get error for key {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL (default 5 minutes)"""
        try:
            # Serialize to JSON if not a string
            if not isinstance(value, str):
                value = json.dumps(value)
            
            return self.redis_client.setex(key, ttl, value)
        except Exception as e:
            logger.error(f"Redis set error for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.error(f"Redis delete error for key {key}: {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis delete pattern error for {pattern}: {e}")
            return 0

    def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.error(f"Redis exists error for key {key}: {e}")
            return False

    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment a counter"""
        try:
            return self.redis_client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Redis increment error for key {key}: {e}")
            return None

    def get_all_matching(self, pattern: str) -> dict:
        """Get all key-value pairs matching pattern"""
        try:
            keys = self.redis_client.keys(pattern)
            if not keys:
                return {}
            
            # Use pipeline for efficiency
            pipeline = self.redis_client.pipeline()
            for key in keys:
                pipeline.get(key)
            
            values = pipeline.execute()
            result = {}
            
            for key, value in zip(keys, values):
                if value:
                    try:
                        result[key] = json.loads(value)
                    except json.JSONDecodeError:
                        result[key] = value
            
            return result
        except Exception as e:
            logger.error(f"Redis get_all_matching error for pattern {pattern}: {e}")
            return {}

    async def get_async(self, key: str) -> Optional[Any]:
        """Async wrapper for get"""
        return await asyncio.to_thread(self.get, key)

    async def set_async(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Async wrapper for set"""
        return await asyncio.to_thread(self.set, key, value, ttl)

    async def delete_async(self, key: str) -> bool:
        """Async wrapper for delete"""
        return await asyncio.to_thread(self.delete, key)


# Cache key generators
def status_key(email: str) -> str:
    """Generate cache key for user status"""
    return f"status:{email}"

def dashboard_key(email: str) -> str:
    """Generate cache key for dashboard data"""
    return f"dashboard:{email}"

def referral_key(code: str) -> str:
    """Generate cache key for referral code"""
    return f"referral:{code}"

def verification_key(email: str, platform: str) -> str:
    """Generate cache key for verification status"""
    return f"verify:{platform}:{email}"

def rate_limit_key(identifier: str, action: str) -> str:
    """Generate cache key for rate limiting"""
    return f"ratelimit:{action}:{identifier}"


# Decorator for caching function results
def cache_result(ttl: int = 300, key_prefix: str = ""):
    """Decorator to cache function results"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = f"{key_prefix}:{func.__name__}"
            if args:
                cache_key += f":{':'.join(str(arg) for arg in args)}"
            if kwargs:
                cache_key += f":{':'.join(f'{k}={v}' for k, v in sorted(kwargs.items()))}"
            
            # Try to get from cache
            cached = cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            if result is not None:
                cache.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


# Rate limiting decorator
def rate_limit(max_requests: int = 10, window: int = 60):
    """Rate limiting decorator"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            # Get identifier (IP or user email)
            identifier = request.client.host
            if hasattr(request.state, "user_email"):
                identifier = request.state.user_email
            
            key = rate_limit_key(identifier, func.__name__)
            
            # Check current count
            current = cache.increment(key)
            if current == 1:
                # First request, set expiry
                cache.redis_client.expire(key, window)
            
            if current > max_requests:
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=429, 
                    detail=f"Rate limit exceeded. Max {max_requests} requests per {window} seconds."
                )
            
            return await func(request, *args, **kwargs)
        
        return wrapper
    return decorator


# Initialize global cache instance
cache = None

def init_cache():
    """Initialize cache - call this in your main.py startup"""
    global cache
    if cache is None:
        cache = RedisCache()
    return cache

