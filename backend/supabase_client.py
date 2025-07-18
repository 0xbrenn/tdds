# backend/supabase_client.py
import os
from supabase import create_client, Client
from dotenv import load_dotenv
import httpx
from functools import lru_cache

load_dotenv()

# IMPORTANT: Use the SERVICE ROLE KEY for backend operations
# This key bypasses Row Level Security
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_SERVICE_ROLE_KEY:
    # Fallback to anon key if service role key not found
    # But this will cause RLS issues
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    print("⚠️ WARNING: Using anon key instead of service role key. This may cause RLS issues.")

# Create a custom httpx client with connection pooling and timeouts
limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
timeout = httpx.Timeout(10.0, connect=5.0)

# Create a persistent client with connection pooling
http_client = httpx.Client(
    limits=limits,
    timeout=timeout,
    http2=True,  # Enable HTTP/2 for better performance
)

# Create the Supabase client without custom options
# The newer version of supabase-py doesn't support passing options directly
@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Get a cached Supabase client"""
    # Create client without custom options for now
    client = create_client(
        SUPABASE_URL,
        SUPABASE_SERVICE_ROLE_KEY
    )
    
    # Configure the client after creation
    # Disable auto refresh token for backend usage
    if hasattr(client.auth, 'auto_refresh_token'):
        client.auth.auto_refresh_token = False
    
    # If you need to use custom httpx client, check if the client supports it
    # Some versions might expose it differently
    if hasattr(client, '_rest') and hasattr(client._rest, '_session'):
        # Try to replace the session if possible
        try:
            client._rest._session = http_client
        except:
            pass  # If it doesn't work, continue with default client
    
    return client

# Export the client
supabase = get_supabase_client()

# Add a health check function
async def check_database_health():
    """Quick health check for database connection"""
    try:
        result = supabase.table("badge_users").select("id").limit(1).execute()
        return True
    except Exception as e:
        print(f"Database health check failed: {e}")
        return False