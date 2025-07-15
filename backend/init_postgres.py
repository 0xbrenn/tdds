# backend/init_postgres.py
import os
import psycopg2
from psycopg2 import sql
from urllib.parse import urlparse
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

def get_db_connection():
    """Get PostgreSQL connection from Supabase URL"""
    database_url = os.getenv("DATABASE_URL")  # or construct from SUPABASE_URL
    
    if not database_url:
        # Construct from Supabase URL if DATABASE_URL not provided
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        # Extract project ref from URL
        # https://xxxxx.supabase.co -> xxxxx
        project_ref = supabase_url.split('//')[1].split('.')[0]
        
        # Supabase database URL pattern
        database_url = f"postgresql://postgres.{project_ref}:postgres@{project_ref}.pooler.supabase.com:6543/postgres"
    
    return psycopg2.connect(database_url)

def init_database_direct():
    """Initialize database using direct PostgreSQL connection"""
    conn = None
    cursor = None
    
    try:
        logger.info("🔄 Connecting to database...")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'badge_users'
            );
        """)
        
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            logger.info("📦 Creating badge_users table...")
            
            # Create table
            cursor.execute("""
                CREATE TABLE badge_users (
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
            """)
            
            # Create indexes
            logger.info("📇 Creating indexes...")
            indexes = [
                "CREATE INDEX idx_badge_users_email ON badge_users(email);",
                "CREATE INDEX idx_badge_users_telegram_id ON badge_users(telegram_id);",
                "CREATE INDEX idx_badge_users_discord_id ON badge_users(discord_id);",
                "CREATE INDEX idx_badge_users_twitter_id ON badge_users(twitter_id);",
                "CREATE INDEX idx_badge_users_badge_issued ON badge_users(badge_issued);",
                "CREATE INDEX idx_badge_users_created_at ON badge_users(created_at DESC);"
            ]
            
            for index_sql in indexes:
                cursor.execute(index_sql)
            
            # Create updated_at trigger
            logger.info("⚡ Creating triggers...")
            cursor.execute("""
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = NOW();
                    RETURN NEW;
                END;
                $$ language 'plpgsql';  
            """)
            
            cursor.execute("""
                CREATE TRIGGER update_badge_users_updated_at 
                BEFORE UPDATE ON badge_users 
                FOR EACH ROW 
                EXECUTE FUNCTION update_updated_at_column();
            """)
            
            conn.commit()
            logger.info("✅ Database tables created successfully!")
            
        else:
            logger.info("✅ Database tables already exist")
            
            # Check for missing columns and add them if needed
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'badge_users' 
                AND table_schema = 'public';
            """)
            
            existing_columns = [row[0] for row in cursor.fetchall()]
            
            # Define expected columns
            expected_columns = {
                'telegram_username': 'TEXT',
                'discord_username': 'TEXT',
                'twitter_username': 'TEXT',
                'email_verified_at': 'TIMESTAMP',
                'badge_issued_at': 'TIMESTAMP',
                'updated_at': 'TIMESTAMP DEFAULT NOW()'
            }
            
            # Add missing columns
            for column, data_type in expected_columns.items():
                if column not in existing_columns:
                    logger.info(f"➕ Adding missing column: {column}")
                    cursor.execute(f"ALTER TABLE badge_users ADD COLUMN IF NOT EXISTS {column} {data_type};")
            
            conn.commit()
        
        # Get statistics
        cursor.execute("SELECT COUNT(*) FROM badge_users;")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM badge_users WHERE badge_issued = TRUE;")
        badges_issued = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM badge_users WHERE email_added = TRUE;")
        emails_verified = cursor.fetchone()[0]
        
        logger.info(f"""
        📊 Database Statistics:
        - Total users: {total_users}
        - Badges issued: {badges_issued}
        - Emails verified: {emails_verified}
        """)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database initialization error: {str(e)}")
        if conn:
            conn.rollback()
        return False
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def migrate_database():
    """Run database migrations if needed"""
    migrations = [
        # Add any future migrations here
        # Example:
        # {
        #     "version": 1,
        #     "description": "Add referral_code column",
        #     "sql": "ALTER TABLE badge_users ADD COLUMN IF NOT EXISTS referral_code TEXT UNIQUE;"
        # }
    ]
    
    conn = None
    cursor = None
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create migrations table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS migrations (
                id SERIAL PRIMARY KEY,
                version INTEGER UNIQUE NOT NULL,
                description TEXT,
                executed_at TIMESTAMP DEFAULT NOW()
            );
        """)
        
        # Run migrations
        for migration in migrations:
            cursor.execute(
                "SELECT EXISTS(SELECT 1 FROM migrations WHERE version = %s);",
                (migration['version'],)
            )
            
            if not cursor.fetchone()[0]:
                logger.info(f"🔄 Running migration {migration['version']}: {migration['description']}")
                cursor.execute(migration['sql'])
                cursor.execute(
                    "INSERT INTO migrations (version, description) VALUES (%s, %s);",
                    (migration['version'], migration['description'])
                )
                conn.commit()
                logger.info(f"✅ Migration {migration['version']} completed")
        
    except Exception as e:
        logger.error(f"❌ Migration error: {str(e)}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_database_direct()
    migrate_database()