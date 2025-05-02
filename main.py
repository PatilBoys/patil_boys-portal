from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
import pandas as pd
import random
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os
import csv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
EMAIL_ID = os.getenv("EMAIL_ID")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# Temporary storage for OTPs
student_otps = {}
parent_otps = {}

# Paths
students_file = "data/students.csv"

# Registered emails
registered_students = set()
registered_parents = set()

# Function to load email data from CSV
def load_emails_from_csv(file_path):
    global registered_students, registered_parents
    try:
        with open(file_path, mode='r') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                # Use the exact column names provided in your CSV file
                if row['Student Email']:
                    registered_students.add(row['Student Email'].strip())
                if row['Parent Email']:
                    registered_parents.add(row['Parent Email'].strip())
    except Exception as e:
        print(f"Error reading CSV file: {e}")

# Call the function to load emails when the app starts
load_emails_from_csv(students_file)

# Function to validate email for the selected role
def is_valid_email(user_type, email):
    if user_type == 'student':
        return email in registered_students
    elif user_type == 'parent':
        return email in registered_parents
    return False

# Function to send OTP via email
def send_otp_email(email, otp):
    try:
        msg = MIMEText(f"Your OTP is: {otp}")
        msg['Subject'] = 'Login OTP'
        msg['From'] = EMAIL_ID
        msg['To'] = email

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_ID, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ID, email, msg.as_string())
        print(f"OTP {otp} sent to {email}")
    except Exception as e:
        print(f"Failed to send OTP to {email}: {e}")

