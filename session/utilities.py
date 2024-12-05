import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
import asyncio
from db.db_connection import get_db_connection
import aiomysql
import bcrypt
from flask import jsonify
import json
import threading
import time

cachedTokens = []
CACHE_EXPIRATION_TIME = 60

async def verifyToken(token, userId: int):
    if not token or not userId:
        return False
    doesTokenExistInCache = False
    
    if (token, userId) in cachedTokens:
        print('Token verified using cachedTokens')
        return True
        
    if not doesTokenExistInCache:
            db_connection = await get_db_connection()
            if not db_connection:
                return False
            async with db_connection.cursor() as cursor:
                    try: 
                        query= """
                        SELECT id FROM sessions WHERE token = %s AND user_id = %s
                        """
                        await cursor.execute(query, (token, userId))
                        result = await cursor.fetchone()
                        
                        if not result:
                            return False
                        cachedTokens.append((token, userId))
                        print('cache not found, put current to cachedTokens')
                        return True
                    except aiomysql.MySQLError as err:
                        print(f"""Error in mysql, {err}""")
                        return False
                    finally:
                        db_connection.close()
    return False

async def revokeToken(targetId: int, userLevel: int, isForSelf: bool, targetToken: str = None):
    if isForSelf:
        try: cachedTokens.remove((targetToken, targetId))
        except ValueError as err:
            pass
    
    db_connection = await get_db_connection()
    if not db_connection:
        return False
    
    async with db_connection.cursor() as cursor:
        try:
            targetLevel: None
            if not isForSelf:
                query = """
                SELECT level FROM faculty WHERE id = %s
                """
                await cursor.execute(query, (targetId))
                targetLevel = await cursor.fetchone()
                
                query2 = """
                SELECT token FROM sessions WHERE user_id = %s
                """
                await cursor.execute(query2, (targetId))
                tupleTargetFetchedToken = await cursor.fetchone()
                if not tupleTargetFetchedToken:
                    return -2
                targetFetchedToken = tupleTargetFetchedToken[0]
            
                if not targetLevel:
                    return False
                
                if targetLevel[0] >= userLevel:
                    return -1
                try: cachedTokens.remove((targetFetchedToken, targetId))
                except ValueError as err:
                    pass
                
                query3 = """
                DELETE FROM sessions WHERE token = %s AND user_id = %s
                """
                await cursor.execute(query3, (targetFetchedToken, targetId))
                await db_connection.commit()
                return True
                
            query3 = """
            DELETE FROM sessions WHERE token = %s AND user_id = %s
            """
            await cursor.execute(query3, (targetToken, targetId))
            await db_connection.commit()
            return True
        except aiomysql.MySQLError as err:
            print(f"""Error in mysql, {err}""")
            return False
        finally:
            db_connection.close()

async def cleanup_expired_tokens():
    while True:
        await asyncio.sleep(CACHE_EXPIRATION_TIME)
        cachedTokens.clear()
        print("Cache has been reset.")