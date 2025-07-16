import aiomysql
from core.config import config
import logging

class Database:
    _pool = None

    @classmethod
    async def init_pool(cls):
        logging.info("Connecting to MySQL...")
        cls._pool = await aiomysql.create_pool(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            db=config.DB_NAME,
            autocommit=True,
            minsize=1,
            maxsize=10,
        )
        logging.info("Database connection pool established.")

    @classmethod
    async def close_pool(cls):
        if cls._pool:
            cls._pool.close()
            await cls._pool.wait_closed()
            logging.info("Database connection pool closed.")

    @classmethod
    async def fetch(cls, query, args=None):
        async with cls._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, args or ())
                return await cur.fetchall()

    @classmethod
    async def fetchrow(cls, query, args=None):
        async with cls._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, args or ())
                return await cur.fetchone()

    @classmethod
    async def execute(cls, query, args=None):
        async with cls._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, args or ())
                return cur.lastrowid
