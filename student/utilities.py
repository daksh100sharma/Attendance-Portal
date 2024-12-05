import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
import asyncio
from db.db_connection import get_db_connection
import aiomysql
import bcrypt
from flask import jsonify
import json

from timeAPI.utilities import TimeAPI

time_api = TimeAPI()

class studentAPI:
    async def queryStudents(sid, sname, sclass, srollNo):
        db_connection = await get_db_connection()
        if not db_connection:
            return False
        
        query = "SELECT id, name, roll_no, class_name, class_id FROM students WHERE 1=1" 

        parameters = []
        
        studentList = []

        if sid != 'skipped' and sid != '':
            query += " AND id = %s"
            parameters.append(sid)
        
        if sname != 'skipped' and sname != '':
            query += " AND name LIKE %s"
            parameters.append(f"%{sname}%")
        
        if sclass != 'skipped' and sclass != '':
            query += " AND class_name LIKE %s"
            parameters.append(f"%{sclass}%")

        if srollNo != 'skipped' and srollNo != '':
            query += " AND roll_no = %s"
            parameters.append(srollNo)
        
        try:
            async with db_connection.cursor() as cursor:
                await cursor.execute(query, parameters)
                result = await cursor.fetchall()
                for student in result:
                    id, name, rollNo, className, classId = student
                    studentList.append({
                        'id': id,
                        'name': name,
                        'class_name': className,
                        'class_id': classId,
                        'roll_no': rollNo
                    })
            return studentList
        except aiomysql.MySQLError as err:
            print(f"Error occurred in MySQL: {err}")
            return False
        finally:
            db_connection.close()
            
    async def fetchStudentInfo(studentId: int):
        if not studentId:
            return False
        db_connection = await get_db_connection()
        if not db_connection:
            return False
        async with db_connection.cursor() as cursor:
            try: 
                studentInfo = []
                currentDate = time_api.current_date()
                query = f"""
                SELECT * FROM students WHERE id = {studentId}
                """
                await cursor.execute(query)
                result = await cursor.fetchone()
                
                if not result:
                    return False
                
                id, name, roll_no, info, pre_gender, class_name, class_id = result
                gender = int.from_bytes(pre_gender, byteorder='little') if result else None
                
                studentInfo.append({
                    'id': id,
                    'name': name,
                    'roll_no': roll_no,
                    'data': info,
                    'gender': gender,
                    'class_name': class_name,
                    'class_id': class_id,
                    'attendanceState': 'Absent'
                })
                
                query2 = f"""
                SELECT data FROM calendar WHERE class_id = {class_id} AND date = '{currentDate}'
                """
                
                await cursor.execute(query2)
                result2 = await cursor.fetchone()
                
                if not result2:
                    return studentInfo
                
                parsedJSON = json.loads(result2[0])
                for student in parsedJSON:
                    id = student['id']
                    if id == studentId:
                        attendance = int(student['attendance'])
                        studentInfo[0]['attendanceState'] = attendance
                return studentInfo
            except aiomysql.MySQLError as err:
                print(f"""Error in mysql, {err}""")
                return False
            finally:
                db_connection.close()
                
    async def editStudentInfo(objData):
        if not objData:
            return False
        id = objData['id']
        name = objData['name']
        roll_no = objData['roll_no']
        class_id = objData['class_id']
        additional_data = objData['additional_data']
        db_connection = await get_db_connection()
        if not db_connection:
            return False
        async with db_connection.cursor() as cursor:
            try:                
                query = f"""
                SELECT name FROM classes WHERE id = {class_id}
                """
                await cursor.execute(query)
                className = await cursor.fetchone()
                if not className:
                    return False
                additional_data_str = json.dumps(additional_data)
                query2 = """
                UPDATE students
                SET name = %s, roll_no = %s, info = %s, class_id = %s, class_name = %s
                WHERE id = %s
                """
                await cursor.execute(query2, (name, roll_no, additional_data_str, class_id, className, id))

                await db_connection.commit()
                return True
            except aiomysql.MySQLError as err:
                print(f"""Error in mysql, {err}""")
                return False
            finally:
                db_connection.close()
    async def addStudent(objData):
        if not objData:
            return False

        name = objData['name']
        class_id = objData['class_id']
        additional_data = objData['additional_data']
        genderText = objData['gender']
        gender = None
        if genderText == 'Female':
            gender = 0
        if genderText == 'Male':
            gender = 1


        db_connection = await get_db_connection()
        if not db_connection:
            return False
        
        async with db_connection.cursor() as cursor:
            try:
                query_check_class = "SELECT name FROM classes WHERE id = %s"
                await cursor.execute(query_check_class, (class_id,))
                class_row = await cursor.fetchone()

                if not class_row:
                    return -1 
                
                class_name = class_row[0]

                query_latest_roll = """
                SELECT COALESCE(MAX(roll_no), 0) + 1 AS next_roll_no
                FROM students
                WHERE class_id = %s
                """
                await cursor.execute(query_latest_roll, (class_id,))
                next_roll_no_row = await cursor.fetchone()
                next_roll_no = next_roll_no_row[0]

                additional_data_str = json.dumps(additional_data)

                query_insert_student = """
                INSERT INTO students (name, roll_no, info, class_id, class_name, gender)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                await cursor.execute(query_insert_student, (name, next_roll_no, additional_data_str, class_id, class_name, gender))

                await db_connection.commit()
                return True
            
            except aiomysql.MySQLError as err:
                print(f"Error in MySQL: {err}")
                return False
            
            finally:
                db_connection.close()
                
    async def deleteStudent(data):
        if 'ids' not in data or not isinstance(data['ids'], list):
            return False

        student_ids = []
        for student_id in data['ids']:
            try:
                student_ids.append(int(student_id))
            except ValueError:
                continue

        if not student_ids:
            return False  
        
        db_connection = await get_db_connection()
        if not db_connection:
            return False

        async with db_connection.cursor() as cursor:
            try:
                await db_connection.begin()
                
                for student_id in student_ids:
                    await cursor.execute("""
                        SELECT id, name, roll_no, info, gender, class_name, class_id
                        FROM students WHERE id = %s
                    """, (student_id,))
                    student_row = await cursor.fetchone()

                    if not student_row:
                        await db_connection.rollback()
                        return -1

                    await cursor.execute("""
                        INSERT INTO ex_students (id, name, roll_no, info, gender, class_name, class_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (student_row[0], student_row[1], student_row[2], student_row[3], student_row[4], student_row[5], student_row[6]))

                    await cursor.execute("DELETE FROM students WHERE id = %s", (student_id,))

                await db_connection.commit()
                return True

            except aiomysql.MySQLError as err:
                print(f"Error in MySQL: {err}")
                await db_connection.rollback()
                return False

            finally:
                db_connection.close()
                                
studnet_api = studentAPI
# if __name__ == "__main__":
#     """
#     Main function that runs the script
#     """
#     asyncio.run(studnet_api.editStudentInfo({'name': 'Alice Johnson', 'roll_no': '101', 'class_id': '1', 'additional_data': {'age': '15', 'hobbies': 'reading,swimming'}}))