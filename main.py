from quart import Quart, render_template, redirect, url_for, request, session, jsonify, abort, g
import aiohttp
from faculty.utilities import authenticate, getClasses, verifyClassPermission, fetchFaculty, removeFaculty, addFaculty
from student.utilities import studentAPI
student_api = studentAPI
from attendance.utilities import attendanceAPI
attendance_api = attendanceAPI
from timeAPI.utilities import TimeAPI
time_api = TimeAPI()
from datetime import timedelta
import uuid
from session.utilities import cleanup_expired_tokens, verifyToken, revokeToken
from classes.utilities import fetchFullClasses, alterClass, deleteClass
import asyncio

app = Quart(__name__)
app.secret_key = 'portal@Daksh'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_SAMESITE'] = None
# app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=1440)


MOCK_API_URL = "https://jsonplaceholder.typicode.com/posts"

@app.before_request
async def sessionChecker():
    if not session.get('logged_in'):
        if request.path not in ['/', '/login']:
            return redirect(url_for('login'))
    
    if request.path in ['/', '/login']:
        return
    
    if not session.get('token'):
        return redirect(url_for('login'))
    
    result = await verifyToken(session.get('token'), session.get('userId'))
    
    if not result:
        return redirect(url_for('login'))
    
    return


@app.route('/')
async def home():
    return await render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
async def login():
    if session.get('token') and await verifyToken(session.get('token'), session.get('userId')):
        return redirect(url_for('portal'))
    if request.method == 'POST':
        form_data = await request.form
        email = form_data['email']
        password = form_data['password']

        result = await authenticate(email, password)

        if result:
            session_token, user_id, user_name, user_level = result
            session['token'] = session_token
            session['logged_in'] = True
            session['userName'] = user_name
            session['userId'] = user_id
            session['userLevel'] = user_level
            print(f"Session set: {session}")
            return redirect(url_for('portal'))
        else:
            print("Invalid credentials")
            return await render_template('login.html', error="Invalid credentials")

    return await render_template('login.html')

@app.route('/logout')
async def logout():
    if not session.get('logged_in'):
        return
    result = await revokeToken(session.get('userId'), session.get('userLevel'), True, session.get('token'))
    if not result:
        return jsonify({"error": "Error appeared while revoking your token at backend"}), 500
    session.clear() 
    return redirect(url_for('home'))

@app.route('/portal')
async def portal():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return await render_template('portal.html', userLevel=session.get('userLevel'))

@app.route('/class')
async def class_panel():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    class_id = request.args.get('classId')
    if not class_id:
        return jsonify({"error": "Missing required parameter"}), 400

    if not session.get('userLevel') >= 4:
        result = await verifyClassPermission(class_id, session.get('userId'))
    
        if not result:
            return redirect(url_for('portal'))
    
    return await render_template('class.html', class_id=class_id)

@app.route('/api/stats/class', methods=['POST'])
async def fetch_states():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    data = await request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    classId = data.get('classId')
    if not classId:
        return jsonify({"error": "Missing 'classId'"}), 400

    result = await attendance_api.classAnalysis(classId)
    if not result:
        return jsonify({'error': 'Error while fetching stats for class'}), 500
    return jsonify(result)
        
@app.route('/student')
async def student_panel():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if session.get('userLevel') <= 2:
        return jsonify({'error': 'Unauthorized access'}), 401
    
    student_id = request.args.get('studentId')
    if not student_id:
        return jsonify({"error": "Missing required parameter"}), 400
    
    return await render_template('student.html')

@app.route('/admin/addStudent')
async def student_add_panel():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if session.get('userLevel') <= 2:
        return jsonify({'error': 'Unauthorized access'}), 401
    
    return await render_template('managestudent.html')

@app.route('/admin/faculty')
async def staff_admin_panel():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized access'}), 401
    
    if not session.get('userLevel') >= 4:
        return redirect(url_for('portal'))
    
    return await render_template('adminStaff.html')

@app.route('/admin/class')
async def class_admin_panel():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized access'}), 401
    
    if not session.get('userLevel') >= 4:
        return redirect(url_for('portal'))
    
    return await render_template('adminClass.html')
    
# @app.route('/admin')
# async def admin_panel():
#     if not session.get('logged_in'):
#         return redirect(url_for('login'))
    
#     if session.get('userLevel') <= 2:
#         return redirect(url_for('portal'))

@app.route('/api/data')
async def get_mock_data():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized access'}), 401

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(MOCK_API_URL) as response:
                data = await response.json()
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    return jsonify(data)


@app.route('/api/stats/grand')
async def stats():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized access'}), 401
    
    data = await attendance_api.grandAnalysis()
    
    if data:
        return jsonify(data)


