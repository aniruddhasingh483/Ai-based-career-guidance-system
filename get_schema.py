import sqlite3

def get_table_schema(table_name):
    conn = sqlite3.connect('career_guide.db')
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name});")
    schema = cursor.fetchall()
    conn.close()
    print(f"Schema for {table_name}:")
    for col in schema:
        print(col)

if __name__ == '__main__':
    get_table_schema('courses')
    get_table_schema('exams')
    get_table_schema('jobs')
