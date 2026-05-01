import sqlite3

def get_distinct_levels():
    conn = sqlite3.connect('career_guide.db')
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT level FROM courses;")
    levels = cursor.fetchall()
    conn.close()
    for level in levels:
        print(level[0])

if __name__ == '__main__':
    get_distinct_levels()