from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import mysql.connector
import os
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this in production

# --- File Upload Config ---
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

ASSIGNMENT_FOLDER = os.path.join(app.config['UPLOAD_FOLDER'], 'assignments')
if not os.path.exists(ASSIGNMENT_FOLDER):
    os.makedirs(ASSIGNMENT_FOLDER)

# Update ALLOWED_EXTENSIONS if needed
ALLOWED_ASSIGNMENT_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}

def allowed_assignment_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_ASSIGNMENT_EXTENSIONS

# --- Database connection ---
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="eduvault"
)
cursor = db.cursor()

# -------------------- Routes --------------------

@app.route('/')
def index():
    return render_template('index.html')

# --- Student Login ---
@app.route('/student_login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor.execute("SELECT * FROM student WHERE username = %s AND password = %s", (username, password))
        student = cursor.fetchone()

        if student:
            session['student_id'] = student[0]
            return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid student credentials')
    return render_template('student/student_login.html')

# --- Teacher Login ---
@app.route('/teacher_login', methods=['GET', 'POST'])
def teacher_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor.execute("SELECT * FROM teacher WHERE username = %s AND password = %s", (username, password))
        teacher = cursor.fetchone()

        if teacher:
            session['teacher_id'] = teacher[0]
            session['teacher_username'] = username
            return redirect(url_for('teacher_dashboard'))
        else:
            flash('Invalid teacher credentials')
    return render_template('teacher/staff_login.html')

# --- Teacher Dashboard ---
@app.route('/teacher_dashboard', methods=['GET'])
def teacher_dashboard():
    if 'teacher_id' not in session:
        return redirect(url_for('teacher_login'))

    cursor.execute("SELECT * FROM study_materials")
    materials = cursor.fetchall()

    cursor.execute("SELECT * FROM videos")
    videos = cursor.fetchall()

    cursor.execute("SELECT * FROM tests")
    tests = cursor.fetchall()

    cursor.execute("SELECT * FROM assignments")
    assignments = cursor.fetchall()

    teacher_id = session['teacher_id']

    cursor.execute("SELECT username, department FROM teacher WHERE id = %s", (teacher_id,))
    user_data = cursor.fetchone()   

    username = user_data[0]
    department = user_data[1]

    return render_template('/teacher/OG_UI.html', materials=materials, videos=videos, tests=tests, assignments=assignments, username=username, department=department)

# --- Upload Study Material (POST only) ---
@app.route('/upload', methods=['POST'])
def upload():
    if 'teacher_id' not in session:
        return redirect(url_for('teacher_login'))

    if 'title' not in request.form or 'file' not in request.files:
        flash("Missing form data.")
        return redirect(url_for('teacher_dashboard'))

    title = request.form['title']
    description = request.form['description']
    file = request.files['file']

    if file and allowed_file(file.filename):
        original_filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))

        uploaded_by = session.get('teacher_username', 'Unknown')
        cursor.execute(
            "INSERT INTO study_materials (title, description, filename, uploaded_by) VALUES (%s, %s, %s, %s)",
            (title, description, unique_filename, uploaded_by)
        )
        db.commit()
        flash("Study material uploaded successfully.")
    else:
        flash("Invalid file format.")

    return redirect(url_for('teacher_dashboard'))

# --- Upload Video ---
@app.route('/upload_video', methods=['POST'])
def upload_video():
    if 'teacher_id' not in session:
        return redirect(url_for('teacher_login'))

    if 'title' not in request.form or 'file' not in request.files:
        flash("Missing form data.")
        return redirect(url_for('teacher_dashboard'))

    title = request.form['title']
    file = request.files['file']

    if file and file.filename.endswith(('.mp4', '.mov', '.avi')):
        original_filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))

        cursor.execute(
            "INSERT INTO videos (title, filename) VALUES (%s, %s)",
            (title, unique_filename)
        )
        db.commit()
        flash("Video uploaded successfully.")
    else:
        flash("Invalid video format.")

    return redirect(url_for('teacher_dashboard'))

