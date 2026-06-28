import asyncio
import asyncpg
import os
from dotenv import load_dotenv
load_dotenv()

async def check():
    user = os.environ["DB_USER"]
    pwd = os.environ["DB_PASSWORD"]
    host = os.environ["DB_HOST"]
    port = os.environ["DB_PORT"]
    name = os.environ["DB_NAME"]
    dsn = "postgresql://" + user + ":" + pwd + "@" + host + ":" + port + "/" + name
    
    conn = await asyncpg.connect(dsn, timeout=15)
    try:
        tables = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
        print("Tables:")
        for t in tables:
            print("  " + t["table_name"])
        
        ext = await conn.fetchval("SELECT extname FROM pg_extension WHERE extname='vector'")
        print("pgvector extension installed: " + str(ext))
    except Exception as e:
        print("Error: " + str(e))
    finally:
        await conn.close()

asyncio.run(check())
