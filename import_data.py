import pandas as pd
import sqlite3
import os
import subprocess

DATABASE_FILE = 'career_guide.db'
CSV_FOLDER = 'data'

def setup_database():
    """Database ko delete karke naya, sahi structure ke saath banata hai."""
    if os.path.exists(DATABASE_FILE):
        os.remove(DATABASE_FILE)
        print(f"Purana database '{DATABASE_FILE}' delete kar diya gaya hai.")
        
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    print("Naya database ban gaya hai.")

    # Step 1: Sabhi tables ko sahi schema ke saath banao
    print("\nTables banana shuru ho raha hai...")
    try:
        # Courses Table - app.py ke according updated
        cursor.execute('''
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
        # Exams Table - app.py ke according updated
        cursor.execute('''
            CREATE TABLE exams (
                exam_id INTEGER PRIMARY KEY AUTOINCREMENT, 
                exam_name TEXT, 
                conducting_body TEXT,
                eligibility TEXT, 
                syllabus TEXT, 
                important_dates TEXT, 
                application_process TEXT, 
                website TEXT,
                level TEXT
            );
        ''')
        # Jobs Table - app.py ke according updated
        cursor.execute('''
            CREATE TABLE jobs (
                job_id INTEGER PRIMARY KEY AUTOINCREMENT, 
                job_title TEXT, 
                company_sector TEXT,
                qualifications TEXT, 
                skills_required TEXT, 
                salary_range TEXT, 
                job_description TEXT,
                application_deadline TEXT, 
                location TEXT, 
                job_type TEXT,
                level TEXT,
                stream TEXT
            );
        ''')
        # User tables
        cursor.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                username TEXT UNIQUE NOT NULL, 
                email TEXT UNIQUE NOT NULL, 
                password_hash TEXT NOT NULL, 
                is_admin BOOLEAN NOT NULL DEFAULT 0
            );
        ''')
        cursor.execute('''
            CREATE TABLE saved_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                user_id INTEGER NOT NULL, 
                item_id INTEGER NOT NULL, 
                item_type TEXT NOT NULL, 
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
        ''')
        cursor.execute('''
            CREATE TABLE chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sender TEXT NOT NULL, -- 'user' or 'bot'
                message TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
        ''')

        # Gamification tables
        cursor.execute('''
            CREATE TABLE user_points (
                user_id INTEGER PRIMARY KEY,
                points INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
        ''')
        cursor.execute('''
            CREATE TABLE badges (
                badge_id INTEGER PRIMARY KEY AUTOINCREMENT,
                badge_name TEXT UNIQUE NOT NULL,
                badge_description TEXT NOT NULL,
                badge_icon TEXT NOT NULL -- Font Awesome icon class
            );
        ''')
        cursor.execute('''
            CREATE TABLE user_badges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                badge_id INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
        ''')

        cursor.execute('''
            CREATE TABLE user_assessment_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
        ''')

        # Pre-populate badges
        badges_to_add = [
            ('Explorer', 'Save at least 5 items', 'fa-solid fa-compass'),
            ('Planner', 'Use the assessment form 3 times', 'fa-solid fa-map-signs'),
            ('Chatterbox', 'Have a chat history of over 20 messages', 'fa-solid fa-comments'),
            ('Profile Pro', 'Upload a resume', 'fa-solid fa-user-tie')
        ]
        cursor.executemany("INSERT INTO badges (badge_name, badge_description, badge_icon) VALUES (?, ?, ?)", badges_to_add)

        conn.commit()
        print("-> Sabhi 5 tables safaltapurvak ban gayi hain.")
    except Exception as e:
        print(f"Tables banate samay error: {e}")

    # Step 2: CSV se data import karo with proper column mapping
    print("\nCSV files se data import karna shuru ho raha hai...")
    
    # Courses data import
    try:
        file_path = os.path.join(CSV_FOLDER, 'course.csv')
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            print(f"Course CSV columns: {df.columns.tolist()}")
            
            # Column mapping - CSV columns ko database columns se match karo
            if 'course_id' in df.columns:
                df = df.drop(columns=['course_id'])
            
            # Ensure all required columns exist
            required_columns = ['course_name', 'stream', 'fees', 'duration', 'future_scope', 'skills_required', 'level', 'field']
            for col in required_columns:
                if col not in df.columns:
                    df[col] = ''  # Add missing columns with empty values
            
            # Add extra columns that app.py expects
            df['provider'] = 'Various Institutions'
            df['link'] = 'https://example.com'
            
            df.to_sql('courses', conn, if_exists='append', index=False)
            print(f"-> 'courses' table mein {len(df)} records import ho gaye hain.")
        else:
            print(f"ERROR: Course CSV file nahi mili: {file_path}")
    except Exception as e:
        print(f"ERROR importing courses: {e}")

    # Exams data import
    try:
        file_path = os.path.join(CSV_FOLDER, 'exam.csv')
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            print(f"Exam CSV columns: {df.columns.tolist()}")
            
            if 'exam_id' in df.columns:
                df = df.drop(columns=['exam_id'])
            
            # Map CSV columns to database columns
            column_mapping = {
                'exam_name': 'exam_name',
                'conducting_body': 'conducting_body', 
                'eligibility': 'eligibility',
                'syllabus': 'syllabus',
                'important_dates': 'important_dates',
                'application_process': 'application_process',
                'website': 'website',
                'level': 'level' # Add this line
            }
            
            # Create new DataFrame with correct column names
            exam_data = {}
            for db_col, csv_col in column_mapping.items():
                if csv_col in df.columns:
                    exam_data[db_col] = df[csv_col]
                else:
                    exam_data[db_col] = ''  # Default value if column missing
            
            exam_df = pd.DataFrame(exam_data)
            exam_df.to_sql('exams', conn, if_exists='append', index=False)
            print(f"-> 'exams' table mein {len(exam_df)} records import ho gaye hain.")
        else:
            print(f"ERROR: Exam CSV file nahi mili: {file_path}")
    except Exception as e:
        print(f"ERROR importing exams: {e}")

    # Step 2.5: Run live job scraper
    print("\nLive job data scrape karna shuru ho raha hai...")
    try:
        # Ensure python3 is used, or just python if that's the system default
        subprocess.run(['python', 'scrapers/scrape_jobs.py'], check=True)
        print("-> Job scraper safaltapurvak chal gaya.")
    except FileNotFoundError:
        print("ERROR: 'python' command nahi mila. Make sure Python is in your system's PATH.")
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Job scraper fail ho gaya: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while running the scraper: {e}")

    # Jobs data import
    try:
        file_path = os.path.join(CSV_FOLDER, 'jobs.csv')
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            print(f"Jobs CSV columns: {df.columns.tolist()}")
            
            if 'job_id' in df.columns:
                df = df.drop(columns=['job_id'])
            
            # Map CSV columns to database columns
            column_mapping = {
                'job_title': 'job_title',
                'company_sector': 'company_sector',
                'qualifications': 'qualifications',
                'skills_required': 'skills_required',
                'salary_range': 'salary_range',
                'job_description': 'job_description',
                'application_deadline': 'application_deadline',
                'location': 'location',
                'job_type': 'job_type',
                'level': 'level',
                'stream': 'stream'
            }
            
            # Create new DataFrame with correct column names
            job_data = {}
            for db_col, csv_col in column_mapping.items():
                if csv_col in df.columns:
                    job_data[db_col] = df[csv_col]
                else:
                    job_data[db_col] = ''  # Default value if column missing
            
            job_df = pd.DataFrame(job_data)
            job_df.to_sql('jobs', conn, if_exists='append', index=False)
            print(f"-> 'jobs' table mein {len(job_df)} records import ho gaye hain.")
        else:
            print(f"ERROR: Jobs CSV file nahi mili: {file_path}")
    except Exception as e:
        print(f"ERROR importing jobs: {e}")

    # Step 3: Sample admin user add karo
    try:
        from flask_bcrypt import Bcrypt
        bcrypt = Bcrypt()
        admin_password = bcrypt.generate_password_hash('admin123').decode('utf-8')
        
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, is_admin) VALUES (?, ?, ?, ?)",
            ('admin', 'admin@careerai.com', admin_password, 1)
        )
        
        # Sample regular user
        user_password = bcrypt.generate_password_hash('user123').decode('utf-8')
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, is_admin) VALUES (?, ?, ?, ?)",
            ('ajay', 'ajay@example.com', user_password, 0)
        )
        
        conn.commit()
        print("-> Sample users add ho gaye hain (admin/admin123, ajay/user123)")
    except Exception as e:
        print(f"ERROR adding sample users: {e}")

    conn.close()
    print("\nDatabase setup complete!")
    print("\nAb aap yeh commands run kar sakte hain:")
    print("1. python app.py - Server start karein")
    print("2. http://127.0.0.1:5000/debug/database - Database check karein")

if __name__ == '__main__':
    setup_database()