@app.route('/api/selfInfo')
async def fetchSelfInfo():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized access'}), 401
    data = {
        "id": session.get('userId'),
        "name": session.get('userName'),
        "level": session.get('userLevel')
    }
    return jsonify(data)

@app.route('/api/getClasses')
async def fetchUserClasses():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized access'}), 401
    
    fetchAllClassesBool = session.get('userLevel') >= 4
    
    result = await getClasses(session.get('userId'), fetchAllClassesBool)
    return jsonify(result)

@app.route('/api/fetchAttendance', methods=['POST'])
async def fetchAttendance():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized access'}), 401
    data = await request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    classId = data.get('classId')
    if not classId:
        return jsonify({"error": "Missing 'classId'"}), 400
    
    studentsList = await attendance_api.fetchAttendance(classId)
    return jsonify(studentsList)

@app.route('/api/postAttendance', methods=['POST'])
async def postAttendance():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized access'}), 401
    
    data = await request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    classId = data.get('classId')
    attendanceData = data.get('data')

    result = await attendance_api.registerAttendance(classId, attendanceData, session.get('userId'))
    
    if not result:
        return jsonify({'error': 'Error occured at backend'}), 200
    
    return jsonify({'success': 'Data was received by the server'}), 200


@app.route('/api/queryStudent', methods=['POST'])
async def queryStudent():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized access'}), 401
    
    data = await request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    idParam = data.get('id')
    nameParam = data.get('name')
    classParam = data.get('class')
    rollNoParam = data.get('rollNo')
    
    result = await student_api.queryStudents(idParam, nameParam, classParam, rollNoParam)
        
    return jsonify(result)

@app.route('/api/fetchStudentInfo', methods=['POST'])
async def fetchStudentInfo():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized access'}), 401
    
    data = await request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    studentId = data.get('studentId')
    result = await student_api.fetchStudentInfo(studentId)
    
    if not result:
        return jsonify({'error': 'Error at backend server while fetching student info'})
    
    return jsonify(result)

@app.route('/api/editStudent', methods=['POST'])
async def editStudnetInfo():
    if not session.get('logged_in') or session.get('userLevel') <= 2:
        return jsonify({'error': 'Unauthorized access'}), 401
        
    data = await request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    result = await student_api.editStudentInfo(data)
    if not result:
        return jsonify({'error': 'Error while updating the student info at backend'}), 500
    
    return jsonify({'success': 'done'}), 200

@app.route('/api/fetchFacultyInfo')
async def fetchFacultyInfo():
    if not session.get('logged_in') or session.get('userLevel') <= 3:
        return jsonify({'error': 'Unauthorized access'}), 401
    
    result = await fetchFaculty()
    if not result:
        return jsonify({'error': 'Error while fetching the faculty info at backend'}), 500
    return jsonify(result)

@app.route('/api/revokeToken', methods=['POST'])
async def revokeFacultyToken():
    if not session.get('logged_in') or session.get('userLevel') <= 3:
        return jsonify({'invalidPerms': 'User does not have the permission to execute this action'}), 401
    data = await request.get_json()
    facultyId = data.get('facultyId')
    if not data:
        return jsonify({'error': 'No faculty Id provided'}), 400
    result = await revokeToken(facultyId, session.get('userLevel'), False)
    if result == False:
        return jsonify({'error': 'Error while revoking faculty\'s token at backend'}), 500
    if result == -1:
        return jsonify({'invalidPerms': 'User does not have the permission to execute this action'}), 401
        
    return jsonify({'success': 'Facuty\'s token has been revoked successfully'}), 200

@app.route('/api/removeFaculty', methods=['POST'])
async def removeFacultyMember():
    if not session.get('logged_in') or session.get('userLevel') <= 3:
        return jsonify({'invalidPerms': 'User does not have the permission to execute this action'}), 401
    data = await request.get_json()
    facultyId = data.get('facultyId')
    if not data:
        return jsonify({'error': 'No faculty Id provided'}), 400
    result = await removeFaculty(facultyId, session.get('userId'), session.get('userLevel'))
    
    if result == False:
        return jsonify({'error': 'Error while revoking faculty\'s token at backend'}), 500
    if result == -1:
        return jsonify({'invalidPerms': 'User does not have the permission to execute this action'}), 401
        
    return jsonify({'success': 'Facuty\'s was removed successfully'}), 200

