# features.py
import random
import datetime
from PIL import Image, ImageDraw, ImageFont # type: ignore
import qrcode # type: ignore
from io import BytesIO
import streamlit as st # type: ignore # Streamlit is needed for st.error in case of font loading issues
import numpy as np # type: ignore # Needed for face_recognition encodings

# --- Face Recognition (REAL) ---
try:
    import face_recognition # type: ignore
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    st.warning("Face recognition library (face_recognition) not found. Face features will be simulated.")

def get_face_encoding_from_photo(photo_bytes):
    """
    Loads an image from bytes, finds faces, and returns the first face encoding.
    Returns None if no face is found or if face_recognition is not available.
    """
    if not FACE_RECOGNITION_AVAILABLE or not photo_bytes:
        return None, "Face recognition is not available or no photo provided."

    try:
        # Load the image from bytes
        image = face_recognition.load_image_file(BytesIO(photo_bytes))
        
        # Find all face encodings in the image
        face_encodings = face_recognition.face_encodings(image)

        if len(face_encodings) > 0:
            # Return the first face encoding found
            return face_encodings[0], "Face encoding generated successfully."
        else:
            return None, "No face found in the uploaded photo."
    except Exception as e:
        return None, f"Error processing photo for face recognition: {e}"

def recognize_face(known_face_encoding_bytes, current_photo_bytes):
    """
    Compares a new photo against a known face encoding.
    known_face_encoding_bytes: BLOB from DB (numpy array converted to bytes)
    current_photo_bytes: Bytes of the photo taken for attendance
    """
    if not FACE_RECOGNITION_AVAILABLE:
        return False, "Face recognition is not available."

    if not known_face_encoding_bytes:
        return False, "No registered face data found for this student."

    if not current_photo_bytes:
        return False, "No current photo provided for attendance."

    try:
        # Convert known encoding from bytes back to numpy array
        known_face_encoding = np.frombuffer(known_face_encoding_bytes)

        # Get encoding from the current attendance photo
        current_face_encodings, message = get_face_encoding_from_photo(current_photo_bytes)

        if current_face_encodings is None:
            return False, f"Could not detect face in current photo: {message}"

        # Compare faces
        # tolerance can be adjusted, smaller means stricter match
        matches = face_recognition.compare_faces([known_face_encoding], current_face_encodings, tolerance=0.5) 
        
        if matches[0]: # If the first (and only) known face matches
            return True, "Face recognized successfully."
        else:
            return False, "Face not recognized. Please try again."

    except Exception as e:
        return False, f"Error during face recognition: {e}"

# --- Payment Gateway (Dummy - Replace with a real integration) ---
def process_payment(amount, token):
    """
    Simulates processing a payment.
    Replace this with actual payment gateway integration (e.g., Stripe, PayPal).
    """
    # Use a library like requests to send the payment request to your provider.
    # You'll need to get API keys and set up an account with the provider.
    # For this example, we'll just return a dummy result.

    if not amount or not token:
        return "failure", "Invalid payment request"

    if amount <= 0:
        return "failure", "Invalid amount"
    
    # Simulate success/failure
    status = random.choice(["success", "failure"])
    message = "Payment successful" if status == "success" else "Payment failed"
    return status, message