# Home Route
@app.route('/')
def home():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_type = request.form.get('role')
        username = request.form.get('username')

        # Debug log
        print(f"User attempting to log in. Role: {user_type}, Email: {username}")

        # Validate that both role and username are provided
        if not user_type or not username:
            flash('Please select a role and enter your email.', 'error')
            return redirect(url_for('login'))

        # Admin login validation
        if user_type == 'admin':
            password = request.form.get('password')
            if not password:
                flash('Please enter the admin password.', 'error')
                return redirect(url_for('login'))

            if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                session['user_type'] = 'admin'
                flash('Login successful! Welcome, Admin.', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Invalid admin credentials. Please try again.', 'error')
                return redirect(url_for('login'))

        # Load and validate email from students.csv
        try:
            students_df = pd.read_csv('data/students.csv')
        except FileNotFoundError:
            flash('Student data file not found. Please check your setup.', 'error')
            return redirect(url_for('login'))

        if user_type == 'student':
            valid_emails = students_df['Student Email'].dropna().tolist()
            if username not in valid_emails:
                flash('Invalid email for Student. Please try again.', 'error')
                return redirect(url_for('login'))
        elif user_type == 'parent':
            valid_emails = students_df['Parent Email'].dropna().tolist()
            if username not in valid_emails:
                flash('Invalid email for Parent. Please try again.', 'error')
                return redirect(url_for('login'))
        else:
            flash('Invalid role selected. Please try again.', 'error')
            return redirect(url_for('login'))

        # Generate OTP for valid email
        otp = str(random.randint(1000, 9999))
        if user_type == 'student':
            student_otps[username] = otp
        elif user_type == 'parent':
            parent_otps[username] = otp

        send_otp_email(username, otp)
        session['pending_user_type'] = user_type
        session['pending_email'] = username
        flash('OTP sent to your email. Please check your inbox.', 'info')
        return redirect(url_for('otp_login'))  # Redirect to OTP login page

    return render_template('login.html')

@app.route('/otp_login', methods=['GET', 'POST'])
def otp_login():
    if request.method == 'POST':
        otp_entered = request.form['otp']
        email = session.get('pending_email')
        user_type = session.get('pending_user_type')

        # Check if the session exists for the email and user type
        if not email or not user_type:
            flash('Session expired. Please log in again.', 'error')
            return redirect(url_for('login'))

        # Retrieve the correct OTP based on user type
        correct_otp = None
        if user_type == 'student':
            correct_otp = student_otps.get(email)
        elif user_type == 'parent':
            correct_otp = parent_otps.get(email)

        if correct_otp and otp_entered == correct_otp:
            session['user_type'] = user_type
            session['email'] = email
            flash('OTP verified successfully! Redirecting...', 'success')

            # Clear the OTP from the session after successful verification
            if user_type == 'student':
                del student_otps[email]
            elif user_type == 'parent':
                del parent_otps[email]

            # Redirect to the appropriate dashboard based on user type
            if user_type == 'student':
                return redirect(url_for('student_dashboard'))
            elif user_type == 'parent':
                return redirect(url_for('parent_dashboard'))
        else:
            flash('Incorrect OTP or OTP expired. Please try again.', 'error')

    return render_template('verify_otp.html')

    
# Admin Dashboard Route
@app.route('/admin_dashboard')
def admin_dashboard():
    if session.get('user_type') != 'admin':
        return redirect(url_for('login'))

    if os.path.exists('data/students.csv'):
        students = pd.read_csv('data/students.csv')
    else:
        students = pd.DataFrame(columns=['Name', 'Roll No', 'Class', 'Parent Email', 'Student Email'])

    students_list = students.to_dict(orient='records')
    return render_template('admin_dashboard.html', students=students_list)

@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if session.get('user_type') != 'admin':
        return redirect(url_for('login'))

    student_data_path = 'data/students.csv'  # Ensure this path matches your setup

    if request.method == 'POST':
        # Get form data
        name = request.form['name']
        roll_no = request.form['roll_no']
        student_class = request.form['class']
        parent_email = request.form['parent_email']
        student_email = request.form['student_email']

        # Read existing student data from CSV
        try:
            students = pd.read_csv(student_data_path)
        except FileNotFoundError:
            # Create a new dataframe if the file does not exist
            students = pd.DataFrame(columns=['Name', 'Roll No', 'Class', 'Parent Email', 'Student Email'])

        # Check if the roll number already exists
        if not students[students['Roll No'] == roll_no].empty:
            flash("Roll number already exists. Please use a unique roll number.", "error")
            return redirect(url_for('add_student'))

        # Add new student to the dataframe
        new_student = {
            'Name': name,
            'Roll No': roll_no,
            'Class': student_class,
            'Parent Email': parent_email,
            'Student Email': student_email
        }
        students = pd.concat([students, pd.DataFrame([new_student])], ignore_index=True)

        # Save updated data back to CSV
        students.to_csv(student_data_path, index=False)

        flash(f"Student {name} added successfully!", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template('add_student.html')

# Route to edit a student's details
@app.route('/edit_student', methods=['POST'])
def edit_student():
    if session.get('user_type') != 'admin':
        return redirect(url_for('login'))

    # Load the students CSV file
    students_file_path = 'data/students.csv'
    students = pd.read_csv(students_file_path)

    # Identify the student to edit using the Roll No
    roll_no_to_edit = request.form.get('roll_no')

    # Check if the student exists
    student_index = students[students['Roll No'] == roll_no_to_edit].index
    if student_index.empty:
        flash("Student not found", "error")
        return redirect(url_for('admin_dashboard'))

    # Update student details
    student_index = student_index[0]  # Extract the single index
    students.at[student_index, 'Name'] = request.form.get(f'name_{roll_no_to_edit}')
    students.at[student_index, 'Class'] = request.form.get(f'class_{roll_no_to_edit}')
    students.at[student_index, 'Parent Email'] = request.form.get(f'parent_email_{roll_no_to_edit}')
    students.at[student_index, 'Student Email'] = request.form.get(f'student_email_{roll_no_to_edit}')

    # Save the updated data back to the CSV file
    students.to_csv(students_file_path, index=False)

    flash("Student details updated successfully", "success")
    return redirect(url_for('admin_dashboard'))


#delete student route
@app.route('/delete_student', methods=['POST'])
def delete_student():
    if session.get('user_type') != 'admin':
        return redirect(url_for('login'))

    roll_no_to_delete = request.form['roll_no']
    student_data_path = 'data/students.csv'

    # Load existing student data
    try:
        students = pd.read_csv(student_data_path)
    except FileNotFoundError:
        flash("No student data found.", "error")
        return redirect(url_for('admin_dashboard'))

    # Check if the roll number exists
    if students[students['Roll No'] == roll_no_to_delete].empty:
        flash("Student not found.", "error")
        return redirect(url_for('admin_dashboard'))

    # Remove the student with the matching roll number
    students = students[students['Roll No'] != roll_no_to_delete]
    students.to_csv(student_data_path, index=False)

    flash("Student deleted successfully.", "success")
    return redirect(url_for('admin_dashboard'))

# Student Dashboard Route
@app.route('/student_dashboard')
def student_dashboard():
    if session.get('user_type') != 'student':
        return redirect(url_for('login'))

    # Retrieve the student's email from the session
    email = session.get('email')

    # Load student data from the CSV
    students = pd.read_csv('data/students.csv')

    # Find the student by email
    student = students[students['Student Email'] == email].iloc[0]
    student_name = student['Name']  # Extract the student's name

    return render_template('student_dashboard.html', student_name=student_name)


# Submit In/Out Details Route

@app.route('/submit_in_out_details', methods=['POST'])
def submit_in_out_details():
    if session.get('user_type') != 'student':
        return redirect(url_for('login'))

    email = session.get('email')
    in_out = request.form.get('in_out')
    check_out_data_path = 'data/check_out.csv'

    # Load check-out data
    try:
        check_out_data = pd.read_csv(check_out_data_path)
    except FileNotFoundError:
        # Initialize the file if it doesn't exist
        check_out_data = pd.DataFrame(columns=['email', 'check_in_time', 'reason', 'expected_return', 'status', 'check_out_time'])
        check_out_data.to_csv(check_out_data_path, index=False)

    # Get the last record for the student
    last_record = check_out_data[check_out_data['email'] == email].tail(1)

    if in_out == 'In':
        # If last record exists and the student is already checked in, prevent new check-in
        if not last_record.empty and last_record['status'].iloc[0] == 'Checked In':
            flash("You are already checked in. Please check out before checking in again.", "error")
            return redirect(url_for('student_dashboard'))

        # Record Check-IN time
        check_in_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_record = {
            'email': email,
            'check_in_time': check_in_time,
            'reason': "N/A",
            'expected_return': "N/A",
            'status': 'Checked In',
            'check_out_time': "N/A"
        }

        # Append new record for check-in
        check_out_data = pd.concat([check_out_data, pd.DataFrame([new_record])], ignore_index=True)
        check_out_data.to_csv(check_out_data_path, index=False)

        flash(f"Checked IN successfully at {check_in_time}.", "success")

    elif in_out == 'Out':
        # If last record exists and the student is already checked out, prevent new check-out
        if not last_record.empty and last_record['status'].iloc[0] == 'Checked Out':
            flash("You are already checked out. Cannot check out again.", "error")
            return redirect(url_for('student_dashboard'))

        # Ensure Expected Return is provided
        expected_return = request.form.get('expected_return')
        if not expected_return:
            flash("Expected return time is required for checking out.", "error")
            return redirect(url_for('student_dashboard'))

        # Record Check-OUT time
        check_out_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        reason = request.form.get('reason', "N/A")
        if reason == 'Other':
            reason = request.form.get('other_reason', "N/A")

        new_record = {
            'email': email,
            'check_in_time': "N/A",
            'reason': reason,
            'expected_return': expected_return,
            'status': 'Checked Out',
            'check_out_time': check_out_time
        }

        # Append new record for check-out
        check_out_data = pd.concat([check_out_data, pd.DataFrame([new_record])], ignore_index=True)
        check_out_data.to_csv(check_out_data_path, index=False)

        flash(f"Checked OUT successfully at {check_out_time}.", "success")

    return redirect(url_for('student_dashboard'))



# Parent Dashboard Route
@app.route('/parent_dashboard')
def parent_dashboard():
    # Ensure only parents can access this route
    if session.get('user_type') != 'parent':
        return redirect(url_for('login'))

    # Retrieve the logged-in parent's email
    parent_email = session.get('email')
    if not parent_email:
        return redirect(url_for('login'))

    # Load the students.csv file to map parent emails to student emails
    try:
        students_data = pd.read_csv('data/students.csv')
    except Exception as e:
        print(f"Error loading students.csv: {e}")
        return "Error loading data. Please contact the administrator."

    # Find the student email associated with the parent
    student_row = students_data[students_data['Parent Email'] == parent_email]
    if student_row.empty:
        return "No student found for this parent."
    student_email = student_row.iloc[0]['Student Email']
    student_name = student_row.iloc[0]['Name']

    # Load the check_out.csv file to get in/out records
    try:
        check_out_data = pd.read_csv('data/check_out.csv')

        # Filter the student-specific data
        student_records = check_out_data[check_out_data['email'] == student_email].to_dict(orient='records')

        # Determine the current status
        current_status = "Unknown"
        if student_records:
            latest_record = student_records[-1]  # Get the latest entry
            if latest_record['status'] == 'Checked In':
                current_status = "HOSTEL"
            elif latest_record['status'] == 'Checked Out':
                current_status = latest_record['reason'] if latest_record['reason'] else "OUT"

    except KeyError as ke:
        print(f"KeyError: Missing key in the data - {ke}")
        return "Error loading data. Please contact the administrator."
    except Exception as e:
        print(f"Unexpected error: {e}")
        return "Error loading data. Please contact the administrator."

    # Pass data to the parent dashboard template
    return render_template(
        'parent_dashboard.html',
        student_name=student_name,
        child=student_records,
        current_status=current_status
    )


# Send OTP Email Function
def send_otp_email(to_email, otp):
    subject = "Your OTP for Patil Boys Hostel Login"
    body = f"Dear User,\n\nYour OTP is {otp}\n\nRegards,\nPatil Boys Hostel"

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_ID
    msg['To'] = to_email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_ID, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ID, to_email, msg.as_string())
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == '__main__':
    app.run(debug=True)
