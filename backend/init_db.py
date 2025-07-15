# backend/init_db.py
import os
import logging
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def init_database():
    """Initialize database tables if they don't exist"""
    try:
        # Create Supabase client
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
         
        logger.info("Checking database tables...") 
        
        # SQL to create badge_users table if it doesn't exist
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS badge_users (
            id SERIAL PRIMARY KEY,
            telegram_id TEXT UNIQUE,
            discord_id TEXT UNIQUE,
            twitter_id TEXT UNIQUE,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            email TEXT UNIQUE,
            badge_issued BOOLEAN DEFAULT FALSE,
            telegram_joined BOOLEAN DEFAULT FALSE,
            discord_joined BOOLEAN DEFAULT FALSE,
            twitter_followed BOOLEAN DEFAULT FALSE,
            email_added BOOLEAN DEFAULT FALSE,
            telegram_username TEXT,
            discord_username TEXT,
            twitter_username TEXT,
            email_verified_at TIMESTAMP,
            badge_issued_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        """
        
        # Create indexes for better performance
        create_indexes_sql = """
        CREATE INDEX IF NOT EXISTS idx_badge_users_email ON badge_users(email);
        CREATE INDEX IF NOT EXISTS idx_badge_users_telegram_id ON badge_users(telegram_id);
        CREATE INDEX IF NOT EXISTS idx_badge_users_discord_id ON badge_users(discord_id);
        CREATE INDEX IF NOT EXISTS idx_badge_users_twitter_id ON badge_users(twitter_id);
        CREATE INDEX IF NOT EXISTS idx_badge_users_badge_issued ON badge_users(badge_issued);
        """
        
        # Create updated_at trigger
        create_trigger_sql = """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        
        DROP TRIGGER IF EXISTS update_badge_users_updated_at ON badge_users;
        
        CREATE TRIGGER update_badge_users_updated_at 
        BEFORE UPDATE ON badge_users 
        FOR EACH ROW 
        EXECUTE FUNCTION update_updated_at_column();
        """
        
        # Check if table exists
        check_table = supabase.table("badge_users").select("id").limit(1).execute()
        
        if hasattr(check_table, 'error') and check_table.error:
            logger.info("Table doesn't exist, creating badge_users table...")
            # Table doesn't exist, create it
            # Note: Supabase doesn't allow direct SQL execution via the client
            # You'll need to run this SQL in the Supabase dashboard or use psycopg2
            logger.warning("Please run the following SQL in your Supabase SQL editor:")
            print("\n" + "="*50)
            print("-- Run this SQL in Supabase SQL Editor --")
            print(create_table_sql)
            print(create_indexes_sql)
            print(create_trigger_sql)
            print("="*50 + "\n")
        else:
            logger.info("✅ Database tables already exist")
            
            # Check table structure
            sample = supabase.table("badge_users").select("*").limit(1).execute()
            if sample.data:
                columns = list(sample.data[0].keys())
                logger.info(f"✅ Table columns: {columns}")
            
            # Get table statistics
            count_result = supabase.table("badge_users").select("id", count="exact").execute()
            if hasattr(count_result, 'count'):
                logger.info(f"✅ Total users in database: {count_result.count}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database initialization error: {str(e)}")
        return False

def check_database_health():
    """Check if database is accessible and healthy"""
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Try a simple query
        result = supabase.table("badge_users").select("id").limit(1).execute()
        
        # Check for badges issued
        badges_issued = supabase.table("badge_users").select("id", count="exact").eq("badge_issued", True).execute()
        
        stats = {
            "healthy": True,
            "badges_issued": getattr(badges_issued, 'count', 0)
        }
        
        logger.info(f"✅ Database health check passed. Badges issued: {stats['badges_issued']}")
        return stats
        
    except Exception as e:
        logger.error(f"❌ Database health check failed: {str(e)}")
        return {"healthy": False, "error": str(e)}