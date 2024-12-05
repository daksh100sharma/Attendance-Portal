import asyncio
from db.db_connection import get_db_connection
import aiomysql
import bcrypt
from flask import jsonify
import uuid
from session.utilities import revokeToken

async def addFaculty(name: str, email: str, level: int, password: str):
    """
    Adds a new staff member to the 'faculty' table in the database.
    
    Parameters:
        name (str): The name of the staff member.
        email (str): The email of the staff member
        level (int): The level of the staff member.
        info (str): Additional information about the staff member (JSON). If empty, it is set to None.
        password (str): The staff member's password, which will be hashed.
    
    Returns:
        None: This function does not return any value. It directly interacts with the database.
    
    Raises:
        aiomysql.MySQLError: If there's an issue with the database query.
    """
    db_connection = await get_db_connection()
    if db_connection:
        async with db_connection.cursor() as cursor:
            try:
                query = """
                SELECT id FROM faculty WHERE email = %s
                """
                await cursor.execute(query, (email))
                tupleDoesEmailExist = await cursor.fetchone()
                
                if tupleDoesEmailExist:
                    return -2
                salt = bcrypt.gensalt(rounds=10)
                hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)

                query2 = """
                    INSERT INTO faculty (name, email, level, password)
                    VALUES (%s, %s, %s, %s)
                    """

                await cursor.execute(query2, (name, email, level, hashed_password.decode('utf-8')))
                await db_connection.commit()
                return True
            except aiomysql.MySQLError as err:
                print(f"Error adding staff member: {err}")
                return False
            finally:
                db_connection.close()
    else:
        print("Failed to connect to the database.")
        
async def authenticate(inputEmail: str, inputPassword: str):
    db_connection = await get_db_connection()
    if db_connection:
        async with db_connection.cursor() as cursor:
            try:
                token = str(uuid.uuid4())
                print(f"Generated token {token}")

                query = "SELECT name, password, level, id FROM faculty WHERE email=%s"
                await cursor.execute(query, (inputEmail,))
                
                result = await cursor.fetchone()
                if result:
                    name, stored_hash, level, id = result
                    
                    if bcrypt.checkpw(inputPassword.encode('utf-8'), stored_hash.encode('utf-8')):
                        
                        query2 = "SELECT token FROM sessions WHERE user_id = %s"
                        await cursor.execute(query2, (id,))
                        existing_session = await cursor.fetchone()

                        if existing_session:
                            query3 = "UPDATE sessions SET token = %s WHERE user_id = %s"
                            await cursor.execute(query3, (token, id))
                        else:
                            query4 = "INSERT INTO sessions (token, user_id) VALUES (%s, %s)"
                            await cursor.execute(query4, (token, id))
                        
                        await db_connection.commit()

                        return (token, id, name, level)
                    else:
                        return False
                else:
                    return False
            except aiomysql.MySQLError as err:
                print(f"Error during authentication: {err}")
                return False
            finally:
                db_connection.close()
    else:
        print("Failed to connect to the database.")
        return False
    
async def getClasses(facultyId: int, fetchAllClassesBoolean):
    """
    Seaches all the classes to find faculty's respective classes
    
    Parameters:
        facultyId (int): The ID of the faculty
        fetchAllClassesBoolean (True/False)
    
    Returns:
        tuple: Returns a tuple with classId, className, hasAttendanceTakenYet.
        False: If faculty has no classes, or an error occurs, False would be returned.
        
    Raises:
        aiomysql.MySQLError: If there's an issue with the database query.
    """
    
    db_connection = await get_db_connection()
    if db_connection:
        async with db_connection.cursor() as cursor:
            try: 
                query = f"""
                SELECT id, name 
                FROM classes 
                WHERE class_head_id = {facultyId} 
                OR (FIND_IN_SET({facultyId}, REPLACE(faculty_members_id, ' ', '')) > 0 AND is_restricted = 0)
                """ if not fetchAllClassesBoolean else 'SELECT id, name FROM classes'
        
                await cursor.execute(query)
                result = await cursor.fetchall()
                if result:
                    return result
                    
            except aiomysql.MySQLError as err:
                print(f"Error during authentication: {err}")
                return False
            finally:
                db_connection.close()
        
