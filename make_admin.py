import sqlite3

def set_admin(email):
    try:
        conn = sqlite3.connect('career_guide.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_admin = 1 WHERE email = ?", (email,))
        conn.commit()
        if cursor.rowcount > 0:
            print(f"Success! User with email '{email}' is now an admin.")
        else:
            print(f"Error: No user found with email '{email}'. Make sure you have registered first.")
        conn.close()
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    user_email = input("Enter the email of the user you want to make an admin: ")
    set_admin(user_email)