# --- ID Card Generation ---
def generate_id_card(student_data):
    """Generates the student ID card image.

    Args:
        student_data (dict):  Dictionary containing student information.
    """
    # ID card dimensions
    width = 800
    height = 500

    # Create a new image with white background
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)

    # Font settings
    # IMPORTANT: Place 'arial.ttf' in the same directory as this script,
    # or provide the full path to a font file on your system.
    font_path = "arial.ttf"  
    try:
        title_font = ImageFont.truetype(font_path, 40)
        header_font = ImageFont.truetype(font_path, 24)
        text_font = ImageFont.truetype(font_path, 20)
        q3_font = ImageFont.truetype(font_path, 100)  # Q3 font
    except Exception as e:
        # Use st.error here as this function might be called directly by Streamlit
        st.error(f"Error loading font: {e}. Please make sure arial.ttf is in the same directory or provide the full path.")
        return None

    # Colors
    blue = (0, 71, 171)
    black = (0, 0, 0)

    # Add a border
    border_width = 5
    draw.rectangle([(0, 0), (width - 1, height - 1)], outline=blue, width=border_width)

    # Title
    title_text = "GIAIC Student ID Card"
    title_width = draw.textlength(title_text, font=title_font)
    title_x = (width - title_width) / 2
    draw.text((title_x, 20), title_text, fill=blue, font=title_font)

    # Add logo (dummy blue square)
    logo_width = 100
    logo_height = 100
    logo_x = 50
    logo_y = 80
    logo_img = Image.new('RGB', (logo_width, logo_height), color=blue)
    img.paste(logo_img, (logo_x, logo_y))

    # Q3 watermark
    q3_text = "Q3"
    bbox = draw.textbbox((0, 0), q3_text, font=q3_font)
    q3_width = bbox[2] - bbox[0]
    q3_height = bbox[3] - bbox[1]

    q3_x = (width - q3_width) / 2
    q3_y = (height - q3_height) / 2
    draw.text((q3_x, q3_y), q3_text, fill=(200, 200, 200, 128), font=q3_font)  # Light gray with alpha

    # Student Information
    start_x = logo_x + logo_width + 20
    start_y = logo_y
    line_height = 30

    # Student Photo
    photo_width = 120
    photo_height = 160
    photo_x = width - photo_width - 50
    photo_y = 80
    if student_data['photo']:
        try:
            student_photo = Image.open(BytesIO(student_data['photo']))
            student_photo = student_photo.resize((photo_width, photo_height))
            img.paste(student_photo, (photo_x, photo_y))
        except Exception as e:
            print(f"Error pasting photo: {e}")
            draw.rectangle([photo_x, photo_y, photo_x + photo_width, photo_y + photo_height], outline=blue,
                            fill=blue)  # Placeholder
            draw.text((photo_x + 10, photo_y + 60), "Photo", fill=black, font=text_font)
    else:
        draw.rectangle([photo_x, photo_y, photo_x + photo_width, photo_y + photo_height], outline=blue,
                        fill=blue)  # Placeholder
        draw.text((photo_x + 10, photo_y + 60), "Photo", fill=black, font=text_font)

    draw.text((start_x, start_y), "Name:", fill=black, font=header_font)
    draw.text((start_x + 150, start_y), student_data['name'], fill=black, font=text_font)

    draw.text((start_x, start_y + line_height), "Roll No:", fill=black, font=header_font)
    draw.text((start_x + 150, start_y + line_height), student_data['roll_no'], fill=black, font=text_font)

    draw.text((start_x, start_y + 2 * line_height), "Email:", fill=black, font=header_font)
    draw.text((start_x + 150, start_y + 2 * line_height), student_data['email'], fill=black, font=text_font)

    draw.text((start_x, start_y + 3 * line_height), "Slot:", fill=black, font=header_font)
    draw.text((start_x + 150, start_y + 3 * line_height), student_data['slot'], fill=black, font=text_font)

    draw.text((start_x, start_y + 4 * line_height), "Contact:", fill=black, font=header_font)
    draw.text((start_x + 150, start_y + 4 * line_height), student_data['contact'], fill=black, font=text_font)

    draw.text((start_x, start_y + 5 * line_height), "Course:", fill=black, font=header_font)
    draw.text((start_x + 150, start_y + 5 * line_height), student_data['course'], fill=black, font=text_font)

    draw.text((start_x, start_y + 6 * line_height), "Teacher:", fill=black, font=header_font)
    draw.text((start_x + 150, start_y + 6 * line_height), student_data['favorite_teacher'], fill=black,
              font=text_font)

    # Add QR code
    qr_data = f"Name: {student_data['name']}, Roll No: {student_data['roll_no']}, Email: {student_data['email']}, Course: {student_data['course']}"
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color=blue, back_color="white")

    qr_width, qr_height = qr_img.size
    qr_x = width - qr_width - 50
    qr_y = height - qr_height - 250  # Adjusted y position
    img.paste(qr_img, (qr_x, qr_y))

    # Add time in and time out
    if student_data.get('time_in'):
        time_in_str = student_data['time_in'] if isinstance(student_data['time_in'], str) else student_data['time_in'].strftime('%Y-%m-%d %H:%M:%S')
        draw.text((50, height - 80), f"Time In: {time_in_str}", fill=black, font=text_font)
    if student_data.get('time_out'):
        time_out_str = student_data['time_out'] if isinstance(student_data['time_out'], str) else student_data['time_out'].strftime('%Y-%m-%d %H:%M:%S')
        draw.text((50, height - 50), f"Time Out: {time_out_str}", fill=black, font=text_font)

    # Convert the image to bytes for Streamlit display
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes = img_bytes.getvalue()
    return img_bytes