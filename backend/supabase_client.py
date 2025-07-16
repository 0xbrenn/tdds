# backend/supabase_client.py
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# IMPORTANT: Use the SERVICE ROLE KEY for backend operations
# This key bypasses Row Level Security
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# If you don't have the service role key in your .env, add it:
# SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here

if not SUPABASE_SERVICE_ROLE_KEY:
    # Fallback to anon key if service role key not found
    # But this will cause RLS issues
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_KEY")
    print("⚠️ WARNING: Using anon key instead of service role key. This may cause RLS issues.")

# Create the client with service role key
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)