# app.py
import sqlite3
import streamlit as st # type: ignore
import datetime 
import numpy as np # type: ignore # Needed to convert BLOB back to numpy array for face encoding

# Import functions/classes from your new files
from database import get_db_connection, setup_database, get_user_role
from utils import display_error, display_success, validate_input, Course
from features import recognize_face, process_payment, generate_id_card, get_face_encoding_from_photo # type: ignore

# --- Main Streamlit App ---
def main():
    st.title("GIAIC Student Portal")

    # Initialize database
    setup_database()

    # Session state for login
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['user_name'] = None
        st.session_state['user_id'] = None  # To store the logged-in user's ID
        st.session_state['role'] = None # to store user role
        
    # --- Login Section ---
    if not st.session_state['logged_in']:
        st.subheader("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_button = st.button("Login")

        if login_button:
            with get_db_connection() as cursor:
                cursor.execute("SELECT id, username, password, role FROM users WHERE username = ?", (username,))
                user = cursor.fetchone()

            if user and user[2] == password:  # plaintext password for demo
                st.session_state['logged_in'] = True
                st.session_state['user_name'] = user[1]
                st.session_state['user_id'] = user[0]
                st.session_state['role'] = user[3] # set user role
                st.success("Logged in successfully!")
                st.experimental_rerun()
            else:
                st.error("Invalid credentials")
    else:
        st.sidebar.write(f"Welcome, {st.session_state['user_name']} ({st.session_state['role'].title()})!")  # Show role
        if st.sidebar.button("Logout"):
            st.session_state['logged_in'] = False
            st.session_state['user_name'] = None
            st.session_state['user_id'] = None
            st.session_state['role'] = None
            st.success("Logged out!")
            st.experimental_rerun()

        # --- Student Form and Actions ---
        if st.session_state['logged_in'] and st.session_state['role'] == 'student': # restrict to student role
            st.subheader("Student Portal")
            # Fetch courses and teachers from the database
            with get_db_connection() as cursor:
                cursor.execute("SELECT id, name FROM courses")
                courses = {row[0]: row[1] for row in cursor.fetchall()}
                cursor.execute("SELECT id, name FROM teachers")
                teachers = {row[0]: row[1] for row in cursor.fetchall()}

            # Student Registration/Update Form
            st.write("#### Register / Update Your Information")
            with st.form(key="student_form"):
                name = st.text_input("Name")
                roll_no = st.text_input("Roll No")
                email = st.text_input("Email")
                slot = st.text_input("Slot")
                contact = st.text_input("Contact")
                
                # Check if courses/teachers are available before creating selectbox
                if courses:
                    course_id = st.selectbox("Course", options=list(courses.keys()), format_func=lambda x: courses[x])
                else:
                    st.warning("No courses available. Please contact admin.")
                    course_id = None

                if teachers:
                    favorite_teacher_id = st.selectbox("Favorite Teacher", options=list(teachers.keys()),
                                                     format_func=lambda x: teachers[x])
                else:
                    st.warning("No teachers available. Please contact admin.")
                    favorite_teacher_id = None
                
                photo = st.file_uploader("Upload Photo (for ID card and Face ID)", type=["jpg", "png", "jpeg"])
                submit_button = st.form_submit_button(label="Submit")

            if submit_button:
                if course_id is None or favorite_teacher_id is None:
                    display_error("Courses or Teachers are not loaded. Cannot submit.")
                else:
                    error_message = validate_input(name, roll_no, email, slot, contact, courses.get(course_id),
                                                 teachers.get(favorite_teacher_id), photo)
                    if error_message:
                        display_error(error_message)
                    else:
                        photo_bytes = photo.read() if photo else None
                        face_encoding_data = None

                        if photo_bytes:
                            # Get face encoding for the uploaded photo
                            encoding, msg = get_face_encoding_from_photo(photo_bytes)
                            if encoding is not None:
                                face_encoding_data = encoding.tobytes() # Convert numpy array to bytes for DB storage
                                display_success("Face detected and encoded successfully from your photo!")
                            else:
                                display_error(f"Could not process photo for face ID: {msg}. Please ensure a clear face is visible.")
                                # You might want to prevent submission if face encoding is critical
                                # For now, we allow submission without face_encoding if it fails.

                        with get_db_connection() as cursor:
                            cursor.execute("SELECT id FROM students WHERE user_id = ?", (st.session_state['user_id'],))
                            existing_student = cursor.fetchone()
                            
                            if existing_student:
                                # Update existing student
                                cursor.execute("""
                                    UPDATE students SET name=?, roll_no=?, email=?, slot=?, contact=?, course_id=?, 
                                    favorite_teacher_id=?, photo=?, face_encoding=? WHERE user_id=?
                                """, (name, roll_no, email, slot, contact, course_id, favorite_teacher_id, photo_bytes, face_encoding_data, st.session_state['user_id']))
                                
                                display_success("Student information updated successfully!")
                            else:
                                # Insert new student
                                cursor.execute("""
                                    INSERT INTO students (user_id, name, roll_no, email, slot, contact, course_id, favorite_teacher_id, photo, face_encoding)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (st.session_state['user_id'], name, roll_no, email, slot, contact, course_id, favorite_teacher_id, photo_bytes, face_encoding_data))
                            display_success("Student information saved successfully!")

            # --- Fetch and Display Student Data ---
            student_id = None
            student_dict = None
            with get_db_connection() as cursor:
                # Retrieve face_encoding as well
                cursor.execute("""
                    SELECT s.id, s.name, s.roll_no, s.email, s.slot, s.contact, c.name, t.name, s.photo, s.face_encoding
                    FROM students s
                    JOIN courses c ON s.course_id = c.id
                    JOIN teachers t ON s.favorite_teacher_id = t.id
                    WHERE s.user_id = ?
                """, (st.session_state['user_id'],))
                student_data = cursor.fetchone()

            if student_data:
                student_id = student_data[0]
                student_dict = {
                    'name': student_data[1],
                    'roll_no': student_data[2],
                    'email': student_data[3],
                    'slot': student_data[4],
                    'contact': student_data[5],
                    'course': student_data[6],
                    'favorite_teacher': student_data[7],
                    'photo': student_data[8],
                    'face_encoding': student_data[9] # Store the face encoding bytes
                }

                st.subheader("Your Profile")
                st.write(f"**Name:** {student_dict['name']}")
                st.write(f"**Roll No:** {student_dict['roll_no']}")
                st.write(f"**Email:** {student_dict['email']}")
                st.write(f"**Slot:** {student_dict['slot']}")
                st.write(f"**Contact:** {student_dict['contact']}")
                st.write(f"**Course:** {student_dict['course']}")
                st.write(f"**Favorite Teacher:** {student_dict['favorite_teacher']}")
                if student_dict['photo']:
                    st.image(student_dict['photo'], caption="Your Photo", width=150)
                else:
                    st.info("No profile photo uploaded yet.")

                # --- Actions ---
                st.subheader("Actions")
                if st.button("Generate ID Card"):
                    if student_dict['photo']:
                        id_card_bytes = generate_id_card(student_dict)
                        if id_card_bytes:
                            st.image(id_card_bytes, caption="Student ID Card", use_column_width=True)
                    else:
                        st.warning("Please upload your profile photo to generate an ID card.")

                st.write("#### Mark Attendance (Face Recognition)")
                attendance_photo = st.camera_input("Take a photo for attendance", key="attendance_camera")
                # Alternatively, use st.file_uploader for a static image:
                # attendance_photo = st.file_uploader("Upload a photo for attendance", type=["jpg", "png", "jpeg"], key="attendance_uploader")

                if attendance_photo is not None:
                    if st.button("Submit Attendance with Face ID"):
                        if student_dict['face_encoding']: # Check if student has a registered face encoding
                            attendance_photo_bytes = attendance_photo.read()
                            is_recognized, message = recognize_face(student_dict['face_encoding'], attendance_photo_bytes)
                            
                            if is_recognized:
                                with get_db_connection() as cursor:
                                    #check if time_in is already marked today
                                    cursor.execute("SELECT id, time_in, time_out FROM attendance WHERE student_id = ? AND DATE(time_in) = DATE('now')", (student_id,))
                                    attendance_record = cursor.fetchone()
                                    
                                    if attendance_record:
                                        if attendance_record[2]:
                                            st.success("Attendance already completed for today.")
                                        else:
                                            # update time_out
                                            cursor.execute("UPDATE attendance SET time_out = DATETIME('now') WHERE id = ?", (attendance_record[0],))
                                            st.success("Attendance marked (Time Out).")
                                    else:
                                        # mark new entry
                                        cursor.execute("INSERT INTO attendance (student_id, time_in) VALUES (?, DATETIME('now'))", (student_id,))
                                        st.success("Attendance marked (Time In).")
                                    
                            else:
                                display_error(f"Face recognition failed: {message}")
                        else:
                            display_warning("No face data registered for your profile. Please upload a profile photo with a clear face first.") # type: ignore
                else:
                    st.info("Please take a photo to mark your attendance.")


                # Display attendance
                st.subheader("Attendance History")
                with get_db_connection() as cursor:
                    cursor.execute("""
                        SELECT time_in, time_out FROM attendance WHERE student_id = ? ORDER BY time_in DESC
                    """, (student_id,))
                    attendance_records = cursor.fetchall()
                    
                    if attendance_records:
                        for record in attendance_records:
                            time_in = record[0]
                            time_out = record[1]
                            st.write(f"Time In: {time_in}, Time Out: {time_out if time_out else 'Not yet marked'}")
                    else:
                        st.info("No attendance records found.")


                # Result Input
                st.subheader("Submit / View Result")
                marks = st.number_input("Enter Marks (0-100):", min_value=0, max_value=100, step=1, key="marks_input")
                if st.button("Submit Marks"):
                    with get_db_connection() as cursor:
                            #check if result already exists
                        cursor.execute("SELECT id FROM results WHERE student_id = ?", (student_id,))
                        existing_result = cursor.fetchone()
                        if existing_result:
                            #update
                            cursor.execute("UPDATE results SET marks = ? WHERE student_id = ?", (marks, student_id))
                        else:
                            cursor.execute("INSERT INTO results (student_id, marks) VALUES (?, ?)", (student_id, marks))
                    st.success("Marks submitted!")

                if st.button("View Result"):
                    with get_db_connection() as cursor:
                        cursor.execute("""
                            SELECT r.marks, c.name FROM results r
                            JOIN students s ON r.student_id = s.id
                            JOIN courses c ON s.course_id = c.id
                            WHERE r.student_id = ?
                        """, (student_id,))
                        result = cursor.fetchone()
                    if result:
                        course_obj = Course(result[1]) # Create a Course object to use get_grade
                        grade = course_obj.get_grade(result[0])
                        st.write(f"**Marks:** {result[0]}, **Grade:** {grade}")
                    else:
                        st.info("Result not available yet. Please submit your marks.")

                if st.button("Print ID Card (Paid Service)"):
                    if student_data:
                        amount = 100  # Fixed amount for printing
                        token = "dummy_token" # Replace with a real payment token from your payment gateway
                        payment_status, payment_message = process_payment(amount, token)
                        if payment_status == "success":
                            st.success(f"Payment of {amount} successful. Printing ID card...")
                            id_card_bytes = generate_id_card(student_dict)  # regenerate
                            if id_card_bytes:
                                st.image(id_card_bytes, caption="Printed Student ID Card", use_column_width=True)
                                # You can add a download button here if you want users to download the image
                                st.download_button(
                                    label="Download ID Card",
                                    data=id_card_bytes,
                                    file_name="student_id_card.png",
                                    mime="image/png"
                                )
                        else:
                            st.error(f"Payment failed: {payment_message}")
                    else:
                        st.warning("Please submit your student information and generate the ID Card first.")
            else:
                st.info("Please fill out the student registration form above to get started.")

        # --- Admin Dashboard ---
        elif st.session_state['logged_in'] and st.session_state['role'] == 'admin':
            st.subheader("Admin Dashboard")
            st.write("Welcome Admin! You can manage users, courses, and teachers here.")

            # --- Display list of students for Admin ---
            st.write("### All Registered Students")
            with get_db_connection() as cursor:
                cursor.execute("""
                    SELECT s.name, s.roll_no, s.email, c.name AS course_name, t.name AS teacher_name
                    FROM students s
                    JOIN courses c ON s.course_id = c.id
                    JOIN teachers t ON s.favorite_teacher_id = t.id
                    ORDER BY s.name
                """)
                students_data = cursor.fetchall()
                if students_data:
                    # Prepare data for display
                    headers = ["Name", "Roll No", "Email", "Course", "Favorite Teacher"]
                    st.table(data=[headers] + list(students_data))
                else:
                    st.info("No students registered yet.")

            # --- Admin: Manage Courses ---
            st.write("### Manage Courses")
            with st.form("add_course_form"):
                new_course_name = st.text_input("New Course Name")
                add_course_button = st.form_submit_button("Add Course")
                if add_course_button:
                    if new_course_name:
                        with get_db_connection() as cursor:
                            try:
                                cursor.execute("INSERT INTO courses (name) VALUES (?)", (new_course_name,))
                                display_success(f"Course '{new_course_name}' added successfully!")
                            except sqlite3.IntegrityError:
                                display_error(f"Course '{new_course_name}' already exists.")
                    else:
                        display_error("Please enter a course name.")

            # Display existing courses
            with get_db_connection() as cursor:
                cursor.execute("SELECT name FROM courses")
                all_courses = [row[0] for row in cursor.fetchall()]
            st.write("**Existing Courses:**", ", ".join(all_courses) if all_courses else "None")


            # --- Admin: Manage Teachers ---
            st.write("### Manage Teachers")
            with st.form("add_teacher_form"):
                new_teacher_name = st.text_input("New Teacher Name")
                add_teacher_button = st.form_submit_button("Add Teacher")
                if add_teacher_button:
                    if new_teacher_name:
                        with get_db_connection() as cursor:
                            try:
                                cursor.execute("INSERT INTO teachers (name) VALUES (?)", (new_teacher_name,))
                                display_success(f"Teacher '{new_teacher_name}' added successfully!")
                            except sqlite3.IntegrityError:
                                display_error(f"Teacher '{new_teacher_name}' already exists.")
                    else:
                        display_error("Please enter a teacher name.")
            
            # Display existing teachers
            with get_db_connection() as cursor:
                cursor.execute("SELECT name FROM teachers")
                all_teachers = [row[0] for row in cursor.fetchall()]
            st.write("**Existing Teachers:**", ", ".join(all_teachers) if all_teachers else "None")

            # --- Admin: View Attendance of all students ---
            st.write("### All Student Attendance Records")
            with get_db_connection() as cursor:
                cursor.execute("""
                    SELECT s.name, s.roll_no, a.time_in, a.time_out
                    FROM attendance a
                    JOIN students s ON a.student_id = s.id
                    ORDER BY a.time_in DESC
                """)
                all_attendance_records = cursor.fetchall()

                if all_attendance_records:
                    st.table(data=[["Student Name", "Roll No", "Time In", "Time Out"]] + list(all_attendance_records))
                else:
                    st.info("No attendance records found yet.")

            # --- Admin: View All Results ---
            st.write("### All Student Results")
            with get_db_connection() as cursor:
                cursor.execute("""
                    SELECT s.name, s.roll_no, c.name AS course_name, r.marks
                    FROM results r
                    JOIN students s ON r.student_id = s.id
                    JOIN courses c ON s.course_id = c.id
                    ORDER BY s.name, c.name
                """)
                all_results = cursor.fetchall()

                if all_results:
                    st.table(data=[["Student Name", "Roll No", "Course", "Marks"]] + list(all_results))
                else:
                    st.info("No results submitted yet.")

if __name__ == "__main__":
    main()