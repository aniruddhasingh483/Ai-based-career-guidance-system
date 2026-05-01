import os
import json
import sqlite3
import PyPDF2
import openai
import ollama

from datetime import datetime
from dotenv import load_dotenv
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt   # ✅ FIXED

UPLOAD_FOLDER = 'uploads'

# 👉 यह automatically folder बना देगा
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
import PyPDF2

def extract_text_from_pdf(filepath):
    text = ""
    with open(filepath, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text()
    return text.lower()



# Load environment variables
load_dotenv()

# --- Flask App Configuration ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'career_ai_secret_key_2025')
app.config['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')

# --- Extensions Setup ---
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# --- User Model and Loader ---
class User(UserMixin):
    def __init__(self, id, username, email, password_hash, is_admin):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.is_admin = is_admin

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    if user_data:
        return User(
            id=user_data['id'],
            username=user_data['username'],
            email=user_data['email'],
            password_hash=user_data['password_hash'],
            is_admin=user_data['is_admin']
        )
    return None

# Initialize OpenAI client globally for resume analysis
openai_client = None
if app.config.get('OPENAI_API_KEY'):
    openai_client = openai.OpenAI(api_key=app.config['OPENAI_API_KEY'])

from models.career_chatbot import CareerChatbot

# --- Database Helper Functions ---
def calculate_match_score(user_interests, text):
    score = 0
    for interest in user_interests:
        if interest.lower() in text.lower():
            score += 15
    return min(score, 100)

def get_db_connection():
    """Safe database connection"""
    db_path = app.config.get('DATABASE', 'career_guide.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# Initialize chatbot
career_bot = CareerChatbot(get_db_connection)

# --- Admin Decorator ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Admin access required!", "danger")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# ================= GAMIFICATION HELPERS =================

def add_points(user_id, points):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_points WHERE user_id = ?", (user_id,))
    user_points = cursor.fetchone()
    if user_points:
        cursor.execute("UPDATE user_points SET points = points + ? WHERE user_id = ?", (points, user_id))
    else:
        cursor.execute("INSERT INTO user_points (user_id, points) VALUES (?, ?)", (user_id, points))
    conn.commit()
    conn.close()

def award_badge(user_id, badge_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT badge_id FROM badges WHERE badge_name = ?", (badge_name,))
    badge = cursor.fetchone()
    if badge:
        badge_id = badge['badge_id']
        cursor.execute("SELECT * FROM user_badges WHERE user_id = ? AND badge_id = ?", (user_id, badge_id))
        user_badge = cursor.fetchone()
        if not user_badge:
            cursor.execute("INSERT INTO user_badges (user_id, badge_id) VALUES (?, ?)", (user_id, badge_id))
            conn.commit()
            flash(f'Congratulations! You have earned the "{badge_name}" badge!', 'success')
    conn.close()

@app.route('/api/user/gamification_stats')
@login_required
def gamification_stats():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get points
    cursor.execute("SELECT points FROM user_points WHERE user_id = ?", (current_user.id,))
    points_row = cursor.fetchone()
    points = points_row['points'] if points_row else 0

    # Get badges
    cursor.execute("""
        SELECT b.badge_name, b.badge_description, b.badge_icon
        FROM user_badges ub
        JOIN badges b ON ub.badge_id = b.badge_id
        WHERE ub.user_id = ?
    """, (current_user.id,))
    badges = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return jsonify({'points': points, 'badges': badges})


# ================= DASHBOARD API =================

@app.route('/api/dashboard/chat_activity')
@login_required
def chat_activity():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Get chat activity for the last 7 days
    cursor.execute("""
        SELECT DATE(timestamp) as date, COUNT(*) as count
        FROM chat_history
        WHERE user_id = ? AND timestamp >= DATE('now', '-7 days')
        GROUP BY DATE(timestamp)
        ORDER BY DATE(timestamp) ASC
    """, (current_user.id,))
    activity = cursor.fetchall()
    conn.close()

    data = {str(i): 0 for i in range(7)} # Initialize with 0 for the last 7 days
    from datetime import date, timedelta
    today = date.today()
    dates = { (today - timedelta(days=i)).strftime('%Y-%m-%d') : i for i in range(7) }

    for row in activity:
        if row['date'] in dates:
            data[str(dates[row['date']])] = row['count']

    # We need to return labels and data separately for Chart.js
    labels = [(today - timedelta(days=i)).strftime('%a') for i in range(6, -1, -1)]
    chart_data = [data[str(i)] for i in range(6, -1, -1)]

    return jsonify({'labels': labels, 'data': chart_data})


@app.route('/api/dashboard/saved_items_stats')
@login_required
def saved_items_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT item_type, COUNT(*) as count FROM saved_recommendations WHERE user_id = ? GROUP BY item_type", (current_user.id,))
    stats = cursor.fetchall()
    conn.close()

    data = {'course': 0, 'job': 0, 'exam': 0}
    for row in stats:
        data[row['item_type']] = row['count']

    return jsonify(data)

# ================= MAIN ROUTES =================

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Dynamic Greeting
    hour = datetime.now().hour
    if 5 <= hour < 12:
        greeting = "Good Morning"
    elif 12 <= hour < 18:
        greeting = "Good Afternoon"
    else:
        greeting = "Good Evening"

    # Profile Completion
    profile_completion = 50  # Base completion
    resume_path = f'uploads/user_{current_user.id}_resume.pdf'
    if os.path.exists(resume_path):
        profile_completion = 100

    # Saved items count
    cursor.execute("SELECT item_type, COUNT(*) as count FROM saved_recommendations WHERE user_id=? GROUP BY item_type",
                   (current_user.id,))
    counts = cursor.fetchall()
    saved_counts = {'course': 0, 'exam': 0, 'job': 0}
    for row in counts:
        saved_counts[row['item_type']] = row['count']

    # Recent saves
    cursor.execute("SELECT * FROM saved_recommendations WHERE user_id=? ORDER BY id DESC LIMIT 3",
                   (current_user.id,))
    recent_saves = cursor.fetchall()
    recent_items = []

    for item in recent_saves:
        if item['item_type'] == 'course':
            cursor.execute("SELECT course_id, course_name as title, field as subtitle FROM courses WHERE course_id=?",
                           (item['item_id'],))
        elif item['item_type'] == 'exam':
            cursor.execute("SELECT exam_id, exam_name as title, conducting_body as subtitle FROM exams WHERE exam_id=?",
                           (item['item_id'],))
        elif item['item_type'] == 'job':
            cursor.execute("SELECT job_id, job_title as title, company_sector as subtitle FROM jobs WHERE job_id=?",
                           (item['item_id'],))

        details = cursor.fetchone()
        if details:
            recent_items.append({
                'id': details[0],
                'title': details['title'],
                'subtitle': details['subtitle'],
                'item_type': item['item_type']
            })

    conn.close()
    return render_template('dashboard.html',
                           greeting=greeting,
                           profile_completion=profile_completion,
                           saved_counts=saved_counts,
                           recent_items=recent_items)

@app.route('/assessment')
@login_required
def assessment():
    return render_template('index.html')

# ================= RESUME UPLOAD =================


@app.route('/upload_resume', methods=['GET', 'POST'])
@login_required
def upload_resume():

    if request.method == 'POST':
        file = request.files['resume']

        if file:
            filename = f"user_{current_user.id}_resume.pdf"
            filepath = os.path.join('uploads', filename)

            os.makedirs('uploads', exist_ok=True)   # 🔥 important
            file.save(filepath)

            # 👉 extract text
            resume_text = extract_text_from_pdf(filepath)

            # 👉 session me store karo
            session['resume_text'] = resume_text

            return redirect(url_for('recommend'))   # 👉 direct recommendation page

    return render_template('upload_resume.html')

# ================= RECOMMENDATION SYSTEM =================
def calculate_score(item, user_input, interests):
    score = 0

    if user_input.get("stream") and item.get("stream"):
        if user_input["stream"].lower() in item["stream"].lower():
            score += 30

    if user_input.get("budget") and item.get("fees"):
        if int(item["fees"]) <= int(user_input["budget"]):
            score += 20

    if item.get("skills_required"):
        skills = item["skills_required"].lower()
        for interest in interests:
            if interest.lower() in skills:
                score += 10

    return score

@app.route('/recommend', methods=['GET', 'POST'])
@login_required
def recommend():

    conn = sqlite3.connect('career_guide.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    resume_text = session.get('resume_text', "")

    interests = []

    if "python" in resume_text:
        interests.append("python")
    if "ai" in resume_text:
        interests.append("ai")
    if "machine learning" in resume_text:
        interests.append("machine learning")
    if "web" in resume_text:
        interests.append("web development")

    if not interests:
        interests = ["coding"]

    user_interests_list = ", ".join(interests)

    user_input = {
        "education": "12th",
        "stream": "science",
        "budget": 200000
    }

    cursor.execute("SELECT * FROM courses")
    courses = cursor.fetchall()

    course_recommendations = []

    for c in courses:
        course_dict = dict(c)

        score = 0
        for skill in interests:
            if skill in course_dict.get("skills_required", "").lower():
                score += 30

        if score > 0:
            course_dict["match_score"] = score
            course_dict["explanation"] = "Matched from your resume skills"
            course_recommendations.append(course_dict)

    course_recommendations = sorted(course_recommendations, key=lambda x: x["match_score"], reverse=True)

    conn.close()

    return render_template("results.html",
        course_recommendations=course_recommendations,
        job_recommendations=[],
        exam_recommendations=[],
        user_input=user_input,
        user_interests_list=user_interests_list
    )

   
# ================= BROWSE PAGES =================

@app.route('/courses')
@login_required
def courses():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM courses ORDER BY course_id DESC")
    all_courses = cursor.fetchall()
    conn.close()
    return render_template('courses.html', courses=all_courses)

@app.route('/exams')
@login_required
def exams():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM exams ORDER BY exam_id DESC")
    all_exams = cursor.fetchall()
    conn.close()
    return render_template('exams.html', exams=all_exams)

@app.route('/jobs')
@login_required
def jobs():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs ORDER BY job_id DESC")
    all_jobs = cursor.fetchall()
    conn.close()
    return render_template('jobs.html', jobs=all_jobs)

@app.route('/course/<int:course_id>')
@login_required
def course_details(course_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM courses WHERE course_id = ?", (course_id,))
    course = cursor.fetchone()
    conn.close()
    return render_template('course_details.html', course=course)

@app.route('/job/<int:job_id>')
@login_required
def job_details(job_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
    job = cursor.fetchone()
    conn.close()
    return render_template('job_details.html', job=job)

@app.route('/exam/<int:exam_id>')
@login_required
def exam_details(exam_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM exams WHERE exam_id = ?", (exam_id,))
    exam = cursor.fetchone()
    conn.close()
    return render_template('exam_details.html', exam=exam)

@app.route('/about')
@login_required
def about():
    return render_template('about.html')

@app.route('/chat_full_page')
@login_required
def chat_full_page():
    return render_template('chat_full_page.html')

@app.route('/api/process_resume', methods=['POST'])
@login_required
def process_resume():
    data = request.get_json(force=True, silent=True)
    if not data or 'resume_path' not in data:
        return jsonify({"error": "No resume_path provided"}), 400

    resume_path = data.get('resume_path')
    full_resume_path = os.path.join(app.root_path, resume_path) # Ensure absolute path

    if not os.path.exists(full_resume_path):
        return jsonify({"error": "Resume file not found."}), 404

    try:
        # Extract text from PDF
        pdf_text = ""
        with open(full_resume_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page_num in range(len(reader.pages)):
                pdf_text += reader.pages[page_num].extract_text() + "\n"

        if not pdf_text.strip():
            return jsonify({"error": "Could not extract text from PDF. Please ensure it's a readable PDF."}), 400

        # Prepare prompt for OpenAI
        resume_analysis_prompt = f"""
        You are an expert career counselor. Analyze the following resume text and provide personalized career recommendations, including potential job roles, industries, and skills to develop. Also, highlight strengths and areas for improvement based on the resume.

        Resume Text:
        {pdf_text}

        Please provide a comprehensive and encouraging response, structured with headings and bullet points.
        """

        # Call OpenAI API for analysis
        messages = [
            {"role": "system", "content": "You are an expert career counselor analyzing resumes."},
            {"role": "user", "content": resume_analysis_prompt}
        ]

        if not openai_client:
            return jsonify({"error": "OpenAI API client not initialized."}), 500

        resp = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=1500, # Increased max_tokens for detailed resume analysis
            temperature=0.7, # Slightly more creative for recommendations
        )

        if resp and hasattr(resp, 'choices') and len(resp.choices) > 0 and hasattr(resp.choices[0], 'message') and hasattr(resp.choices[0].message, 'content'):
            analysis_result = str(resp.choices[0].message.content).strip()
            return jsonify({"answer": analysis_result}), 200
        else:
            print(f"OpenAI API returned an unexpected response format for resume analysis: {resp}")
            return jsonify({"error": "OpenAI did not return a valid response for resume analysis."}), 500

    except PyPDF2.errors.PdfReadError as e:
        return jsonify({"error": f"Failed to read PDF: {str(e)}. Is it a valid PDF?"}), 400
    except Exception as e:
        print(f"Error during resume processing: {e}")
        return jsonify({"error": f"An unexpected error occurred during resume analysis: {str(e)}"}), 500

# ================= CHATBOT API =================
@app.route('/api/roadmap', methods=['POST'])
@login_required
def roadmap():

    career = request.json.get('career')

    resume_text = session.get('resume_text', "")

    prompt = f"""
    User Resume:
    {resume_text}

    Create a personalized step-by-step roadmap to become a {career}
    based on user's current skills.
    """

    response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )

    return jsonify({
        "roadmap": response.choices[0].message.content
    })

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():

    data = request.get_json(force=True, silent=True)
    if not data or 'message' not in data:
        return jsonify({"error": "No message provided"}), 400

    user_message = data.get('message', '').strip()
    if user_message == "":
        return jsonify({"error": "Empty message"}), 400

    try:
        # 👉 STEP 1: Resume text lo
        resume_text = session.get('resume_text', "")

        # 👉 STEP 2: Resume + user message combine karo
        enhanced_prompt = f"""
        User Resume:
        {resume_text}

        User Question:
        {user_message}

        Give personalized career advice based on user's skills, education, and interests.
        """

        # 👉 STEP 3: AI response generate karo
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a career guidance expert."},
                {"role": "user", "content": enhanced_prompt}
            ]
        )

        answer = response.choices[0].message.content

        # 👉 STEP 4: Chat history save karo
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO chat_history (user_id, sender, message) VALUES (?, ?, ?)",
            (current_user.id, 'user', user_message)
        )
        cursor.execute(
            "INSERT INTO chat_history (user_id, sender, message) VALUES (?, ?, ?)",
            (current_user.id, 'bot', answer)
        )

        conn.commit()

        # 👉 STEP 5: Gamification
        add_points(current_user.id, 1)

        cursor.execute("SELECT COUNT(*) FROM chat_history WHERE user_id = ?", (current_user.id,))
        chat_count = cursor.fetchone()[0]

        if chat_count >= 20:
            award_badge(current_user.id, 'Chatterbox')

        conn.close()

        return jsonify({"answer": answer}), 200

    except Exception as e:
        print("Chat API error:", e)

        # 👉 fallback (resume bhi include karo)
        resume_text = session.get('resume_text', "")

        fallback = f"""
        Based on your resume:
        {resume_text[:200]}

        Suggested answer: Try exploring careers in IT, AI, or Software Development.
        """

        return jsonify({"answer": fallback}), 200
# ================= AUTHENTICATION =================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if not username or not email or not password:
            flash('Please fill all fields', 'danger')
            return render_template('register.html')

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, email, password_hash, is_admin) VALUES (?, ?, ?, ?)",
                (username, email, hashed_password, 0)
            )
            conn.commit()
            conn.close()

            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))

        except sqlite3.IntegrityError:
            flash('Username or email already exists!', 'danger')
        except Exception as e:
            flash(f'Registration error: {str(e)}', 'danger')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            user_data = cursor.fetchone()
            conn.close()

            if user_data and bcrypt.check_password_hash(user_data['password_hash'], password):
                user = User(
                    id=user_data['id'],
                    username=user_data['username'],
                    email=user_data['email'],
                    password_hash=user_data['password_hash'],
                    is_admin=user_data['is_admin']
                )
                login_user(user)
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid email or password', 'danger')

        except Exception as e:
            flash(f'Login error: {str(e)}', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

# ================= SOCIAL LOGIN PLACEHOLDER =================
@app.route('/auth/google')
def auth_google():
    flash('Google Sign-In is not configured yet. Please use regular login.', 'info')
    return redirect(url_for('login'))

@app.route('/auth/linkedin')
def auth_linkedin():
    flash('LinkedIn Sign-In is not configured yet. Please use regular login.', 'info')
    return redirect(url_for('login'))

# ================= SAVE RECOMMENDATIONS =================

@app.route('/save_recommendation', methods=['POST'])
@login_required
def save_recommendation():
    item_type = request.form.get('item_type')
    item_id = request.form.get('item_id')

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if already saved
        cursor.execute(
            "SELECT id FROM saved_recommendations WHERE user_id=? AND item_type=? AND item_id=?",
            (current_user.id, item_type, item_id)
        )

        if cursor.fetchone():
            flash('Already saved!', 'info')
        else:
            cursor.execute(
                "INSERT INTO saved_recommendations (user_id, item_type, item_id) VALUES (?, ?, ?)",
                (current_user.id, item_type, item_id)
            )
            conn.commit()
            flash('Saved successfully!', 'success')

            # Gamification: Award points for saving and check for Explorer badge
            add_points(current_user.id, 5)
            cursor.execute("SELECT COUNT(*) FROM saved_recommendations WHERE user_id = ?", (current_user.id,))
            saved_count = cursor.fetchone()[0]
            if saved_count >= 5:
                award_badge(current_user.id, 'Explorer')

        conn.close()
    except Exception as e:
        flash(f'Error saving: {str(e)}', 'danger')

    return redirect(request.referrer or url_for('dashboard'))

@app.route('/unsave/<int:saved_id>')
@login_required
def unsave_recommendation(saved_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM saved_recommendations WHERE id=? AND user_id=?",
                       (saved_id, current_user.id))
        conn.commit()
        conn.close()
        flash('Removed from saved items', 'success')
    except Exception as e:
        flash(f'Error removing: {str(e)}', 'danger')

    return redirect(url_for('profile'))

from werkzeug.utils import secure_filename

# ... (rest of the imports)


# ================= PROFILE =================

@app.route('/profile')
@login_required
def profile():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Saved courses
    cursor.execute("""
        SELECT c.*, s.id as save_id FROM courses c
        JOIN saved_recommendations s ON c.course_id = s.item_id
        WHERE s.user_id = ? AND s.item_type = 'course'
    """, (current_user.id,))
    saved_courses = cursor.fetchall()

    # Saved exams
    cursor.execute("""
        SELECT e.*, s.id as save_id FROM exams e
        JOIN saved_recommendations s ON e.exam_id = s.item_id
        WHERE s.user_id = ? AND s.item_type = 'exam'
    """, (current_user.id,))
    saved_exams = cursor.fetchall()

    # Saved jobs
    cursor.execute("""
        SELECT j.*, s.id as save_id FROM jobs j
        JOIN saved_recommendations s ON j.job_id = s.item_id
        WHERE s.user_id = ? AND s.item_type = 'job'
    """, (current_user.id,))
    saved_jobs = cursor.fetchall()

    conn.close()

    return render_template('profile.html',
                         saved_courses=saved_courses,
                         saved_exams=saved_exams,
                         saved_jobs=saved_jobs)

# ================= ADMIN ROUTES =================

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as count FROM courses")
    total_courses = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM exams")
    total_exams = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM jobs")
    total_jobs = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM users")
    total_users = cursor.fetchone()['count']

    cursor.execute("SELECT * FROM courses ORDER BY course_id DESC")
    courses = cursor.fetchall()

    cursor.execute("SELECT * FROM exams ORDER BY exam_id DESC")
    exams = cursor.fetchall()

    cursor.execute("SELECT * FROM jobs ORDER BY job_id DESC")
    jobs = cursor.fetchall()

    conn.close()

    return render_template('admin_dashboard.html',
                         courses=courses, exams=exams, jobs=jobs,
                         total_courses=total_courses, total_exams=total_exams, total_jobs=total_jobs, total_users=total_users)

@app.route('/admin/add_course', methods=['GET', 'POST'])
@login_required
@admin_required
def add_course():
    if request.method == 'POST':
        course_name = request.form['course_name']
        stream = request.form['stream']
        fees = request.form['fees']
        duration = request.form['duration']
        future_scope = request.form['future_scope']
        skills_required = request.form['skills_required']
        level = request.form['level']
        field = request.form['field']
        provider = request.form['provider']
        link = request.form['link']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO courses (course_name, stream, fees, duration, future_scope, skills_required, level, field, provider, link) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (course_name, stream, fees, duration, future_scope, skills_required, level, field, provider, link))
        conn.commit()
        conn.close()
        flash('Course added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('add_course.html')

@app.route('/admin/edit_course/<int:course_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_course(course_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == 'POST':
        course_name = request.form['course_name']
        stream = request.form['stream']
        fees = request.form['fees']
        duration = request.form['duration']
        future_scope = request.form['future_scope']
        skills_required = request.form['skills_required']
        level = request.form['level']
        field = request.form['field']
        provider = request.form['provider']
        link = request.form['link']

        cursor.execute("UPDATE courses SET course_name=?, stream=?, fees=?, duration=?, future_scope=?, skills_required=?, level=?, field=?, provider=?, link=? WHERE course_id=?",
                       (course_name, stream, fees, duration, future_scope, skills_required, level, field, provider, link, course_id))
        conn.commit()
        conn.close()
        flash('Course updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    cursor.execute("SELECT * FROM courses WHERE course_id=?", (course_id,))
    course = cursor.fetchone()
    conn.close()
    return render_template('edit_course.html', course=course)

@app.route('/admin/delete_course/<int:course_id>', methods=['POST'])
@login_required
@admin_required
def delete_course(course_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM courses WHERE course_id=?", (course_id,))
    conn.commit()
    conn.close()
    flash('Course deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_exam', methods=['GET', 'POST'])
@login_required
@admin_required
def add_exam():
    if request.method == 'POST':
        exam_name = request.form['exam_name']
        conducting_body = request.form['conducting_body']
        eligibility = request.form['eligibility']
        syllabus = request.form['syllabus']
        important_dates = request.form['important_dates']
        application_process = request.form['application_process']
        website = request.form['website']
        level = request.form['level']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO exams (exam_name, conducting_body, eligibility, syllabus, important_dates, application_process, website, level) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (exam_name, conducting_body, eligibility, syllabus, important_dates, application_process, website, level))
        conn.commit()
        conn.close()
        flash('Exam added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('add_exam.html')

@app.route('/admin/edit_exam/<int:exam_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_exam(exam_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == 'POST':
        exam_name = request.form['exam_name']
        conducting_body = request.form['conducting_body']
        eligibility = request.form['eligibility']
        syllabus = request.form['syllabus']
        important_dates = request.form['important_dates']
        application_process = request.form['application_process']
        website = request.form['website']
        level = request.form['level']

        cursor.execute("UPDATE exams SET exam_name=?, conducting_body=?, eligibility=?, syllabus=?, important_dates=?, application_process=?, website=?, level=? WHERE exam_id=?",
                       (exam_name, conducting_body, eligibility, syllabus, important_dates, application_process, website, level, exam_id))
        conn.commit()
        conn.close()
        flash('Exam updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    cursor.execute("SELECT * FROM exams WHERE exam_id=?", (exam_id,))
    exam = cursor.fetchone()
    conn.close()
    return render_template('edit_exam.html', exam=exam)

@app.route('/admin/delete_exam/<int:exam_id>', methods=['POST'])
@login_required
@admin_required
def delete_exam(exam_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM exams WHERE exam_id=?", (exam_id,))
    conn.commit()
    conn.close()
    flash('Exam deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_job', methods=['GET', 'POST'])
@login_required
@admin_required
def add_job():
    if request.method == 'POST':
        job_title = request.form['job_title']
        company_sector = request.form['company_sector']
        qualifications = request.form['qualifications']
        skills_required = request.form['skills_required']
        salary_range = request.form['salary_range']
        job_description = request.form['job_description']
        application_deadline = request.form['application_deadline']
        location = request.form['location']
        job_type = request.form['job_type']
        level = request.form['level']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO jobs (job_title, company_sector, qualifications, skills_required, salary_range, job_description, application_deadline, location, job_type, level) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (job_title, company_sector, qualifications, skills_required, salary_range, job_description, application_deadline, location, job_type, level))
        conn.commit()
        conn.close()
        flash('Job added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('add_job.html')

@app.route('/admin/edit_job/<int:job_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_job(job_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == 'POST':
        job_title = request.form['job_title']
        company_sector = request.form['company_sector']
        qualifications = request.form['qualifications']
        skills_required = request.form['skills_required']
        salary_range = request.form['salary_range']
        job_description = request.form['job_description']
        application_deadline = request.form['application_deadline']
        location = request.form['location']
        job_type = request.form['job_type']
        level = request.form['level']

        cursor.execute("UPDATE jobs SET job_title=?, company_sector=?, qualifications=?, skills_required=?, salary_range=?, job_description=?, application_deadline=?, location=?, job_type=?, level=? WHERE job_id=?",
                       (job_title, company_sector, qualifications, skills_required, salary_range, job_description, application_deadline, location, job_type, level, job_id))
        conn.commit()
        conn.close()
        flash('Job updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    cursor.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,))
    job = cursor.fetchone()
    conn.close()
    return render_template('edit_job.html', job=job)

@app.route('/admin/delete_job/<int:job_id>', methods=['POST'])
@login_required
@admin_required
def delete_job(job_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM jobs WHERE job_id=?", (job_id,))
    conn.commit()
    conn.close()
    flash('Job deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

# ================= DEBUG ROUTES =================

@app.route('/debug')
def debug_info():
    """Database debug information"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as count FROM courses")
    course_count = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM exams")
    exam_count = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM jobs")
    job_count = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM users")
    user_count = cursor.fetchone()['count']

    # Sample data
    cursor.execute("SELECT course_name, stream, level FROM courses LIMIT 5")
    sample_courses = cursor.fetchall()

    conn.close()

    return f"""
    <h2>Database Debug Info</h2>
    <p>Courses: {course_count}</p>
    <p>Exams: {exam_count}</p>
    <p>Jobs: {job_count}</p>
    <p>Users: {user_count}</p>
    <h3>Sample Courses:</h3>
    <ul>
        {"".join([f"<li>{course['course_name']} ({course['stream']}) - {course['level']}</li>" for course in sample_courses])}
    </ul>
    <a href="/">Home</a>
    """

# ================= RUN APP =================

if __name__ == '__main__':
    print("Starting CareerAI Server...")
    print("Available Routes:")
    print("- /login - User login")
    print("- /register - User registration")
    print("- /dashboard - Main dashboard")
    print("- /assessment - Career assessment")
    print("- /recommend - Get recommendations")
    print("- /api/chat - Smart Career Chatbot (POST JSON: {message: '...'} )")
    print("- /debug - Database debug info")
    app.run(debug=True, host='127.0.0.1', port=5000)
@app.route('/api/roadmap', methods=['POST'])
@login_required
def roadmap():
    data = request.get_json()
    career = data.get('career', '')

    roadmap_text = f"""
🚀 Roadmap for {career}

1. Learn Basics
2. Build Projects
3. Practice Skills
4. Do Internship
5. Apply for Jobs

🔥 Stay consistent and upgrade skills regularly.
"""

    return jsonify({"roadmap": roadmap_text})

def calculate_score(item, user_input, interests):
    score = 0

    # 🎯 Stream match
    if user_input.get("stream") and item.get("stream"):
        if user_input["stream"].lower() in item["stream"].lower():
            score += 30

    # 🎯 Budget match
    if user_input.get("budget") and item.get("fees"):
        if int(item["fees"]) <= int(user_input["budget"]):
            score += 20

    # 🎯 Interest match
    if item.get("skills_required"):
        skills = item["skills_required"].lower()
        for interest in interests:
            if interest.lower() in skills:
                score += 10

    return score

@app.route('/api/roadmap', methods=['POST'])
@login_required
def get_roadmap():
    data = request.get_json()
    career = data.get("career")

    roadmap = ""

    if "B.Tech" in career or "Computer" in career:
        roadmap = """
Step 1: Learn Programming (Python / C++)
Step 2: Study Data Structures & Algorithms
Step 3: Build Projects (Web / AI)
Step 4: Learn AI & Machine Learning
Step 5: Apply for Internships
Step 6: Crack Product-based Companies
        """

    elif "Developer" in career:
        roadmap = """
Step 1: Learn HTML, CSS, JavaScript
Step 2: Learn Python / Java
Step 3: Build Real Projects
Step 4: Learn Backend (Flask / Django)
Step 5: Practice DSA
Step 6: Apply for Jobs
        """

    else:
        roadmap = "Roadmap will be updated soon..."

    return jsonify({"roadmap": roadmap})

import os

UPLOAD_FOLDER = 'uploads'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER) 