# --- Delete Video ---
@app.route('/delete_video/<int:video_id>')
def delete_video(video_id):
    if 'teacher_id' not in session:
        return redirect(url_for('teacher_login'))

    cursor.execute("SELECT filename FROM videos WHERE id = %s", (video_id,))
    video = cursor.fetchone()

    if video:
        filename = video[0]
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            os.remove(file_path)

        cursor.execute("DELETE FROM videos WHERE id = %s", (video_id,))
        db.commit()
        flash("Video deleted successfully.")
    else:
        flash("Video not found.")

    return redirect(url_for('teacher_dashboard'))


# --- Upload Test ---
@app.route('/upload_test', methods=['POST'])
def upload_test():
    if 'teacher_id' not in session:
        return redirect(url_for('teacher_login'))

    if 'title' not in request.form or 'date' not in request.form or 'link' not in request.form:
        flash("Missing form data.")
        return redirect(url_for('teacher_dashboard'))

    title = request.form['title']
    date = request.form['date']
    link = request.form['link']

    cursor.execute(
        "INSERT INTO tests (title, date, link) VALUES (%s, %s, %s)",
        (title, date, link)
    )
    db.commit()
    flash("Test uploaded successfully.")

    return redirect(url_for('teacher_dashboard'))

@app.route('/upload_assignment', methods=['POST'])
def upload_assignment():
    if 'teacher_id' not in session:
        return redirect(url_for('teacher_login'))

    title = request.form['title']
    given_date = request.form['given_date']
    last_date = request.form['last_date']
    uploaded_by = session.get('teacher_username', 'Unknown')

    cursor.execute(
        "INSERT INTO assignments (title, given_date, last_date, uploaded_by) VALUES (%s, %s, %s, %s)",
        (title, given_date, last_date, uploaded_by)
    )
    db.commit()
    flash("Assignment uploaded successfully.")

    return redirect(url_for('teacher_dashboard'))

# --- Student Dashboard ---
@app.route('/student_dashboard')
def student_dashboard():
    if 'student_id' not in session:
        return redirect(url_for('student_login'))

    cursor.execute("SELECT * FROM study_materials")
    materials = cursor.fetchall()

    cursor.execute("SELECT * FROM videos")
    videos = cursor.fetchall()

    cursor.execute("SELECT * FROM tests")
    tests = cursor.fetchall()

    cursor.execute("SELECT * FROM assignments")
    assignments = cursor.fetchall()

    student_id = session['student_id']

    cursor.execute("SELECT username, department FROM student WHERE id = %s", (student_id,))
    user_data = cursor.fetchone()

    username = user_data[0]
    department = user_data[1]

    return render_template('/student/student_og_uii.html', materials=materials, videos=videos, tests=tests, assignments=assignments, username=username, department=department)

# --- Serve Uploaded Files ---
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'teacher_id' not in session:
        return redirect(url_for('teacher_login'))

    cursor = db.cursor()
    teacher_id = session['teacher_id']

    if request.method == 'POST':
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        email = request.form['email']
        department = request.form['department']

        cursor.execute("""
            UPDATE teacher
            SET firstname = %s, lastname = %s, email = %s, department = %s
            WHERE id = %s
        """, (firstname, lastname, email, department, teacher_id))

        db.commit()
        flash("Profile updated successfully.")
        return redirect(url_for('teacher_dashboard'))

    cursor.execute("SELECT * FROM teacher WHERE id = %s", (teacher_id,))
    teacher = cursor.fetchone()

    return render_template('/teacher/index.html', teacher=teacher)

@app.route('/profiles', methods=['GET', 'POST'])
def profiles():
    if 'student_id' not in session:
        return redirect(url_for('student_login'))

    cursor = db.cursor()
    student_id = session['student_id']

    if request.method == 'POST':
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        email = request.form['email']
        department = request.form['department']

        cursor.execute("""
            UPDATE student
            SET firstname = %s, lastname = %s, email = %s, department = %s
            WHERE id = %s
        """, (firstname, lastname, email, department, student_id))

        db.commit()
        flash("Profile updated successfully.")
        return redirect(url_for('student_dashboard'))

    cursor.execute("SELECT * FROM student WHERE id = %s", (student_id,))
    student = cursor.fetchone()

    return render_template('/student/index.html', student=student)

# --- Logout (both) ---
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
