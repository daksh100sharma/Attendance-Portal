import asyncio
from db.db_connection import get_db_connection
import aiomysql
import bcrypt
from flask import jsonify
import uuid
from session.utilities import revokeToken

async def fetchFullClasses():
    db_connection = await get_db_connection()
    if not db_connection:
        return False
    async with db_connection.cursor() as cursor:
        try:
            classList = []
            studentsList = []
            facultyList = []
            query = """
            SELECT id, name, is_restricted, faculty_members_id, class_head_id, class_representative_id FROM classes
            """
            await cursor.execute(query)
            result = await cursor.fetchall()
            if not result:
                return False
            for eachClass in result:
                id, name, raw_is_restricted, faculty_members_id, class_head_id, class_representative_id = eachClass
                is_restricted = int.from_bytes(raw_is_restricted, byteorder='little') if raw_is_restricted else None
                classList.append({
                    'id': id,
                    'name': name,
                    'is_restricted': is_restricted,
                    'faculty_members_id': faculty_members_id,
                    'class_head_id': class_head_id,
                    'class_representative_id': class_representative_id
                })
                
            query3 = """
            SELECT id, name FROM faculty
            """
            await cursor.execute(query3)
            result2 = await cursor.fetchall()
            
            if not result2:
                return False
            
            for faculty in result2:
                fid, fname = faculty
                facultyList.append({
                    'id': fid,
                    'name': fname
                })
                
            for eachClass in classList:
                facultyMembersId = eachClass['faculty_members_id'].replace(' ', '').split(',')
                classHeadId = eachClass['class_head_id']
                row = []
                
                class_head_set = False
                for faculty in facultyList:
                    facultyId = faculty['id']
                    facultyName = faculty['name']
                    if int(classHeadId) == int(facultyId):
                        eachClass['class_head_id'] = f"{facultyName}[{classHeadId}]"
                        class_head_set = True
                        break
                
                if not class_head_set:
                    eachClass['class_head_id'] = f"Unknown[{classHeadId}]"

                for i, specificFacultyMemberId in enumerate(facultyMembersId):
                    found = False
                    for faculty in facultyList:
                        facultyId = faculty['id']
                        if int(specificFacultyMemberId) == int(facultyId):
                            row.append(f" {faculty['name']}[{specificFacultyMemberId}] ")
                            found = True
                            break
                    
                    if not found:
                        row.append(f" Unknown[{specificFacultyMemberId}]")
                    
                eachClass['faculty_members_id'] = row
                
            return classList
            
        except aiomysql.MySQLError as err:
            print(f"Error in mysql, {err}")
        finally:
            db_connection.close()

            
async def alterClass(data, isToEdit: bool):
    if not data:
        return False
    class_name = data['className']
    class_head_id = data['class_head_id']
    faculty_members_id = data['faculty_members_id']
    class_representative_id = data['class_representative_id']
    facultyMembersList = faculty_members_id.replace(' ', '').split(',')
    
    db_connection = await get_db_connection()
    if not db_connection:
        return False

    async with db_connection.cursor() as cursor:
        try:
            placeholders = ','.join(['%s'] * len(facultyMembersList))
            query2 = f"SELECT id FROM faculty WHERE id IN ({placeholders})"
            await cursor.execute(query2, facultyMembersList)
            valid_faculty_ids = [row[0] for row in await cursor.fetchall()] 

            if len(facultyMembersList) != len(valid_faculty_ids):
                return -2

            updated_faculty_ids = ','.join(str(id) for id in valid_faculty_ids)

            if isToEdit:
                query3 = "SELECT name FROM students WHERE id = %s"
                await cursor.execute(query3, (class_representative_id,))
                result2 = await cursor.fetchone()

                if not result2:
                    return -3
                
            if isToEdit:
                query1 = "SELECT name FROM classes WHERE id = %s"
                await cursor.execute(query1, (data['classId'],))
                result = await cursor.fetchone()

                if not result:
                    return -1 

                query4 = """
                UPDATE classes SET name = %s, faculty_members_id = %s, class_head_id = %s, class_representative_id = %s WHERE id = %s
                """
                await cursor.execute(query4, (class_name, updated_faculty_ids, class_head_id, class_representative_id, data['classId']))
            else:
                query4 = """
                INSERT INTO classes (name, faculty_members_id, class_head_id, class_representative_id)
                VALUES (%s, %s, %s, %s)
                """
                await cursor.execute(query4, (class_name, updated_faculty_ids, class_head_id, class_representative_id))

            await db_connection.commit()
            return True

        except aiomysql.MySQLError as err:
            print(f"Error in MySQL: {err}")
            return False
        finally:
            db_connection.close()

async def deleteClass(strClassId):
    if not strClassId:
        return False
    classId = None
    try: classId = int(strClassId)
    except ValueError as err:
        return -1
    if not classId:
        return False
    db_connection = await get_db_connection()
    if not db_connection:
        return False
    async with db_connection.cursor() as cursor:
        try: 
            query = """
            SELECT name FROM classes WHERE id = %s
            """
            await cursor.execute(query, (classId))
            result = await cursor.fetchone()
            if not result:
                return -1
            query2 = """
            DELETE FROM classes WHERE id = %s
            """
            await cursor.execute(query2, (classId))
            query3 = """
            SELECT id FROM students WHERE class_id = %s
            """
            await cursor.execute(query3, (classId))
            studentIds = await cursor.fetchall()
            studentIdsList = [row[0] for row in studentIds]
            if not studentIdsList:
                return True
            if studentIdsList:
                placeholders = ','.join(['%s'] * len(studentIdsList))
                queryInsert = f"""
                INSERT INTO ex_students (id, name, roll_no, info, gender, class_name, class_id)
                SELECT id, name, roll_no, info, gender, class_name, class_id
                FROM students
                WHERE id IN ({placeholders})
                """
                await cursor.execute(queryInsert, studentIdsList)
                queryDelete = f"""
                DELETE FROM students
                WHERE id IN ({placeholders})
                """
                await cursor.execute(queryDelete, studentIdsList)
            await db_connection.commit()
            return True
        except aiomysql.MySQLError as err:
            print(f"""Error in mysql, {err}""")
            return False
        finally:
            db_connection.close()


if __name__ == "__main__":
    """
    Main function that runs the script to add a new staff member to the database.
    """
    result = asyncio.run(fetchFullClasses())