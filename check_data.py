import asyncio
import asyncpg
import os
from dotenv import load_dotenv
load_dotenv()

async def run():
    user = os.environ["DB_USER"]
    pwd = os.environ["DB_PASSWORD"]
    host = os.environ["DB_HOST"]
    port = os.environ["DB_PORT"]
    name = os.environ["DB_NAME"]
    dsn = "postgresql://" + user + ":" + pwd + "@" + host + ":" + port + "/" + name
    
    conn = await asyncpg.connect(dsn, timeout=15)
    try:
        # Check migration script
        with open("database/migrate_add_columns.py", "r") as f:
            content = f.read()
        print("Migration script loaded")
        
        # Check existing data
        tables = ["customers", "tickets", "messages", "knowledge_base", "channel_configs", "agent_metrics", "conversations", "customer_identifiers"]
        for t in tables:
            count = await conn.fetchval("SELECT COUNT(*) FROM " + t)
            print(f"  {t}: {count} rows")
        
    except Exception as e:
        print("Error: " + str(e))
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

asyncio.run(run())
