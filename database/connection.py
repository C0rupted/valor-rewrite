import aiomysql, logging

from pymysql.err import OperationalError

from core.config import config



class Database:
    _pool = None  # Class-level variable to hold the connection pool


    @classmethod
    async def init_pool(cls):
        """
        Initialize the connection pool to the MySQL database using aiomysql.
        This should be called once when the bot starts.
        """
        logging.info("Connecting to MySQL...")
        cls._pool = await aiomysql.create_pool(
            host=config.DB_HOST,           # Database host from config
            port=config.DB_PORT,           # Database port from config
            user=config.DB_USER,           # Database user from config
            password=config.DB_PASSWORD,   # Database password from config
            db=config.DB_NAME,             # Database name from config
            autocommit=True,               # Automatically commit transactions
            minsize=1,                     # Minimum number of connections in the pool
            maxsize=10,                    # Maximum number of connections in the pool
        )
        logging.info("Database connection pool established.")


    @classmethod
    async def close_pool(cls):
        """
        Close the connection pool gracefully.
        This should be called when the bot is shutting down.
        """
        if cls._pool:
            cls._pool.close()              # Close the pool (no new connections)
            await cls._pool.wait_closed()  # Wait for all connections to close
            logging.info("Database connection pool closed.")


    @classmethod
    async def fetch(cls, query, args=None, retry: bool = True):
        """
        Execute a SELECT query that returns multiple rows.
        
        Args:
            query (str): The SQL query to execute.
            args (tuple or list, optional): Parameters to safely substitute in query.
            retry (bool): Whether to retry query if it fails for some reason
        
        Returns:
            List[Dict]: List of rows, each row is a dictionary mapping column names to values.
        """
        try:
            async with cls._pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(query, args or ())
                    return await cur.fetchall()
        except OperationalError:
            if retry:
                logging.warning(f"Retrying SQL query: {query}")
                Database.fetch(query, args=args, retry=False)
            else:
                logging.error(f"SQL query failed: {query}")




    @classmethod
    async def fetchrow(cls, query, args=None):
        """
        Execute a SELECT query that returns a single row.
        
        Args:
            query (str): The SQL query to execute.
            args (tuple or list, optional): Parameters to safely substitute in query.
        
        Returns:
            Dict or None: A single row as a dictionary or None if no row found.
        """
        async with cls._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, args or ())
                return await cur.fetchone()


    @classmethod
    async def execute(cls, query, args=None):
        """
        Execute a query that modifies data (INSERT, UPDATE, DELETE).
        
        Args:
            query (str): The SQL query to execute.
            args (tuple or list, optional): Parameters to safely substitute in query.
        
        Returns:
            int: The last inserted row ID (if applicable), or 0.
        """
        async with cls._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, args or ())
                return cur.lastrowid

