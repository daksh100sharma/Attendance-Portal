import aiomysql
import asyncio

async def get_db_connection():
    """
    Establishes and returns an asynchronous database connection.
    
    Returns:
        aiomysql.Connection: The MySQL database connection.
    """
    try:
        db_connection = await aiomysql.connect(
            host='localhost',
            user='root',
            password='',
            db='attendance_system'
        )
        return db_connection
    except aiomysql.Error as err:
        print(f"Error: {err}")
        return None
