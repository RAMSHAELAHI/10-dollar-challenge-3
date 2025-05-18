# utils.py
import streamlit as st # type: ignore

def display_error(message):
    """Displays an error message in Streamlit."""
    st.error(message)

def display_success(message):
    """Displays a success message in Streamlit."""
    st.success(message)

def validate_input(name, roll_no, email, slot, contact, course, favorite_teacher, photo):
    """Validates input fields."""
    if not name:
        return "Please enter your name."
    if not roll_no:
        return "Please enter your roll number."
    if not email:
        return "Please enter your email."
    if not slot:
        return "Please enter your slot."
    if not contact:
        return "Please enter your contact number."
    if not course:
        return "Please select a course."
    if not favorite_teacher:
        return "Please select your favorite teacher."
    if not photo:
        return "Please upload a photo."
    return None  # Returns None if all inputs are valid

class Course:
    """A dummy Course class to encapsulate grade logic."""
    def __init__(self, name):
        self.name = name

    def get_grade(self, marks):
        if marks >= 90:
            return "A"
        elif marks >= 80:
            return "B"
        elif marks >= 70:
            return "C"
        elif marks >= 60:
            return "D"
        else:
            return "F"