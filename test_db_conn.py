import asyncio
import asyncpg
import os
from dotenv import load_dotenv
load_dotenv()

async def test():
    user = os.environ['DB_USER']
    pwd = os.environ['DB_PASSWORD']
    host = os.environ['DB_HOST']
    port = os.environ['DB_PORT']
    name = os.environ['DB_NAME']
    dsn = f"postgresql://{user}:{pwd}@{host}:{port}/{name}"
    try:
        conn = await asyncpg.connect(dsn, timeout=10)
        v = await conn.fetchval('SELECT version()')
        print(f'Connected! PostgreSQL: {v}')
        await conn.close()
    except Exception as e:
        print(f'Failed: {e}')

asyncio.run(test())
