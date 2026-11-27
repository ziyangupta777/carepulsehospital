"""Automated tests for CarePulse Hospital & Patient Health Portal."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app import create_app


class CarePulseHospitalTests(unittest.TestCase):
    """End-to-end tests for public health guides, symptom checker, booking, and portal."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_hospital.db"
        self.app = create_app(db_path=self.db_path, test_config={"TESTING": True})
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_public_pages_render(self) -> None:
        for path in [
            "/",
            "/health-library",
            "/health-library/hypertension",
            "/symptom-checker",
            "/doctors",
            "/appointments/book",
            "/departments",
            "/health-tools",
            "/login",
            "/register",
        ]:
            res = self.client.get(path)
            self.assertEqual(res.status_code, 200, f"Failed on {path}")

    def test_health_library_filters(self) -> None:
        res = self.client.get("/health-library?q=Asthma")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Bronchial Asthma", res.data)

        res_letter = self.client.get("/health-library?letter=M")
        self.assertIn(b"Migraine Headache", res_letter.data)

        api_res = self.client.get("/api/conditions?q=Diabetes")
        self.assertEqual(api_res.status_code, 200)
        self.assertTrue(any(item["slug"] == "type-2-diabetes" for item in api_res.get_json()))

    def test_symptom_checker_api(self) -> None:
        res_empty = self.client.post("/api/symptom-check", json={"symptoms": []})
        self.assertEqual(res_empty.status_code, 400)

        res_emergency = self.client.post(
            "/api/symptom-check",
            json={"symptoms": ["Chest Pain", "Shortness of Breath"], "severe_chest_or_breathing": True},
        )
        self.assertEqual(res_emergency.status_code, 200)
        data = res_emergency.get_json()
        self.assertEqual(data["triage_level"], "Emergency")
        self.assertTrue(len(data["matches"]) > 0)

    def test_portal_requires_auth_and_demo_login_works(self) -> None:
        unauth = self.client.get("/portal")
        self.assertEqual(unauth.status_code, 302)

        login_res = self.client.post(
            "/login",
            data={"email": "patient@carepulse.org", "password": "Patient@123"},
            follow_redirects=True,
        )
        self.assertEqual(login_res.status_code, 200)
        self.assertIn(b"Aarav Sharma", login_res.data)
        self.assertIn(b"CP-LAB-2026-8841", login_res.data)
        self.assertIn(b"Telmisartan", login_res.data)

        report_res = self.client.get("/portal/reports/1")
        self.assertEqual(report_res.status_code, 200)
        self.assertIn(b"Hemoglobin", report_res.data)

    def test_register_book_appointment_and_log_vitals(self) -> None:
        reg_res = self.client.post(
            "/register",
            data={
                "full_name": "Neha Verma",
                "email": "neha@example.com",
                "password": "StrongPass123",
                "phone": "9876543210",
                "date_of_birth": "1995-03-20",
                "gender": "Female",
                "blood_group": "A+",
                "allergies": "None",
                "emergency_contact": "Raj Verma (9876543211)",
            },
            follow_redirects=True,
        )
        self.assertEqual(reg_res.status_code, 200)
        self.assertIn(b"Neha Verma", reg_res.data)

        book_res = self.client.post(
            "/appointments/book",
            data={
                "patient_name": "Neha Verma",
                "patient_email": "neha@example.com",
                "patient_phone": "9876543210",
                "doctor_id": "1",
                "appointment_date": "2026-12-15",
                "time_slot": "10:30 AM",
                "visit_type": "In-Person",
                "reason": "Annual cardiac wellness check",
            },
            follow_redirects=True,
        )
        self.assertEqual(book_res.status_code, 200)
        self.assertIn(b"Appointment confirmed", book_res.data)
        self.assertIn(b"2026-12-15", book_res.data)

        vitals_res = self.client.post(
            "/portal/vitals",
            data={
                "systolic": "118",
                "diastolic": "76",
                "heart_rate": "68",
                "blood_sugar": "92",
                "spo2": "99",
                "weight_kg": "60.5",
                "notes": "Morning check",
            },
            follow_redirects=True,
        )
        self.assertEqual(vitals_res.status_code, 200)
        self.assertIn(b"118/76 mmHg", vitals_res.data)

    def test_vercel_entrypoint_imports(self) -> None:
        from api.index import app as vercel_app

        client = vercel_app.test_client()
        res = client.get("/")
        self.assertEqual(res.status_code, 200)


if __name__ == "__main__":
    unittest.main()
