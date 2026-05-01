import sqlite3

conn = sqlite3.connect('career_guide.db')
cursor = conn.cursor()

# USERS
cursor.execute("""CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    email TEXT UNIQUE,
    password_hash TEXT,
    is_admin INTEGER DEFAULT 0
)""")

# COURSES
cursor.execute("""CREATE TABLE IF NOT EXISTS courses (
    course_id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_name TEXT,
    stream TEXT,
    fees INTEGER,
    duration TEXT,
    future_scope TEXT,
    skills_required TEXT,
    level TEXT,
    field TEXT,
    provider TEXT,
    link TEXT
)""")

# JOBS
cursor.execute("""CREATE TABLE IF NOT EXISTS jobs (
    job_id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_title TEXT,
    company_sector TEXT,
    qualifications TEXT,
    skills_required TEXT,
    salary_range TEXT,
    job_description TEXT,
    level TEXT
)""")

# EXAMS
cursor.execute("""CREATE TABLE IF NOT EXISTS exams (
    exam_id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_name TEXT,
    conducting_body TEXT,
    eligibility TEXT,
    syllabus TEXT,
    level TEXT
)""")

# SAVED RECOMMENDATIONS
cursor.execute("""CREATE TABLE IF NOT EXISTS saved_recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    item_type TEXT,
    item_id INTEGER
)""")

# CHAT HISTORY
cursor.execute("""CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    sender TEXT,
    message TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)""")

# USER POINTS
cursor.execute("""CREATE TABLE IF NOT EXISTS user_points (
    user_id INTEGER PRIMARY KEY,
    points INTEGER DEFAULT 0
)""")

# BADGES
cursor.execute("""CREATE TABLE IF NOT EXISTS badges (
    badge_id INTEGER PRIMARY KEY AUTOINCREMENT,
    badge_name TEXT,
    badge_description TEXT,
    badge_icon TEXT
)""")

# USER BADGES
cursor.execute("""CREATE TABLE IF NOT EXISTS user_badges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    badge_id INTEGER
)""")

# USER ASSESSMENT
import sqlite3

conn = sqlite3.connect('career_guide.db')
cursor = conn.cursor()

# USERS
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    email TEXT UNIQUE,
    password_hash TEXT,
    is_admin INTEGER DEFAULT 0
)
""")

# COURSES
cursor.execute("""
CREATE TABLE IF NOT EXISTS courses (
    course_id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_name TEXT,
    stream TEXT,
    fees INTEGER,
    duration TEXT,
    future_scope TEXT,
    skills_required TEXT,
    level TEXT,
    field TEXT
)
""")

# JOBS
cursor.execute("""
CREATE TABLE IF NOT EXISTS jobs (
    job_id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_title TEXT,
    company_sector TEXT,
    qualifications TEXT,
    skills_required TEXT,
    salary_range TEXT,
    location TEXT,
    level TEXT
)
""")

# EXAMS
cursor.execute("""
CREATE TABLE IF NOT EXISTS exams (
    exam_id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_name TEXT,
    conducting_body TEXT,
    eligibility TEXT,
    level TEXT
)
""")

# SAVED ITEMS
cursor.execute("""
CREATE TABLE IF NOT EXISTS saved_recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    item_type TEXT,
    item_id INTEGER
)
""")

conn.commit()
conn.close()

print("✅ Database Created Successfully!")
