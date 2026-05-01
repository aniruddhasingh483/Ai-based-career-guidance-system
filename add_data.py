import sqlite3

conn = sqlite3.connect('career_guide.db')
cursor = conn.cursor()

# ===== COURSES DATA =====
courses = [
("B.Tech Computer Science", "Science", 100000, "4 Years", "Software Engineer, AI Engineer", "Programming, Logic", "12th", "Engineering", "IIT/NIT", ""),
("BCA", "Commerce", 60000, "3 Years", "Developer, IT Jobs", "Coding, Basics", "12th", "Computer", "Private Colleges", ""),
("MBA", "Any", 200000, "2 Years", "Manager, Business Analyst", "Leadership, Communication", "Graduate", "Management", "IIM", ""),
("B.Sc Data Science", "Science", 80000, "3 Years", "Data Analyst", "Python, Statistics", "12th", "Data", "University", ""),
("Diploma in Web Dev", "Any", 30000, "1 Year", "Frontend Developer", "HTML, CSS, JS", "10th", "IT", "Online", "")
]

cursor.executemany("""
INSERT INTO courses (course_name, stream, fees, duration, future_scope, skills_required, level, field, provider, link)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", courses)

# ===== JOBS DATA =====
jobs = [
("Software Developer", "IT", "B.Tech/BCA", "Coding", "5-10 LPA", "Develop software", "Graduate"),
("Data Analyst", "IT", "B.Sc/MCA", "Python, SQL", "4-8 LPA", "Analyze data", "Graduate"),
("Bank Clerk", "Banking", "Graduate", "Math, Reasoning", "3-5 LPA", "Bank work", "Graduate"),
("Teacher", "Education", "B.Ed", "Teaching", "2-6 LPA", "Teach students", "Graduate"),
("Web Designer", "IT", "Any", "HTML, CSS", "3-6 LPA", "Design websites", "Any")
]

cursor.executemany("""
INSERT INTO jobs (job_title, company_sector, qualifications, skills_required, salary_range, job_description, level)
VALUES (?, ?, ?, ?, ?, ?, ?)
""", jobs)

# ===== EXAMS DATA =====
exams = [
("UPSC", "Government", "Graduate", "GS, Aptitude", "Graduate"),
("JEE", "NTA", "12th Science", "Physics, Math", "12th"),
("NEET", "NTA", "12th Biology", "Biology", "12th"),
("CAT", "IIM", "Graduate", "Aptitude", "Graduate"),
("SSC", "Govt", "Graduate", "Reasoning", "Graduate")
]

cursor.executemany("""
INSERT INTO exams (exam_name, conducting_body, eligibility, syllabus, level)
VALUES (?, ?, ?, ?, ?)
""", exams)

# ===== BADGES =====
badges = [
("Starter", "First login", "⭐"),
("Explorer", "Saved 5 items", "🧭"),
("Chatterbox", "20 chats", "💬"),
("Planner", "3 assessments", "📅"),
("Profile Pro", "Uploaded resume", "📄")
]

cursor.executemany("""
INSERT INTO badges (badge_name, badge_description, badge_icon)
VALUES (?, ?, ?)
""", badges)

conn.commit()
conn.close()

print("Sample data inserted successfully!")