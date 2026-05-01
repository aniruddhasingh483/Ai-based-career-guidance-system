import unittest
import app as main_app
import sqlite3
import pandas as pd
import os

class TestApp(unittest.TestCase):
    def setUp(self):
        main_app.app.testing = True
        self.app = main_app.app.test_client()

        # Set up a test database
        self.db_name = 'test_career_guide.db'
        if os.path.exists(self.db_name):
            os.remove(self.db_name)
            
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()

        # Create tables
        self.cursor.execute("DROP TABLE IF EXISTS courses")
        self.cursor.execute("DROP TABLE IF EXISTS exams")
        self.cursor.execute("DROP TABLE IF EXISTS jobs")
        self.cursor.execute("DROP TABLE IF EXISTS users")
        self.cursor.execute("DROP TABLE IF EXISTS saved_recommendations")
        self.cursor.execute("DROP TABLE IF EXISTS chat_history")
        self.cursor.execute("DROP TABLE IF EXISTS user_points")
        self.cursor.execute("DROP TABLE IF EXISTS badges")
        self.cursor.execute("DROP TABLE IF EXISTS user_badges")
        self.cursor.execute("DROP TABLE IF EXISTS user_assessment_history")

        self.cursor.execute('''
            CREATE TABLE courses (
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
            );
        ''')
        self.cursor.execute('''
            CREATE TABLE exams (
                exam_id INTEGER PRIMARY KEY AUTOINCREMENT, 
                exam_name TEXT, 
                stream TEXT,
                conducting_body TEXT,
                eligibility TEXT, 
                application_mode TEXT,
                exam_date TEXT,
                last_date TEXT,
                syllabus TEXT, 
                website TEXT,
                fees INTEGER,
                popular_courses TEXT,
                level TEXT
            );
        ''')
        self.cursor.execute('''
            CREATE TABLE jobs (
                job_id INTEGER PRIMARY KEY AUTOINCREMENT, 
                job_title TEXT, 
                company_sector TEXT,
                stream TEXT,
                education_required TEXT,
                experience_required TEXT,
                salary_range TEXT, 
                location TEXT, 
                skills_required TEXT, 
                job_type TEXT,
                application_deadline TEXT, 
                website TEXT,
                description TEXT,
                level TEXT
            );
        ''')
        self.cursor.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                username TEXT UNIQUE NOT NULL, 
                email TEXT UNIQUE NOT NULL, 
                password_hash TEXT NOT NULL, 
                is_admin BOOLEAN NOT NULL DEFAULT 0
            );
        ''')
        self.cursor.execute('''
            CREATE TABLE saved_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                user_id INTEGER NOT NULL, 
                item_id INTEGER NOT NULL, 
                item_type TEXT NOT NULL, 
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
        ''')
        self.cursor.execute('''
            CREATE TABLE chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sender TEXT NOT NULL, -- 'user' or 'bot'
                message TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
        ''')
        self.cursor.execute('''
            CREATE TABLE user_points (
                user_id INTEGER PRIMARY KEY,
                points INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
        ''')
        self.cursor.execute('''
            CREATE TABLE badges (
                badge_id INTEGER PRIMARY KEY AUTOINCREMENT,
                badge_name TEXT UNIQUE NOT NULL,
                badge_description TEXT NOT NULL,
                badge_icon TEXT NOT NULL -- Font Awesome icon class
            );
        ''')
        self.cursor.execute('''
            CREATE TABLE user_badges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                badge_id INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
        ''')
        self.cursor.execute('''
            CREATE TABLE user_assessment_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
        ''')

        # Import data
        df_courses = pd.read_csv('data/course.csv')
        df_courses.to_sql('courses', self.conn, if_exists='append', index=False)
        
        df_exams = pd.read_csv('data/exam.csv')
        df_exams.to_sql('exams', self.conn, if_exists='append', index=False)
        
        df_jobs = pd.read_csv('data/jobs.csv')
        df_jobs.to_sql('jobs', self.conn, if_exists='append', index=False)

        self.conn.commit()
        self.conn.close()

    def tearDown(self):
        if os.path.exists(self.db_name):
            os.remove(self.db_name)

    def test_recommend_graduate_science(self):
        with self.app as client:
            # Register and login a user
            client.post('/register', data=dict(username='testuser', email='test@example.com', password='password'), follow_redirects=True)
            client.post('/login', data=dict(email='test@example.com', password='password'), follow_redirects=True)

            # Make a recommendation request
            response = client.post('/recommend', data=dict(
                education='Graduate',
                stream='Science',
                budget='200000',
                user_interests='Data Science, Machine Learning'
            ), follow_redirects=True)

            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Recommendations', response.data)
            self.assertIn(b'M.Sc in Data Science', response.data)
            self.assertIn(b'Data Analytics Entrance Exam', response.data)

if __name__ == '__main__':
    main_app.app.config['DATABASE'] = 'test_career_guide.db'
    unittest.main()


