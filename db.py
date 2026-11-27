"""Database initialization, schema definition, and seed data for CarePulse Hospital."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from werkzeug.security import generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = (
    Path("/tmp/hospital.db")
    if os.environ.get("VERCEL")
    else BASE_DIR / "instance" / "hospital.db"
)


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Return a SQLite connection with row factory and foreign keys enabled."""
    target = Path(db_path) if db_path else DEFAULT_DB_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    tagline TEXT NOT NULL,
    description TEXT NOT NULL,
    floor_location TEXT NOT NULL,
    phone_ext TEXT NOT NULL,
    is_emergency INTEGER NOT NULL DEFAULT 0,
    icon TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS doctors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    qualification TEXT NOT NULL,
    department_slug TEXT NOT NULL,
    specialty TEXT NOT NULL,
    experience_years INTEGER NOT NULL,
    languages TEXT NOT NULL,
    available_days TEXT NOT NULL,
    consultation_fee INTEGER NOT NULL,
    bio TEXT NOT NULL,
    FOREIGN KEY (department_slug) REFERENCES departments(slug)
);

CREATE TABLE IF NOT EXISTS conditions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    department_slug TEXT NOT NULL,
    urgency TEXT NOT NULL,
    summary TEXT NOT NULL,
    causes TEXT NOT NULL,
    symptoms_json TEXT NOT NULL,
    red_flags_json TEXT NOT NULL,
    diagnosis_tests_json TEXT NOT NULL,
    treatment TEXT NOT NULL,
    prevention TEXT NOT NULL,
    FOREIGN KEY (department_slug) REFERENCES departments(slug)
);

CREATE TABLE IF NOT EXISTS lab_packages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price INTEGER NOT NULL,
    turnaround_hours INTEGER NOT NULL,
    fasting_required INTEGER NOT NULL DEFAULT 0,
    preparation_notes TEXT NOT NULL,
    included_tests_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    phone TEXT NOT NULL,
    date_of_birth TEXT NOT NULL,
    gender TEXT NOT NULL,
    blood_group TEXT NOT NULL,
    allergies TEXT NOT NULL DEFAULT 'None reported',
    chronic_conditions TEXT NOT NULL DEFAULT 'None reported',
    emergency_contact TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER,
    patient_name TEXT NOT NULL,
    patient_email TEXT NOT NULL,
    patient_phone TEXT NOT NULL,
    doctor_id INTEGER NOT NULL,
    appointment_date TEXT NOT NULL,
    time_slot TEXT NOT NULL,
    visit_type TEXT NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Confirmed',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(id),
    FOREIGN KEY (doctor_id) REFERENCES doctors(id)
);

CREATE TABLE IF NOT EXISTS lab_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    report_code TEXT UNIQUE NOT NULL,
    test_name TEXT NOT NULL,
    ordered_by TEXT NOT NULL,
    report_date TEXT NOT NULL,
    overall_status TEXT NOT NULL,
    summary_notes TEXT NOT NULL,
    metrics_json TEXT NOT NULL,
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);

CREATE TABLE IF NOT EXISTS prescriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    medication_name TEXT NOT NULL,
    dosage TEXT NOT NULL,
    frequency TEXT NOT NULL,
    duration TEXT NOT NULL,
    prescribed_by TEXT NOT NULL,
    prescribed_date TEXT NOT NULL,
    instructions TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Active',
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);

CREATE TABLE IF NOT EXISTS vitals_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    recorded_at TEXT NOT NULL,
    systolic INTEGER NOT NULL,
    diastolic INTEGER NOT NULL,
    heart_rate INTEGER NOT NULL,
    blood_sugar INTEGER NOT NULL,
    spo2 INTEGER NOT NULL,
    weight_kg REAL NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);