async def verifyClassPermission(classId: int, facultyId: int):
    if not classId:
        return False
    db_connection = await get_db_connection()
    
    if not db_connection:
        return False
    
    async with db_connection.cursor() as cursor:
        
        try:
            query = f"""
            SELECT id
            FROM classes 
            WHERE id = {classId} 
            AND (class_head_id = {facultyId} 
            OR (FIND_IN_SET({facultyId}, REPLACE(faculty_members_id, ' ', '')) > 0 AND is_restricted = 0))
            """
            
            await cursor.execute(query)
            result = await cursor.fetchone()
            
            if not result:
                return False
            
            return True
        
        except aiomysql.MySQLError as err:
            print(f"Error during authentication: {err}")
            return False
        finally: db_connection.close()
        
async def fetchFaculty():
    db_connection = await get_db_connection()
    if not db_connection:
        return False
    async with db_connection.cursor() as cursor:
        try: 
            facultyList = []
            query = """
            SELECT id, email, name, level FROM faculty
            """
            await cursor.execute(query)
            result = await cursor.fetchall()
            
            if not result:
                return facultyList
            
            for faculty in result:
                id, email, name, level = faculty
                facultyList.append({
                    'id': id,
                    'name': name,
                    'email': email,
                    'level': level,
                    'session': 0
                })
            
            query2 = """
                SELECT user_id FROM sessions
            """
            await cursor.execute(query2)
            result2 = await cursor.fetchall()
            
            if not result2:
                return facultyList
            
            for i in range(len(result2)):
                for userId in result2[i]:
                    for faculty in facultyList:
                        facultyId = int(faculty['id'])
                        if facultyId == userId:
                            faculty['session'] = 1 
            return facultyList
        
        except aiomysql.MySQLError as err:
            print(f"""Error in mysql, {err}""")
        finally: 
            db_connection.close()
            

async def removeFaculty(facultyId: int, userId: int, userLevel: int):
    if not facultyId or not userLevel:
        return False
    db_connection = await get_db_connection()
    if not db_connection:
        return False
    async with db_connection.cursor() as cursor:
        try:
            query = """
            SELECT level FROM faculty WHERE id = %s
            """
            await cursor.execute(query, (facultyId,))
            facultyLevel = await cursor.fetchone()
            
            if not facultyLevel:
                return False
            
            if facultyLevel[0] >= userLevel:
                return -1 
            
            isTokenRemove = await revokeToken(facultyId, userLevel, False)
            if not isTokenRemove:
                return False

            query2 = """
            DELETE FROM faculty WHERE id = %s
            """
            await cursor.execute(query2, (facultyId,))

            query3 = """
            SELECT id, faculty_members_id, class_head_id 
            FROM classes 
            WHERE class_head_id = %s 
            OR FIND_IN_SET(%s, REPLACE(faculty_members_id, ' ', '')) > 0
            """
            await cursor.execute(query3, (facultyId, facultyId))
            classes = await cursor.fetchall()
            
            for class_id, faculty_members_id, class_head_id in classes:
                if class_head_id == facultyId:
                    update_query = """
                    UPDATE classes
                    SET class_head_id = 0
                    WHERE id = %s
                    """
                    await cursor.execute(update_query, (class_id,))
                
                if facultyId in (faculty_members_id or "").split():
                    updated_faculty_list = [f for f in faculty_members_id.split() if f != str(facultyId)]
                    updated_faculty_members = " ".join(updated_faculty_list)
                    
                    update_query = """
                    UPDATE classes
                    SET faculty_members_id = %s
                    WHERE id = %s
                    """
                    await cursor.execute(update_query, (updated_faculty_members, class_id))
            
            await db_connection.commit()
            return True
            
        except aiomysql.MySQLError as err:
            print(f"Error in mysql: {err}")
        finally: 
            db_connection.close()
            
# if __name__ == "__main__":
#     """
#     Main function that runs the script to add a new staff member to the database.
#     """
#     asyncio.run(add_staff('Daksh Sharma', 8, '{}', 'test'))

if __name__ == "__main__":
    """
    Main function that runs the script to add a new staff member to the database.
    """
    # asyncio.run(authenticate('daksh100sharma@gmail.com', 'test'))
    #asyncio.run(add_staff('Darshan Soni', 'darshan@gmail.com', 1, '{}', 'test'))
    result = asyncio.run(fetchFaculty())
    print(result)