@app.route('/api/addFaculty', methods = ['POST'])
async def addFacultyMember():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized access'}), 401
    if session.get('userLevel') <= 3:
        return jsonify({'invalidPerms': 'User does not have the permission to execute this action'}), 401
    data = await request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    fName = data.get('fName')
    fLevel = data.get('fLevel')
    fEmail = data.get('fEmail')
    fPassword = data.get('fPassword')
    if not fName or not fLevel or not fEmail or not fPassword:
        return jsonify({'error', 'Not one or more data were provided'}), 400
    if fLevel >= session.get('userLevel'):
        return jsonify({'invalidPerms': 'User does not have the permission to execute this action'}), 401
    result = await addFaculty(fName, fEmail, fLevel, fPassword)
    if result == -2:
        return jsonify({'facultyAlreadyExists': 'Faculty does already exists'}), 401
    if result == False:
        return jsonify({'error': 'Error while adding faculty at backend'}), 500
    return jsonify({'success': 'Faculty has been added successfully'}), 200
    
@app.route('/api/fetchFullClasses')
async def fetch_full_classes():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized access'}), 401
    
    if session.get('userLevel') <= 3:
        return jsonify({'invalidPerms': 'User does not have the permission to execute this action'}), 401
    
    result = await fetchFullClasses()
    if not result:
        return jsonify({'error': 'Error occuered while fetching full classes at backend'}), 500
    return jsonify(result)

@app.route('/api/addClass', methods = ['POST'])
async def add_class():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized access'}), 401
    
    if session.get('userLevel') <= 3:
        return jsonify({'invalidPerms': 'User does not have the permission to execute this action'}), 401
    
    data = await request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    result = await alterClass(data, False) # data, isToEdit
    
    if result == False:
        return jsonify({'error': 'Error while editing class at backend'}), 500
    if result == -2:
        return jsonify({'noFacultyFound': 'Faculty members id include a wrong one that does not exists in faculty\'s data'}), 404
    if result == -3:
        return jsonify({'noCRFound': 'Class representative include a wrong one that does not exists in student\'s data'}), 404
    return jsonify({'success': 'Class was added successfully'}), 200

@app.route('/api/editClass', methods = ['POST'])
async def edit_class():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized access'}), 401
    
    if session.get('userLevel') <= 3:
        return jsonify({'invalidPerms': 'User does not have the permission to execute this action'}), 401
    
    data = await request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    result = await alterClass(data, True)
    if result == False:
        return jsonify({'error': 'Error while editing class at backend'}), 500
    if result == -1:
        return jsonify({'noClassFound': 'No class was found with that id'}), 404
    if result == -2:
        return jsonify({'noFacultyFound': 'Faculty members id include a wrong one that does not exists in faculty\'s data'}), 404
    if result == -3:
        return jsonify({'noCRFound': 'Class representative include a wrong one that does not exists in student\'s data'}), 404
    return jsonify({'success': 'Class was edited successfully'}), 200

@app.route('/api/deleteClass', methods = ['POST'])
async def delete_class():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized access'}), 401
    
    if session.get('userLevel') <= 3:
        return jsonify({'invalidPerms': 'User does not have the permission to execute this action'}), 401
    
    data = await request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    classId = data.get('classId')

    if not classId:
        return jsonify({'error': 'No class Id provided'}), 400
    
    result = await deleteClass(classId)
    if result == -1:
        return jsonify({'noClassFound': 'No class was found with that id'}), 404
    
    return jsonify({'success': 'Given class associated with the given ID was deleted'}), 200

@app.route('/api/addStudent', methods=['POST'])
async def add_student():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized access'}), 401
    
    if session.get('userLevel') <= 2:
        return jsonify({'invalidPerms': 'User does not have the permission to execute this action'}), 401
    
    data = await request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400   
    
    result = await student_api.addStudent(data)

    if result == -1:
        return jsonify({'noClassFound': 'Class with that ID could not be found'}), 404
    
    if not result:
        return jsonify({'error': 'Something went wrong on server while adding student'}), 500
    
    return jsonify({'success': 'Student was added successfully'}), 200

@app.route('/api/deleteStudent', methods = ['POST'])
async def delete_student():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized access'}), 401
    
    if session.get('userLevel') <= 2:
        return jsonify({'invalidPerms': 'User does not have the permission to execute this action'}), 401
    
    data = await request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    result = await student_api.deleteStudent(data)

    if result == -1:
        return jsonify({'noStudentIDFound': 'One or more student id was not found in the database'}), 404
    
    if result == False:
        return jsonify({'error': 'Unknown error occured while deleting the student(s)'}), 500
    
    return jsonify({'success': 'Student(s) with given ID(s) were deleted'})
    
async def start_cleanup_task():
    """Starts the cleanup task in the background."""
    asyncio.create_task(cleanup_expired_tokens())    

@app.before_serving
async def before_serving():
    """Run cleanup task before the server starts."""
    await start_cleanup_task()

if __name__ == "__main__":
    app.run(debug=True, port=5000, host='0.0.0.0')