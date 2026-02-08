"""Quick test to verify database connection."""
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text
from config.settings import settings

def test_connection():
    print(f"Testing connection to: {settings.APP_DB_URL}\n")
    
    try:
        engine = create_engine(settings.APP_DB_URL, pool_pre_ping=True)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"✅ Database connected successfully!")
            print(f"PostgreSQL version: {version}\n")
            
            # Check if tables exist
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """))
            tables = [row[0] for row in result.fetchall()]
            
            if tables:
                print(f"📊 Existing tables ({len(tables)}):")
                for table in tables:
                    print(f"   - {table}")
            else:
                print("⚠️  No tables found. Run seed script to create them.")
                
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    test_connection()
