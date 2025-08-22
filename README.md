Patil Boys Portal
Overview

Patil Boys Portal is a student management system that allows:

Adding and managing student details

Recording check-in and check-out activities

Simple user authentication for login

Data storage using CSV files (no traditional database)

Live Demo: https://patil-boys-portal.onrender.com/login

GitHub Repo: https://github.com/PatilBoys/patil_boys-portal

Features

✔ Student information management
✔ Check-in / Check-out tracking
✔ Simple login system
✔ CSV-based data storage
✔ Deployed on Render

Tech Stack

Backend: Python (Flask)

Frontend: HTML, CSS

Database: CSV files using Pandas

Database

This project uses CSV files instead of a traditional database:

students.csv → Stores student details (name, email, parent contact, etc.)

check_out.csv → Stores check-in and check-out logs

Data is managed using Python’s csv module and Pandas.

How to Run Locally

Clone the repository:

git clone https://github.com/PatilBoys/patil_boys-portal.git


Navigate to the project folder:

cd patil_boys-portal


Install dependencies:

pip install -r requirements.txt


Run the app:

python main.py


Open your browser and go to:

http://127.0.0.1:5000
