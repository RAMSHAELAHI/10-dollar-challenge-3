# database.py
import sqlite3
from contextlib import contextmanager

@contextmanager
def get_db_connection():
    """Context manager for database connection."""
    conn = sqlite3.connect("student_portal.db")
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def setup_database():
    """Sets up the database schema (tables)."""
    with get_db_connection() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,  
                role TEXT NOT NULL DEFAULT 'student'  
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                roll_no TEXT NOT NULL,
                email TEXT NOT NULL,
                slot TEXT NOT NULL,
                contact TEXT NOT NULL,
                course_id INTEGER NOT NULL,
                favorite_teacher_id INTEGER NOT NULL,
                photo BLOB,
                face_encoding BLOB, -- New column for face encoding
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (course_id) REFERENCES courses(id),
                FOREIGN KEY (favorite_teacher_id) REFERENCES teachers(id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teachers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                time_in DATETIME,
                time_out DATETIME,
                FOREIGN KEY (student_id) REFERENCES students(id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                marks INTEGER NOT NULL,
                FOREIGN KEY (student_id) REFERENCES students(id)
            )
        """)

        # Insert initial courses and teachers if they don't exist
        for course_name in ["Python", "Typescript", "Next.js"]:
            cursor.execute("INSERT OR IGNORE INTO courses (name) VALUES (?)", (course_name,))
        for teacher_name in ["Sir Zia", "Madam Hira", "Sir Inam"]:
            cursor.execute("INSERT OR IGNORE INTO teachers (name) VALUES (?)", (teacher_name,))
        
        # Insert a dummy admin user and student user if they don't exist
        cursor.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)", ("admin", "admin123", "admin"))
        cursor.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)", ("student", "student123", "student"))

def get_user_role(username):
    """Retrieves the role of a user from the database."""
    with get_db_connection() as cursor:
        cursor.execute("SELECT role FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        if result:
            return result[0]
        else:
            return None