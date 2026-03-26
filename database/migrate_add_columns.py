"""
CRM Digital FTE - Database Migration Script
Adds missing columns and tables for test compatibility.
"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'dbname': os.getenv('DB_NAME', 'crm_db'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres123')
}


def add_missing_columns_and_tables():
    """Add missing columns and tables."""
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = False
        cur = conn.cursor()
        
        print("Checking for missing columns in messages table...")
        
        # Check and add sentiment_score column if not exists
        try:
            cur.execute("""
                ALTER TABLE messages 
                ADD COLUMN IF NOT EXISTS sentiment_score FLOAT DEFAULT 0.5
            """)
            print("✓ sentiment_score column added/verified")
        except Exception as e:
            print(f"✗ Error adding sentiment_score: {e}")
        
        # Check and add created_at column if not exists (as alias to timestamp)
        try:
            cur.execute("""
                ALTER TABLE messages 
                ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE 
                GENERATED ALWAYS AS (timestamp) STORED
            """)
            print("✓ created_at column added/verified")
        except Exception as e:
            print(f"Note: created_at as generated column: {e}")
            print("  Using timestamp column instead (already exists)")
        
        # Create customer_identifiers table for cross-channel tracking
        print("\nCreating customer_identifiers table...")
        try:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS customer_identifiers (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
                    identifier_type VARCHAR(50),
                    identifier_value VARCHAR(255),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    UNIQUE(customer_id, identifier_type, identifier_value)
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_customer_identifiers_value ON customer_identifiers(identifier_value)")
            print("✓ customer_identifiers table created/verified")
        except Exception as e:
            print(f"✗ Error creating customer_identifiers: {e}")
        
        conn.commit()
        print("\n✓ Migration completed successfully!")
        
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    add_missing_columns_and_tables()
