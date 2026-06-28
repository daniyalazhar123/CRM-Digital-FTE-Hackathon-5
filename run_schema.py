import asyncio
import asyncpg
import os
from dotenv import load_dotenv
load_dotenv()

async def run_schema():
    user = os.environ['DB_USER']
    pwd = os.environ['DB_PASSWORD']
    host = os.environ['DB_HOST']
    port = os.environ['DB_PORT']
    name = os.environ['DB_NAME']
    dsn = f"postgresql://{user}:{pwd}@{host}:{port}/{name}"
    
    with open('database/schema.sql', 'r') as f:
        schema = f.read()
    
    conn = await asyncpg.connect(dsn, timeout=15)
    try:
        await conn.execute(schema)
        print('Schema executed successfully!')
        
        # Verify tables
        tables = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
        for t in tables:
            print(f'  Table: {t["table_name"]}')
    except Exception as e:
        print(f'Error: {e}')
    finally:
        await conn.close()

asyncio.run(run_schema())
