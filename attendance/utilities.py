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

# 0 Absent
# 1 Present
# 2 On Leave
# 3 On Duty

class attendanceAPI: 
    async def fetchAttendance(classId: int):
        currentDate = time_api.current_date()
        
        db_connection = await get_db_connection()
        if db_connection:
            async with db_connection.cursor() as cursor:
                
                try:
                    query = f"""
                    SELECT id, name, roll_no, gender FROM students WHERE class_id = {classId}
                    """
                    
                    await cursor.execute(query)
                    students = await cursor.fetchall()
                    studentsList = []
                    if students:
                        for student in students:
                            id, name, roll_no, pre_gender = student
                            gender = int.from_bytes(pre_gender, byteorder='little') if student else None
                            studentsList.append({
                                'id': id,
                                'name': name,
                                'roll_no': roll_no,
                                'gender': gender,
                                'attendanceState': 1
                            })

                        query2 = f"""
                        SELECT data FROM calendar WHERE class_id = {classId} AND date = '{currentDate}'
                        """
                        
                        await cursor.execute(query2)
                        doneStudents = await cursor.fetchone()
                        
                        if doneStudents and doneStudents[0]:
                            processedDoneStudentsList = json.loads(doneStudents[0])
                            for eachJSON in processedDoneStudentsList:
                                studentId = int(eachJSON['id'])
                                studentAttendance = int(eachJSON['attendance'])
                                for mainStudent in studentsList:
                                    sId = int(mainStudent['id'])
                                    if sId == studentId:
                                        mainStudent['attendanceState'] = studentAttendance
                                        
                    return studentsList
                except aiomysql.MySQLError as err:
                    print(f"Error during authentication: {err}")
                    return False
                finally:
                    db_connection.close()
                    
    async def registerAttendance(classId: int, jsonAttendance, executedById: int):
        db_connection = await get_db_connection()
        if db_connection:
            async with db_connection.cursor() as cursor:
                try:
                    if isinstance(jsonAttendance, str):
                        processedAttendance = json.loads(jsonAttendance)
                    else:
                        processedAttendance = jsonAttendance
                    if not processedAttendance:
                        return False
                    
                    currentDate = time_api.current_date()
                    currentTime = time_api.current_time()

                    query = f"""
                    SELECT id FROM calendar WHERE class_id = {classId} AND date = '{currentDate}'
                    """
                    
                    await cursor.execute(query)
                    result = await cursor.fetchone()

                    if not result:
                        query2 = """
                        INSERT INTO calendar (executed_by_id, date, class_id, data, executed_at) VALUES (%s, %s, %s, %s, %s)
                        """
                        
                        await cursor.execute(query2, (executedById, currentDate, classId, json.dumps(processedAttendance), currentTime))
                        await db_connection.commit()
                        return True

                    query3 = """
                    UPDATE calendar SET last_edited_by_id = %s, data = %s, last_edited_at = %s WHERE class_id = %s AND date = %s
                    """
                    
                    await cursor.execute(query3, (executedById, json.dumps(processedAttendance), currentTime, classId, currentDate))
                    await db_connection.commit()
                    return True
                except aiomysql.MySQLError as err:
                    print(f"Error during attendance registration: {err}")
                    return False
                finally:
                    db_connection.close()
                    
    async def grandAnalysis():
        db_connection = await get_db_connection()
        if db_connection:
            async with db_connection.cursor() as cursor:
                try:
                    studentsPresent = 0
                    studentsAbsent = 0
                    studentsOnDuty = 0
                    studentsOnLeave = 0
                    
                    currentDate = time_api.current_date()

                    query = f"""
                    SELECT data FROM calendar WHERE date = '{currentDate}'
                    """
                    
                    await cursor.execute(query)
                    
                    result = await cursor.fetchall()
                    
                    if not result:
                        sampleData = {
                            'present': 25,
                            'absent': 25,
                            'onDuty': 25,
                            'onLeave': 25
                        }
                        return sampleData
                    
                    for row in result:
                        json_str = row[0]
                        
                        attendance_records = json.loads(json_str)
                        
                        for record in attendance_records:
                            attendance = record['attendance']
                            
                            if attendance == 0:
                                studentsAbsent += 1
                            elif attendance == 2:
                                studentsOnDuty += 1
                            elif attendance == 3:
                                studentsOnLeave += 1
                            else:
                                studentsPresent += 1
                    totalAttendanceSum = studentsPresent + studentsAbsent + studentsOnDuty + studentsOnLeave
                    studentsRatioPresent = studentsPresent / totalAttendanceSum * 100
                    studentsRatioAbsent = studentsAbsent / totalAttendanceSum * 100
                    studentsRatioOnDuty = studentsOnDuty / totalAttendanceSum * 100
                    studentsRatioOnLeave = studentsOnLeave / totalAttendanceSum * 100
                    
                    data = {
                        'present': studentsRatioPresent,
                        'absent': studentsRatioAbsent,
                        'onDuty': studentsRatioOnDuty,
                        'onLeave': studentsRatioOnLeave
                    }
                    return data
                except aiomysql.MySQLError as err:
                    print(f"""Error in MySQL, {err}""")
                    
    async def classAnalysis(classIdInput):
        try:
            classId = int(classIdInput)
        except ValueError:
            print("Invalid class ID")
            return False

        if not classId:
            print("Class ID is required")
            return -1
        
        db_connection = await get_db_connection()
        if not db_connection:
            print("Failed to connect to the database")
            return False

        async with db_connection.cursor() as cursor:
            try:
                previousweekEndDate = time_api.subtract_days(time_api.start_of_week()[0:10], 2)
                previousweekStartDate = time_api.subtract_days(previousweekEndDate, 5)
                allPreviousDatesList = time_api.get_all_dates_between(previousweekStartDate, previousweekEndDate)

                placeholders = ', '.join(['%s'] * len(allPreviousDatesList))
                query = """SELECT date, data FROM calendar WHERE class_id = %s AND date IN ({})""".format(placeholders)
                await cursor.execute(query, [classId] + allPreviousDatesList)

                result = await cursor.fetchall()

                result_dict = {}
                for row in result:
                    date = row[0]
                    data = row[1]
                    result_dict[date] = data

                days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

                attendanceData = []
                for i in range(len(allPreviousDatesList)):
                    date = allPreviousDatesList[i]
                    day_name = days_of_week[i]
                    day_data = result_dict.get(date, '[]')
                    attendanceData.append({day_name: day_data}) # Placing a cloth upon an old cloth, if they both match, put them in cupboard
                attendanceweeklyTrend = []
                
                for dayAttendance in attendanceData:
                    for day, attendance in dayAttendance.items():
                        attendance_list = eval(attendance)

                        totalPresentStudents = 0
                        totalAbsentStudents = 0
                        totalStudentsOnLeave = 0
                        
                        for student in attendance_list:
                            if student['attendance'] == 1 or student['attendance'] == 3:
                                totalPresentStudents += 1
                            elif student['attendance'] == 0:
                                totalAbsentStudents += 1
                            elif student['attendance'] == 2:
                                totalStudentsOnLeave += 1
                        totalStudents = len(attendance_list)
                        if totalStudents == 0:
                            attendancePercentage = 0
                        else:
                            attendancePercentage = (totalPresentStudents / totalStudents) * 10
                            
                        attendanceweeklyTrend.append(attendancePercentage)
                yesterdaysDate = time_api.get_yesterday()
                
                query2 = f"""SELECT data FROM calendar WHERE class_id = {classId} AND date = '{yesterdaysDate}'"""
                
                await cursor.execute(query2)
                result2 = await cursor.fetchone()
                
                data = {
                   'attendanceweeklyTrend': attendanceweeklyTrend,
                   'attendanceYesterdayData': [0, 100, 0] # Absent[0], Present (P + OD)[1+3], On Leave[2]
                }
                
                if not result2:
                    return data
                
                parsedJson = json.loads(result2[0])
                totalStudentsPresentYesterday = 0
                totalStudentsAbsentYesterday = 0
                totalStudentsOnLeaveYesterday = 0
                totalYesterdayStudents = len(parsedJson)
                for row in parsedJson:
                    if row['attendance'] == 1 or row['attendance'] == 3:
                        totalStudentsPresentYesterday += 1
                    elif row['attendance'] == 0:
                        totalStudentsAbsentYesterday += 1
                    elif row['attendance'] == 2:
                        totalStudentsOnLeaveYesterday += 1
                    
                if totalYesterdayStudents == 0:
                    return data
                
                data['attendanceYesterdayData'] = [
                    (totalStudentsPresentYesterday / totalYesterdayStudents) * 100,
                    (totalStudentsAbsentYesterday / totalYesterdayStudents) * 100,
                    (totalStudentsOnLeaveYesterday / totalYesterdayStudents) * 100
                    ]
                return data
            except Exception as err:
                print("Error:", err)
            finally:
                db_connection.close()

attendance_API = attendanceAPI

if __name__ == "__main__":
    """
    Main function that runs the script
    """

    # attendance_data = [
    #     {"id": "2", "attendance": "2"},
    #     {"id": "4", "attendance": "2"},
    #     {"id": "6", "attendance": "3"}
    # ]
    
    # json_data = json.dumps(attendance_data) 
    asyncio.run(attendance_API.classAnalysis(1))