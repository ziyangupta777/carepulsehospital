"""Insert Ziyan Gupta user into the SQLite database for testing."""
import os, sqlite3
from werkzeug.security import generate_password_hash

# Resolve the database path used by the app
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'hospital.db')

if not os.path.exists(DB_PATH):
    raise FileNotFoundError(f'Database not found at {DB_PATH}')

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Prepare user data
full_name = 'Ziyan Gupta'
email = 'ziyan@example.com'
password = 'Password123'  # default password
password_hash = generate_password_hash(password)
phone = '6359662010'
date_of_birth = '2006-01-01'  # placeholder DOB; age 20 approx (2026-2006)
gender = 'Male'
blood_group = 'O+'
allergies = 'None reported'
chronic_conditions = 'None reported'
emergency_contact = '6359662010'

# Insert if not exists
cur.execute('SELECT id FROM patients WHERE email = ?', (email,))
if cur.fetchone() is None:
    cur.execute('''
        INSERT INTO patients (full_name, email, password_hash, phone, date_of_birth, gender, blood_group, allergies, chronic_conditions, emergency_contact)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    ''', (full_name, email, password_hash, phone, date_of_birth, gender, blood_group, allergies, chronic_conditions, emergency_contact))
    conn.commit()
    print('Inserted Ziyan Gupta user.')
else:
    print('User already exists.')

conn.close()
