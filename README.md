# CarePulse Hospital & Patient Health Portal (Python / Flask)

A full-stack Python hospital web application where patients can explore health conditions, check symptoms, find doctors, book appointments, calculate health metrics, and sign in to view lab reports, prescriptions, and vitals.

## Features

1. **A–Z Health Conditions Library** (`/health-library`) — Searchable encyclopedia covering causes, common symptoms, red-flag emergency warning signs, diagnostic tests, treatments, and prevention tips.
2. **Interactive Symptom Checker** (`/symptom-checker`) — Select symptoms and red flags to receive triage priority (`Emergency`, `Urgent`, or `Routine`) and matched specialist departments via `/api/symptom-check`.
3. **Doctors Directory & Appointment Booking** (`/doctors`, `/appointments/book`) — Filter physicians by department or specialty and schedule In-Person or Telehealth appointments.
4. **Departments, 24/7 Emergency & Lab Packages** (`/departments`) — Hospital wing locations, direct desk extensions, preventive checkup pricing, and fasting/prep instructions.
5. **Health Calculators & First Aid** (`/health-tools`) — BMI & healthy weight range, Blood Pressure stage analyzer, Target Heart Rate zones, Daily Hydration estimator, and Emergency First-Aid guide.
6. **Patient Health Portal** (`/portal`) — Secure patient login/registration, personal health profile, printable lab reports, active prescriptions with refill requests, appointment cancellation, and home vitals logging.

## Demo Patient Credentials

- **Email:** `patient@carepulse.org`
- **Password:** `Patient@123`

## Setup & Run (Windows PowerShell)

```powershell
cd C:\Users\ASUS\.gemini\antigravity\scratch\carepulse-hospital
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Open `http://127.0.0.1:5000` in your browser.

## Run Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