"""


def init_and_seed(db_path: Path | str | None = None) -> None:
    """Create tables if needed and populate initial hospital and health data."""
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        existing_depts = conn.execute("SELECT COUNT(*) FROM departments").fetchone()[0]
        if existing_depts == 0:
            _seed_hospital_data(conn)
        conn.commit()
    finally:
        conn.close()


def _seed_hospital_data(conn: sqlite3.Connection) -> None:
    departments = [
        (
            "emergency",
            "24/7 Emergency & Trauma Care",
            "Rapid triage, cardiac resuscitation, and trauma stabilization",
            "Equipped with advanced trauma bays, 24/7 CT/MRI access, ambulance dispatch, and dedicated cardiac and stroke response teams.",
            "Ground Floor, North Wing",
            "Ext. 100 / Toll-Free 108",
            1,
            "ambulance",
        ),
        (
            "cardiology",
            "Cardiology & Heart Care",
            "Preventive cardiology, ECG, echocardiography, and hypertension care",
            "Comprehensive diagnosis and long-term management of heart disease, arrhythmias, cholesterol disorders, and blood pressure.",
            "2nd Floor, Heart Pavilion",
            "Ext. 210",
            0,
            "heart",
        ),
        (
            "general-medicine",
            "Internal & General Medicine",
            "Primary care, fevers, diabetes, thyroid, and preventive checkups",
            "First-stop adult care for acute infections, metabolic health, diabetes management, chronic fatigue, and annual physicals.",
            "1st Floor, Main Block",
            "Ext. 145",
            0,
            "stethoscope",
        ),
        (
            "pulmonology",
            "Pulmonology & Respiratory Care",
            "Asthma, COPD, sleep apnea, and respiratory infections",
            "Pulmonary function testing, bronchoscopy, allergy-linked asthma plans, and post-infection lung recovery.",
            "3rd Floor, East Wing",
            "Ext. 312",
            0,
            "lungs",
        ),
        (
            "neurology",
            "Neurology & Brain Care",
            "Migraine, stroke prevention, epilepsy, and nerve disorders",
            "Specialized neurological evaluations, EEG diagnostics, headache clinics, and neuro-rehabilitation support.",
            "4th Floor, Neuro Center",
            "Ext. 418",
            0,
            "brain",
        ),
        (
            "orthopedics",
            "Orthopedics & Joint Care",
            "Fractures, arthritis, sports injuries, and spine health",
            "Digital X-ray, arthroscopy, joint preservation therapy, and physical rehabilitation for bone and muscle recovery.",
            "2nd Floor, West Wing",
            "Ext. 265",
            0,
            "bone",
        ),
        (
            "pediatrics",
            "Pediatrics & Child Health",
            "Immunizations, growth tracking, and childhood illness care",
            "Friendly pediatric care from newborn screenings and vaccination schedules to adolescent wellness.",
            "1st Floor, Family Wing",
            "Ext. 180",
            0,
            "child",
        ),
        (
            "gastroenterology",
            "Gastroenterology & Digestive Health",
            "Acid reflux, IBS, liver health, and endoscopic diagnostics",
            "Evidence-based nutrition and medical care for digestive disorders, hepatitis screening, and gut health.",
            "3rd Floor, West Wing",
            "Ext. 340",
            0,
            "digestive",
        ),
    ]
    conn.executemany(
        """
        INSERT INTO departments (slug, name, tagline, description, floor_location, phone_ext, is_emergency, icon)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        departments,
    )

    doctors = [
        (
            "Dr. Meera Nair",
            "MD, DM (Cardiology)",
            "cardiology",
            "Interventional & Preventive Cardiology",
            14,
            "English, Hindi, Malayalam",
            "Mon, Tue, Thu, Sat",
            800,
            "Specializes in early heart risk detection, hypertension control, and non-invasive cardiac imaging.",
        ),
        (
            "Dr. Arjun Kulkarni",
            "MD (Internal Medicine)",
            "general-medicine",
            "Diabetes, Thyroid & Metabolic Care",
            11,
            "English, Hindi, Marathi",
            "Mon - Sat",
            600,
            "Focuses on holistic chronic disease reversal, fever evaluation, and personalized preventive checkups.",
        ),
        (
            "Dr. Sofia Rahman",
            "MD (Pulmonary Medicine)",
            "pulmonology",
            "Asthma, Allergies & Sleep Medicine",
            9,
            "English, Hindi, Bengali",
            "Tue, Wed, Fri, Sat",
            750,
            "Guides patients through inhaler optimization, post-viral cough care, and sleep apnea testing.",
        ),
        (
            "Dr. Vikramaditya Rao",
            "MD, DM (Neurology)",
            "neurology",
            "Headache, Stroke & Nerve Disorders",
            16,
            "English, Telugu, Hindi",
            "Mon, Wed, Fri",
            900,
            "Leads the rapid stroke clinic and comprehensive migraine prevention programs.",
        ),
        (
            "Dr. Elena D'Souza",
            "MS (Orthopedics)",
            "orthopedics",
            "Sports Medicine & Joint Preservation",
            12,
            "English, Konkani, Hindi",
            "Mon, Tue, Thu, Fri",
            750,
            "Treats ligament injuries, knee osteoarthritis, and posture-related back pain with conservative-first protocols.",
        ),
        (
            "Dr. Kabir Malhotra",
            "MD (Pediatrics)",
            "pediatrics",
            "Child Wellness & Immunization",
            10,
            "English, Hindi, Punjabi",
            "Mon - Sat",
            650,
            "Dedicated to developmental milestones, childhood nutrition, and anxiety-free pediatric visits.",
        ),
        (
            "Dr. Ananya Sen",
            "MD, DM (Gastroenterology)",
            "gastroenterology",
            "Digestive, Liver & Gut Health",
            13,
            "English, Bengali, Hindi",
            "Tue, Thu, Sat",
            850,
            "Helps patients manage GERD, fatty liver, and irritable bowel syndrome through targeted therapy.",
        ),
        (
            "Dr. Rohan Deshmukh",
            "MD (Emergency Medicine)",
            "emergency",
            "Acute Trauma & Emergency Triage",
            8,
            "English, Hindi, Marathi",
            "24/7 Rotational",
            500,
            "Heads acute stabilization protocols, poison control, and rapid cardiac emergency response.",
        ),
    ]
    conn.executemany(
        """
        INSERT INTO doctors (name, qualification, department_slug, specialty, experience_years, languages, available_days, consultation_fee, bio)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        doctors,
    )

    conditions = [
        (
            "hypertension",
            "Hypertension (High Blood Pressure)",
            "cardiology",
            "Routine / Monitor",
            "Persistent elevation of blood pressure in the arteries (typically >= 130/80 mmHg), often without noticeable symptoms until organs are strained.",
            "High sodium intake, chronic stress, excess body weight, sedentary lifestyle, kidney disease, sleep apnea, and family genetics.",
            ["Headache", "Dizziness", "Blurred Vision", "Chest Tightness", "Fatigue", "Shortness of Breath"],
            [
                "Blood pressure reading >= 180/120 mmHg",
                "Sudden severe chest pain or pressure",
                "Difficulty speaking, facial drooping, or sudden weakness",
                "Severe shortness of breath or vision loss",
            ],
            ["Automated BP Monitoring (24-hr ABPM)", "Basic Metabolic Panel (Kidney & Electrolytes)", "12-Lead ECG", "Lipid Profile"],
            "Lifestyle modifications (DASH diet, sodium under 1,500–2,300 mg/day, 150 min/week brisk walking) combined with prescribed antihypertensive medicines when needed.",
            "Check blood pressure monthly, limit ultra-processed foods, maintain healthy weight, manage stress, and avoid tobacco.",
        ),
        (
            "type-2-diabetes",
            "Type 2 Diabetes",
            "general-medicine",
            "Routine / Monitor",
            "A chronic metabolic condition where the body resists insulin or does not produce enough to keep blood glucose within a healthy range.",
            "Insulin resistance, abdominal obesity, physical inactivity, family history, and high refined-carbohydrate diets.",
            ["Frequent Urination", "Excessive Thirst", "Fatigue", "Blurred Vision", "Slow Healing Wounds", "Tingling in Feet"],
            [
                "Blood sugar > 300 mg/dL with vomiting or fruity breath",
                "Confusion, severe drowsiness, or fainting",
                "Signs of severe hypoglycemia (< 54 mg/dL) like shaking or loss of consciousness",
            ],
            ["HbA1c (3-Month Average)", "Fasting Blood Glucose", "Post-Prandial Glucose", "Urine Microalbumin & Kidney Panel"],
            "Structured nutrition plan with balanced fiber and protein, regular aerobic and resistance exercise, glucose monitoring, and medications such as metformin or GLP-1/SGLT2 therapies.",
            "Maintain waist circumference in a healthy range, walk 15 minutes after meals, prioritize sleep, and get annual HbA1c screening after age 35.",
        ),
        (
            "asthma",
            "Bronchial Asthma",
            "pulmonology",
            "Urgent if Flare-up",
            "Chronic airway inflammation causing episodic narrowing, excess mucus, and difficulty breathing triggered by allergens, cold air, or exercise.",
            "Genetic predisposition, dust mites, pollen, air pollution, viral respiratory infections, and workplace irritants.",
            ["Wheezing", "Shortness of Breath", "Chest Tightness", "Persistent Cough", "Nighttime Coughing"],
            [
                "Lips or fingernails turning bluish or gray",
                "Inability to speak full sentences due to breathlessness",
                "Rescue inhaler provides no relief after repeated puffs",
            ],
            ["Spirometry (Lung Function Test)", "Peak Expiratory Flow Rate", "Chest X-Ray", "Allergy Skin or IgE Panel"],
            "Controller inhaled corticosteroids to calm airway inflammation plus fast-acting rescue bronchodilators and a written Asthma Action Plan.",
            "Identify and reduce indoor allergens, use air filtration during high-pollution days, get annual flu vaccines, and follow inhaler technique.",
        ),
        (
            "migraine",
            "Migraine Headache",
            "neurology",
            "Routine / Urgent if Sudden",
            "A neurological condition causing throbbing moderate-to-severe headaches, frequently one-sided and accompanied by nausea or light sensitivity.",
            "Neurovascular nerve signaling changes, hormonal shifts, dehydration, skipped meals, sleep disruption, and sensory overload.",
            ["Throbbing Headache", "Nausea", "Sensitivity to Light", "Visual Aura", "Dizziness", "Neck Stiffness"],
            [
                "Sudden 'thunderclap' worst headache of life",
                "Headache with high fever, stiff neck, or rash",
                "New weakness, numbness, confusion, or slurred speech",
            ],
            ["Clinical Neurological Exam", "Brain MRI (if atypical signs)", "Vision & Optic Nerve Check"],
            "Early acute abortive therapy (triptans, NSAIDs, anti-nausea agents) in a dark quiet room, plus preventive therapy for frequent monthly attacks.",
            "Keep a trigger diary, stay hydrated, wake and sleep at consistent hours, and limit excess caffeine.",
        ),
        (
            "gerd",
            "Acid Reflux & GERD",
            "gastroenterology",
            "Routine",
            "Gastroesophageal reflux disease occurs when stomach acid repeatedly flows back into the esophagus, irritating its lining.",
            "Weakened lower esophageal sphincter, hiatal hernia, late heavy meals, spicy/fatty foods, smoking, and obesity.",
            ["Heartburn", "Sour Regurgitation", "Chest Discomfort", "Sore Throat", "Bloating", "Nausea"],
            [
                "Chest pain radiating to arm, jaw, or back (rule out heart attack immediately)",
                "Difficulty or pain when swallowing food",
                "Vomiting blood or black tarry stools",
            ],
            ["Upper GI Endoscopy (if persistent)", "H. pylori Breath/Stool Test", "Abdominal Ultrasound"],
            "Dietary adjustments, elevating head of bed, avoiding lying down within 3 hours of eating, and acid-suppressing medication when prescribed.",
            "Eat smaller evening meals, limit caffeine/carbonated drinks, and maintain healthy weight.",
        ),
        (
            "osteoarthritis",
            "Knee & Joint Osteoarthritis",
            "orthopedics",
            "Routine",
            "Gradual wear-and-tear breakdown of protective joint cartilage leading to stiffness, swelling, and pain during movement.",
            "Aging, previous joint injury, repetitive high-impact strain, excess weight on weight-bearing joints, and genetics.",
            ["Joint Pain", "Morning Stiffness", "Joint Swelling", "Reduced Mobility", "Clicking Sensation"],
            [
                "Sudden hot, red, severely swollen joint with fever (possible septic arthritis)",
                "Inability to bear weight after a fall or twist",
            ],
            ["Digital Weight-Bearing X-Ray", "Vitamin D & Inflammatory Markers (ESR/CRP)", "Orthopedic Gait Evaluation"],
            "Targeted physiotherapy to strengthen supporting muscles, low-impact exercise (swimming, cycling), topical/oral pain relief, and weight management.",
            "Keep quadriceps and core strong, wear cushioned footwear, and avoid prolonged squatting or sudden load spikes.",
        ),
        (
            "viral-fever",
            "Acute Viral Fever & Influenza",
            "general-medicine",
            "Urgent if High Fever",
            "Systemic immune response to seasonal respiratory or viral infections causing fever, body aches, and fatigue.",
            "Influenza, seasonal coronaviruses, adenoviruses, or vector-borne viruses depending on season and exposure.",
            ["Fever", "Body Aches", "Chills", "Sore Throat", "Persistent Cough", "Fatigue", "Headache"],
            [
                "Fever above 103 F (39.4 C) not responding to medication",
                "Persistent vomiting, inability to keep fluids down",
                "Difficulty breathing, chest pain, or confusion",
                "Fever lasting longer than 3–4 days or accompanied by skin rash",
            ],
            ["Complete Blood Count (CBC)", "Rapid Viral Antigen / PCR Swab", "Dengue / Malaria Panel (if clinically indicated)"],
            "Rest, oral rehydration solutions, antipyretics as directed by a doctor, and early antiviral medication when appropriate for high-risk patients.",
            "Practice frequent hand hygiene, stay updated on seasonal flu vaccinations, and mask in crowded indoor spaces when unwell.",
        ),
        (
            "acute-coronary",
            "Chest Pain & Cardiac Emergency",
            "emergency",
            "Emergency - Call 108",
            "Reduced blood flow to heart muscle that requires immediate emergency evaluation to prevent heart attack and tissue damage.",
            "Plaque buildup in coronary arteries, blood clots, severe hypertension crisis, or coronary spasm.",
            ["Chest Pain", "Chest Tightness", "Shortness of Breath", "Sweating", "Nausea", "Dizziness"],
            [
                "Crushing pressure or heaviness in center of chest lasting > 5 minutes",
                "Pain spreading to left arm, shoulder, neck, jaw, or back",
                "Cold sweats, sudden lightheadedness, or fainting",
            ],
            ["Immediate 12-Lead ECG (within 10 mins)", "High-Sensitivity Troponin Blood Test", "Emergency Echocardiogram"],
            "Immediate emergency room activation: oxygen support, antiplatelet therapy, continuous cardiac monitoring, and urgent angiography if indicated.",
            "Control blood pressure, LDL cholesterol, and blood sugar; stop smoking; never drive yourself during suspected cardiac chest pain.",
        ),
        (
            "iron-deficiency-anemia",
            "Iron-Deficiency Anemia",
            "general-medicine",
            "Routine",
            "Low healthy red blood cell count caused by insufficient iron to make hemoglobin, reducing oxygen delivery throughout the body.",
            "Low dietary iron, poor absorption, heavy menstrual bleeding, or chronic gastrointestinal blood loss.",
            ["Fatigue", "Dizziness", "Pale Skin", "Shortness of Breath", "Cold Hands and Feet", "Headache"],
            [
                "Fainting or rapid pounding heartbeat at rest",
                "Severe breathlessness climbing a single flight of stairs",
            ],
            ["Complete Blood Count (CBC)", "Serum Ferritin & Iron Studies", "Peripheral Blood Smear"],
            "Identifying and treating the root cause plus oral or IV iron supplementation paired with vitamin C to enhance absorption.",
            "Include iron-rich foods (lentils, spinach, lean meats, fortified grains) and avoid drinking tea/coffee immediately with iron-rich meals.",
        ),
        (
            "pediatric-ear-infection",
            "Childhood Ear Infection (Otitis Media)",
            "pediatrics",
            "Urgent (Same-Day Clinic)",
            "Fluid buildup and bacterial or viral inflammation behind the eardrum, common in young children after colds.",
            "Blocked Eustachian tubes following upper respiratory congestion or allergies.",
            ["Ear Pain", "Fever", "Irritability", "Difficulty Sleeping", "Reduced Appetite"],
            [
                "Fluid, pus, or blood draining from the ear canal",
                "High fever in an infant under 3 months",
                "Swelling or redness behind the ear bone",
            ],
            ["Otoscope Ear Exam", "Tympanometry (if recurrent)"],
            "Age-appropriate pain relief, careful monitoring for mild viral cases, and prescribed pediatric antibiotics when clinically needed.",
            "Keep child's routine vaccinations current, avoid bottle-feeding flat on the back, and keep living spaces smoke-free.",
        ),
    ]

    for c in conditions:
        conn.execute(
            """
            INSERT INTO conditions (
                slug, name, department_slug, urgency, summary, causes,
                symptoms_json, red_flags_json, diagnosis_tests_json, treatment, prevention
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                c[0],
                c[1],
                c[2],
                c[3],
                c[4],
                c[5],
                json.dumps(c[6]),
                json.dumps(c[7]),
                json.dumps(c[8]),
                c[9],
                c[10],
            ),
        )

    lab_packages = [
        (
            "Complete Master Health Checkup",
            "Preventive Wellness",
            2499,
            12,
            1,
            "Fast for 10–12 hours (water allowed). Morning sample collection recommended between 7:00 AM and 10:00 AM.",
            ["Complete Blood Count (CBC)", "Lipid Profile", "HbA1c & Fasting Glucose", "Liver Function Test (LFT)", "Kidney Function Test (KFT)", "Thyroid Profile (TSH, T3, T4)", "Vitamin D & B12", "Resting 12-Lead ECG"],
        ),
        (
            "Comprehensive Cardiac Risk Panel",
            "Heart Care",
            1899,
            8,
            1,
            "10-hour overnight fast required. Avoid heavy exercise or caffeine 12 hours before ECG.",
            ["Lipid Profile with ApoB", "hs-CRP Inflammation Marker", "HbA1c", "12-Lead ECG", "2D Echocardiography Screening"],
        ),
        (
            "Diabetes & Metabolic Care Package",
            "Chronic Care",
            1199,
            6,
            1,
            "Give fasting blood sample first, then post-meal sample 2 hours after breakfast.",
            ["Fasting & Post-Prandial Glucose", "HbA1c", "Urine Microalbumin", "Serum Creatinine & Electrolytes", "Lipid Profile"],
        ),
        (
            "Fever & Infection Diagnostic Panel",
            "Acute Care",
            1399,
            4,
            0,
            "No fasting needed. Inform lab technician of any antibiotics or fever medications taken in last 48 hours.",
            ["Complete Blood Count (CBC)", "CRP", "Dengue NS1 & IgM", "Malaria Antigen", "Typhoid Test", "Urine Routine"],
        ),
    ]
    for pkg in lab_packages:
        conn.execute(
            """
            INSERT INTO lab_packages (name, category, price, turnaround_hours, fasting_required, preparation_notes, included_tests_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (pkg[0], pkg[1], pkg[2], pkg[3], pkg[4], pkg[5], json.dumps(pkg[6])),
        )

    # Demo Patient Account
    conn.execute(
        """
        INSERT INTO patients (
            full_name, email, password_hash, phone, date_of_birth, gender,
            blood_group, allergies, chronic_conditions, emergency_contact
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "Aarav Sharma",
            "patient@carepulse.org",
            generate_password_hash("Patient@123"),
            "+91 98201 44510",
            "1991-05-14",
            "Male",
            "O+",
            "Penicillin (mild skin rash), Dust mites",
            "Mild Borderline Hypertension",
            "Priya Sharma (+91 98201 44511 - Spouse)",
        ),
    )
    patient_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    # Sample appointments for demo patient
    conn.executemany(
        """
        INSERT INTO appointments (patient_id, patient_name, patient_email, patient_phone, doctor_id, appointment_date, time_slot, visit_type, reason, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (patient_id, "Aarav Sharma", "patient@carepulse.org", "+91 98201 44510", 1, "2026-12-03", "10:30 AM", "In-Person", "Quarterly blood pressure & lipid review", "Confirmed"),
            (patient_id, "Aarav Sharma", "patient@carepulse.org", "+91 98201 44510", 2, "2026-10-18", "04:00 PM", "Telehealth", "Annual preventive blood test follow-up", "Completed"),
        ],
    )

    # Sample lab reports
    reports = [
        (
            patient_id,
            "CP-LAB-2026-8841",
            "Complete Blood & Metabolic Panel",
            "Dr. Arjun Kulkarni",
            "2026-11-12",
            "Attention Needed",
            "Fasting glucose and triglycerides are slightly elevated. Repeat HbA1c in 3 months and continue 30-min daily brisk walks.",
            [
                {"parameter": "Hemoglobin", "value": "14.6 g/dL", "range": "13.5 - 17.5 g/dL", "status": "Normal"},
                {"parameter": "Fasting Blood Glucose", "value": "108 mg/dL", "range": "70 - 99 mg/dL", "status": "Borderline"},
                {"parameter": "HbA1c", "value": "5.8 %", "range": "< 5.7 %", "status": "Borderline"},
                {"parameter": "Total Cholesterol", "value": "188 mg/dL", "range": "< 200 mg/dL", "status": "Normal"},
                {"parameter": "Triglycerides", "value": "168 mg/dL", "range": "< 150 mg/dL", "status": "High"},
                {"parameter": "Vitamin D (25-OH)", "value": "24 ng/mL", "range": "30 - 100 ng/mL", "status": "Low"},
            ],
        ),
        (
            patient_id,
            "CP-LAB-2026-7410",
            "Cardiac ECG & Kidney Function Check",
            "Dr. Meera Nair",
            "2026-10-18",
            "Normal",
            "Normal sinus rhythm on ECG. Kidney filtration and electrolytes are completely within healthy limits.",
            [
                {"parameter": "Resting Heart Rate", "value": "74 bpm", "range": "60 - 100 bpm", "status": "Normal"},
                {"parameter": "Serum Creatinine", "value": "0.94 mg/dL", "range": "0.7 - 1.3 mg/dL", "status": "Normal"},
                {"parameter": "Serum Potassium", "value": "4.3 mEq/L", "range": "3.5 - 5.1 mEq/L", "status": "Normal"},
                {"parameter": "TSH (Thyroid)", "value": "2.1 mIU/L", "range": "0.4 - 4.5 mIU/L", "status": "Normal"},
            ],
        ),
    ]
    for rep in reports:
        conn.execute(
            """
            INSERT INTO lab_reports (patient_id, report_code, test_name, ordered_by, report_date, overall_status, summary_notes, metrics_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (rep[0], rep[1], rep[2], rep[3], rep[4], rep[5], rep[6], json.dumps(rep[7])),
        )

    # Sample prescriptions
    conn.executemany(
        """
        INSERT INTO prescriptions (patient_id, medication_name, dosage, frequency, duration, prescribed_by, prescribed_date, instructions, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (patient_id, "Telmisartan", "40 mg", "Once daily (Morning)", "90 days", "Dr. Meera Nair", "2026-10-18", "Take at the same time each morning; monitor BP twice weekly.", "Active"),
            (patient_id, "Cholecalciferol (Vitamin D3)", "60,000 IU", "Once weekly", "8 weeks", "Dr. Arjun Kulkarni", "2026-11-12", "Take after a main meal for better absorption.", "Active"),
            (patient_id, "Cetirizine", "10 mg", "As needed at bedtime", "14 days", "Dr. Sofia Rahman", "2026-09-05", "Use only during seasonal dust allergy flare-ups.", "Completed"),
        ],
    )

    # Sample vitals logs
    conn.executemany(
        """
        INSERT INTO vitals_logs (patient_id, recorded_at, systolic, diastolic, heart_rate, blood_sugar, spo2, weight_kg, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (patient_id, "2026-11-24 08:15", 126, 82, 72, 102, 98, 74.5, "Morning resting reading before breakfast"),
            (patient_id, "2026-11-18 08:30", 130, 84, 76, 106, 98, 75.0, "After light walk"),
            (patient_id, "2026-11-10 09:00", 134, 86, 78, 110, 99, 75.4, "Baseline clinic check"),
        ],
    )
