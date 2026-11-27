"""CarePulse Hospital & Patient Health Portal — Flask Application."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import date, datetime
from functools import wraps
from pathlib import Path
from typing import Any, Callable

from flask import (
    Flask,
    abort,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from db import DEFAULT_DB_PATH, get_connection, init_and_seed

TIME_SLOTS = [
    "09:00 AM",
    "09:30 AM",
    "10:30 AM",
    "11:30 AM",
    "02:00 PM",
    "03:00 PM",
    "04:00 PM",
    "05:30 PM",
]


def _decode_condition(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    data["symptoms"] = json.loads(data.pop("symptoms_json"))
    data["red_flags"] = json.loads(data.pop("red_flags_json"))
    data["diagnosis_tests"] = json.loads(data.pop("diagnosis_tests_json"))
    return data


def _decode_package(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    data["included_tests"] = json.loads(data.pop("included_tests_json"))
    return data


def _decode_report(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    data["metrics"] = json.loads(data.pop("metrics_json"))
    return data


def login_required(view: Callable[..., Any]) -> Callable[..., Any]:
    """Redirect unauthenticated visitors to the patient sign-in page."""

    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        if g.patient is None:
            flash("Please sign in to access your Patient Health Portal.", "warning")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def create_app(db_path: Path | str | None = None, test_config: dict[str, Any] | None = None) -> Flask:
    """Create and configure the Flask hospital application."""
    app = Flask(__name__)
    resolved_db = Path(db_path) if db_path else DEFAULT_DB_PATH
    app.config.update(
        SECRET_KEY=os.environ.get("CAREPULSE_SECRET_KEY", "dev-carepulse-hospital-secret-key"),
        DATABASE_PATH=str(resolved_db),
    )
    if test_config:
        app.config.update(test_config)

    init_and_seed(app.config["DATABASE_PATH"])

    def get_db() -> sqlite3.Connection:
        if "db" not in g:
            g.db = get_connection(app.config["DATABASE_PATH"])
        return g.db

    @app.teardown_appcontext
    def close_db(_exc: BaseException | None) -> None:
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.before_request
    def load_logged_in_patient() -> None:
        patient_id = session.get("patient_id")
        if patient_id is None:
            g.patient = None
        else:
            row = get_db().execute(
                "SELECT * FROM patients WHERE id = ?", (patient_id,)
            ).fetchone()
            g.patient = dict(row) if row else None

    @app.context_processor
    def inject_globals() -> dict[str, Any]:
        return {
            "current_patient": g.get("patient"),
            "current_year": datetime.now().year,
            "hospital_hotline": "108 / +1 (800) 555-0199",
        }

    @app.route("/")
    def index() -> str:
        db = get_db()
        departments = db.execute(
            "SELECT * FROM departments ORDER BY is_emergency DESC, name ASC LIMIT 6"
        ).fetchall()
        featured_conditions = [
            _decode_condition(r)
            for r in db.execute(
                """
                SELECT c.*, d.name AS department_name
                FROM conditions c
                JOIN departments d ON c.department_slug = d.slug
                ORDER BY c.id ASC LIMIT 6
                """
            ).fetchall()
        ]
        packages = [
            _decode_package(r)
            for r in db.execute("SELECT * FROM lab_packages ORDER BY id ASC LIMIT 3").fetchall()
        ]
        doctor_count = db.execute("SELECT COUNT(*) FROM doctors").fetchone()[0]
        condition_count = db.execute("SELECT COUNT(*) FROM conditions").fetchone()[0]
        return render_template(
            "index.html",
            departments=departments,
            featured_conditions=featured_conditions,
            packages=packages,
            doctor_count=doctor_count,
            condition_count=condition_count,
        )

    @app.route("/health-library")
    def health_library() -> str:
        db = get_db()
        q = request.args.get("q", "").strip()
        dept = request.args.get("dept", "").strip()
        letter = request.args.get("letter", "").strip().upper()

        query = """
            SELECT c.*, d.name AS department_name
            FROM conditions c
            JOIN departments d ON c.department_slug = d.slug
            WHERE 1=1
        """
        params: list[Any] = []
        if q:
            like = f"%{q}%"
            query += " AND (c.name LIKE ? OR c.summary LIKE ? OR c.symptoms_json LIKE ? OR c.causes LIKE ?)"
            params.extend([like, like, like, like])
        if dept:
            query += " AND c.department_slug = ?"
            params.append(dept)
        if letter and len(letter) == 1 and letter.isalpha():
            query += " AND UPPER(c.name) LIKE ?"
            params.append(f"{letter}%")

        query += " ORDER BY c.name ASC"
        conditions = [_decode_condition(r) for r in db.execute(query, params).fetchall()]
        departments = db.execute("SELECT slug, name FROM departments ORDER BY name ASC").fetchall()
        all_letters = sorted(
            {
                r["name"][0].upper()
                for r in db.execute("SELECT name FROM conditions").fetchall()
                if r["name"]
            }
        )
        return render_template(
            "health_library.html",
            conditions=conditions,
            departments=departments,
            all_letters=all_letters,
            q=q,
            selected_dept=dept,
            selected_letter=letter,
        )

    @app.route("/health-library/<slug>")
    def condition_detail(slug: str) -> str:
        db = get_db()
        row = db.execute(
            """
            SELECT c.*, d.name AS department_name, d.floor_location, d.phone_ext
            FROM conditions c
            JOIN departments d ON c.department_slug = d.slug
            WHERE c.slug = ?
            """,
            (slug,),
        ).fetchone()
        if row is None:
            abort(404)
        condition = _decode_condition(row)
        doctors = db.execute(
            "SELECT * FROM doctors WHERE department_slug = ? ORDER BY experience_years DESC",
            (condition["department_slug"],),
        ).fetchall()
        return render_template(
            "condition_detail.html",
            condition=condition,
            doctors=doctors,
        )

    @app.route("/symptom-checker")
    def symptom_checker() -> str:
        db = get_db()
        rows = db.execute("SELECT symptoms_json FROM conditions").fetchall()
        symptom_set: set[str] = set()
        for row in rows:
            for item in json.loads(row["symptoms_json"]):
                symptom_set.add(item)
        return render_template("symptom_checker.html", symptoms=sorted(symptom_set))

    @app.route("/api/symptom-check", methods=["POST"])
    def api_symptom_check() -> Any:
        payload = request.get_json(silent=True) or {}
        selected = [str(s).strip().lower() for s in payload.get("symptoms", []) if str(s).strip()]
        has_red_flag = bool(payload.get("severe_chest_or_breathing", False))

        if not selected and not has_red_flag:
            return jsonify({"error": "Please select at least one symptom."}), 400

        db = get_db()
        rows = db.execute(
            """
            SELECT c.*, d.name AS department_name
            FROM conditions c
            JOIN departments d ON c.department_slug = d.slug
            """
        ).fetchall()

        matches: list[dict[str, Any]] = []
        for row in rows:
            cond = _decode_condition(row)
            cond_symptoms = [s.lower() for s in cond["symptoms"]]
            matched = [s for s in cond["symptoms"] if s.lower() in selected]
            if matched:
                score = round((len(matched) / max(len(cond_symptoms), 1)) * 100)
                matches.append(
                    {
                        "slug": cond["slug"],
                        "name": cond["name"],
                        "department_slug": cond["department_slug"],
                        "department_name": cond["department_name"],
                        "urgency": cond["urgency"],
                        "summary": cond["summary"],
                        "matched_symptoms": matched,
                        "match_count": len(matched),
                        "match_percent": score,
                        "red_flags": cond["red_flags"],
                    }
                )

        matches.sort(key=lambda item: (item["match_count"], item["match_percent"]), reverse=True)

        emergency_keywords = {"chest pain", "chest tightness", "shortness of breath"}
        urgent_keywords = {"fever", "wheezing", "blurred vision", "dizziness"}
        if has_red_flag or (
            any(k in selected for k in emergency_keywords)
            and ("chest pain" in selected or "shortness of breath" in selected)
        ):
            triage_level = "Emergency"
            triage_advice = (
                "Your selected symptoms include potential warning signs. Please visit the "
                "24/7 Emergency Department immediately or call 108 — do not drive yourself."
            )
        elif any(k in selected for k in urgent_keywords) or len(selected) >= 4:
            triage_level = "Urgent"
            triage_advice = (
                "Schedule a same-day clinic or telehealth consultation with the recommended "
                "specialist below. Seek ER care if symptoms rapidly worsen."
            )
        else:
            triage_level = "Routine"
            triage_advice = (
                "Symptoms appear mild or chronic. Book a routine outpatient appointment and "
                "review self-care steps in our Health Library."
            )

        return jsonify(
            {
                "triage_level": triage_level,
                "triage_advice": triage_advice,
                "matches": matches[:5],
            }
        )

    @app.route("/api/conditions")
    def api_conditions() -> Any:
        q = request.args.get("q", "").strip()
        db = get_db()
        if q:
            like = f"%{q}%"
            rows = db.execute(
                """
                SELECT slug, name, department_slug, urgency, summary
                FROM conditions
                WHERE name LIKE ? OR summary LIKE ? OR symptoms_json LIKE ?
                ORDER BY name ASC LIMIT 12
                """,
                (like, like, like),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT slug, name, department_slug, urgency, summary FROM conditions ORDER BY name ASC"
            ).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.route("/doctors")
    def doctors() -> str:
        db = get_db()
        dept = request.args.get("dept", "").strip()
        q = request.args.get("q", "").strip()
        query = """
            SELECT doc.*, d.name AS department_name, d.floor_location
            FROM doctors doc
            JOIN departments d ON doc.department_slug = d.slug
            WHERE 1=1
        """
        params: list[Any] = []
        if dept:
            query += " AND doc.department_slug = ?"
            params.append(dept)
        if q:
            like = f"%{q}%"
            query += " AND (doc.name LIKE ? OR doc.specialty LIKE ? OR d.name LIKE ?)"
            params.extend([like, like, like])
        query += " ORDER BY doc.name ASC"
        doctor_rows = db.execute(query, params).fetchall()
        departments = db.execute("SELECT slug, name FROM departments ORDER BY name ASC").fetchall()
        return render_template(
            "doctors.html",
            doctors=doctor_rows,
            departments=departments,
            selected_dept=dept,
            q=q,
        )

    @app.route("/appointments/book", methods=["GET", "POST"])
    def book_appointment() -> Any:
        db = get_db()
        doctors = db.execute(
            """
            SELECT doc.*, d.name AS department_name
            FROM doctors doc
            JOIN departments d ON doc.department_slug = d.slug
            ORDER BY doc.name ASC
            """
        ).fetchall()
        selected_doctor_id = request.args.get("doctor_id", type=int)

        if request.method == "POST":
            patient_name = request.form.get("patient_name", "").strip()
            patient_email = request.form.get("patient_email", "").strip()
            patient_phone = request.form.get("patient_phone", "").strip()
            doctor_id = request.form.get("doctor_id", type=int)
            appointment_date = request.form.get("appointment_date", "").strip()
            time_slot = request.form.get("time_slot", "").strip()
            visit_type = request.form.get("visit_type", "In-Person").strip()
            reason = request.form.get("reason", "").strip()

            errors: list[str] = []
            if not patient_name or not patient_email or not patient_phone:
                errors.append("Please enter patient name, email, and phone number.")
            if not doctor_id:
                errors.append("Please select a doctor.")
            if not appointment_date or not time_slot:
                errors.append("Please choose an appointment date and time slot.")
            if not reason:
                errors.append("Please describe your health concern or reason for visit.")

            doc_exists = (
                db.execute("SELECT name FROM doctors WHERE id = ?", (doctor_id,)).fetchone()
                if doctor_id
                else None
            )
            if doctor_id and doc_exists is None:
                errors.append("Selected doctor was not found.")

            if errors:
                for err in errors:
                    flash(err, "danger")
            else:
                patient_id = g.patient["id"] if g.patient else None
                db.execute(
                    """
                    INSERT INTO appointments (
                        patient_id, patient_name, patient_email, patient_phone,
                        doctor_id, appointment_date, time_slot, visit_type, reason, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Confirmed')
                    """,
                    (
                        patient_id,
                        patient_name,
                        patient_email,
                        patient_phone,
                        doctor_id,
                        appointment_date,
                        time_slot,
                        visit_type,
                        reason,
                    ),
                )
                db.commit()
                flash(
                    f"Appointment confirmed with {doc_exists['name']} on {appointment_date} at {time_slot}.",
                    "success",
                )
                if g.patient:
                    return redirect(url_for("portal"))
                return redirect(url_for("doctors"))

        return render_template(
            "book_appointment.html",
            doctors=doctors,
            selected_doctor_id=selected_doctor_id,
            time_slots=TIME_SLOTS,
            min_date=date.today().isoformat(),
        )

    @app.route("/appointments/<int:appt_id>/cancel", methods=["POST"])
    @login_required
    def cancel_appointment(appt_id: int) -> Any:
        db = get_db()
        row = db.execute(
            "SELECT * FROM appointments WHERE id = ? AND patient_id = ?",
            (appt_id, g.patient["id"]),
        ).fetchone()
        if row is None:
            abort(404)
        db.execute(
            "UPDATE appointments SET status = 'Cancelled' WHERE id = ?",
            (appt_id,),
        )
        db.commit()
        flash("Appointment has been cancelled.", "info")
        return redirect(url_for("portal"))

    @app.route("/departments")
    def departments() -> str:
        db = get_db()
        dept_rows = db.execute(
            "SELECT * FROM departments ORDER BY is_emergency DESC, name ASC"
        ).fetchall()
        packages = [
            _decode_package(r)
            for r in db.execute("SELECT * FROM lab_packages ORDER BY id ASC").fetchall()
        ]
        return render_template(
            "departments.html",
            departments=dept_rows,
            packages=packages,
        )

    @app.route("/health-tools")
    def health_tools() -> str:
        return render_template("health_tools.html")

    @app.route("/login", methods=["GET", "POST"])
    def login() -> Any:
        if g.patient is not None:
            return redirect(url_for("portal"))

        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            db = get_db()
            user = db.execute(
                "SELECT * FROM patients WHERE LOWER(email) = ?", (email,)
            ).fetchone()
            if user is None or not check_password_hash(user["password_hash"], password):
                flash("Invalid email or password. Please try again.", "danger")
            else:
                session.clear()
                session["patient_id"] = user["id"]
                # Determine role based on email domain (simple demo)
                email_domain = user["email"].split("@")[-1]
                if email_domain == "admin.carepulse.com":
                    session["role"] = "admin"
                elif email_domain == "doctor.carepulse.com":
                    session["role"] = "doctor"
                elif email_domain == "pharmacy.carepulse.com":
                    session["role"] = "pharmacy"
                else:
                    session["role"] = "patient"
                # Simple admin flag – keep for backward compatibility
                session["is_admin"] = (user["email"] == "admin@carepulse.com")
                flash(f"Welcome back, {user['full_name']}.", "success")
                next_url = request.args.get("next")
                return redirect(next_url or url_for("portal"))

        return render_template("login.html")

    @app.route("/register", methods=["GET", "POST"])
    def register() -> Any:
        if g.patient is not None:
            return redirect(url_for("portal"))

        if request.method == "POST":
            full_name = request.form.get("full_name", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            phone = request.form.get("phone", "").strip()
            dob = request.form.get("date_of_birth", "").strip()
            gender = request.form.get("gender", "Prefer not to say").strip()
            blood_group = request.form.get("blood_group", "Unknown").strip()
            allergies = request.form.get("allergies", "").strip() or "None reported"
            emergency_contact = request.form.get("emergency_contact", "").strip()

            db = get_db()
            if not full_name or not email or len(password) < 6 or not phone or not dob or not emergency_contact:
                flash("Please fill in all required fields (password minimum 6 characters).", "danger")
            elif db.execute("SELECT id FROM patients WHERE LOWER(email) = ?", (email,)).fetchone():
                flash("An account with this email already exists. Please sign in.", "warning")
            else:
                cur = db.execute(
                    """
                    INSERT INTO patients (
                        full_name, email, password_hash, phone, date_of_birth, gender,
                        blood_group, allergies, chronic_conditions, emergency_contact
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'None reported', ?)
                    """,
                    (
                        full_name,
                        email,
                        generate_password_hash(password),
                        phone,
                        dob,
                        gender,
                        blood_group,
                        allergies,
                        emergency_contact,
                    ),
                )
                db.commit()
                session.clear()
                session["patient_id"] = cur.lastrowid
                flash("Your patient health account is ready!", "success")
                return redirect(url_for("portal"))

        return render_template("register.html")

    @app.route("/logout")
    def logout() -> Any:
        session.clear()
        flash("You have been signed out securely.", "info")
        return redirect(url_for("index"))

    @app.route("/portal")
    @login_required
    def portal() -> str:
        db = get_db()
        pid = g.patient["id"]
        appointments = db.execute(
            """
            SELECT a.*, d.name AS doctor_name, d.specialty, dep.name AS department_name
            FROM appointments a
            JOIN doctors d ON a.doctor_id = d.id
            JOIN departments dep ON d.department_slug = dep.slug
            WHERE a.patient_id = ?
            ORDER BY a.appointment_date DESC, a.id DESC
            """,
            (pid,),
        ).fetchall()
        reports = [
            _decode_report(r)
            for r in db.execute(
                "SELECT * FROM lab_reports WHERE patient_id = ? ORDER BY report_date DESC",
                (pid,),
            ).fetchall()
        ]
        prescriptions = db.execute(
            "SELECT * FROM prescriptions WHERE patient_id = ? ORDER BY prescribed_date DESC",
            (pid,),
        ).fetchall()
        vitals = db.execute(
            "SELECT * FROM vitals_logs WHERE patient_id = ? ORDER BY recorded_at DESC LIMIT 6",
            (pid,),
        ).fetchall()
        return render_template(
            "portal.html",
            appointments=appointments,
            reports=reports,
            prescriptions=prescriptions,
            vitals=vitals,
        )

    @app.route("/portal/vitals", methods=["POST"])
    @login_required
    def log_vitals() -> Any:
        try:
            systolic = int(request.form.get("systolic", 0))
            diastolic = int(request.form.get("diastolic", 0))
            heart_rate = int(request.form.get("heart_rate", 0))
            blood_sugar = int(request.form.get("blood_sugar", 0))
            spo2 = int(request.form.get("spo2", 0))
            weight_kg = float(request.form.get("weight_kg", 0))
        except ValueError:
            flash("Please enter valid numeric values for your vitals.", "danger")
            return redirect(url_for("portal"))

        notes = request.form.get("notes", "").strip()
        if not (50 <= systolic <= 260 and 30 <= diastolic <= 160 and 30 <= heart_rate <= 220 and 50 <= spo2 <= 100):
            flash("One or more vital readings are outside expected physiological ranges.", "danger")
            return redirect(url_for("portal"))

        db = get_db()
        db.execute(
            """
            INSERT INTO vitals_logs (patient_id, recorded_at, systolic, diastolic, heart_rate, blood_sugar, spo2, weight_kg, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                g.patient["id"],
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                systolic,
                diastolic,
                heart_rate,
                blood_sugar,
                spo2,
                weight_kg,
                notes,
            ),
        )
        db.commit()
        flash("New vitals reading saved to your health timeline.", "success")
        return redirect(url_for("portal"))

    @app.route("/portal/reports/<int:report_id>")
    @login_required
    def view_report(report_id: int) -> str:
        db = get_db()
        row = db.execute(
            "SELECT * FROM lab_reports WHERE id = ? AND patient_id = ?",
            (report_id, g.patient["id"]),
        ).fetchone()
        if row is None:
            abort(404)
        return render_template("report_detail.html", report=_decode_report(row))

    @app.route("/portal/prescriptions/<int:rx_id>/refill", methods=["POST"])
    @login_required
    def request_refill(rx_id: int) -> Any:
        db = get_db()
        row = db.execute(
            "SELECT * FROM prescriptions WHERE id = ? AND patient_id = ?",
            (rx_id, g.patient["id"]),
        ).fetchone()
        if row is None:
            abort(404)
        db.execute(
            "UPDATE prescriptions SET status = 'Refill Requested' WHERE id = ?",
            (rx_id,),
        )
        db.commit()
        flash(f"Refill requested for {row['medication_name']}. Pharmacy will notify you shortly.", "success")
        return redirect(url_for("portal"))

    @app.errorhandler(404)
    def not_found(_err: Any) -> tuple[str, int]:
        return render_template("404.html"), 404

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)

# ----- Role‑based portals -----

@app.route("/doctor")
@login_required
def doctor_portal() -> str:
    if session.get("role") != "doctor":
        abort(403)
    # In a real system you would look up the doctor record and related data.
    return render_template("doctor.html")

@app.route("/admin")
@login_required
def admin_portal() -> str:
    if session.get("role") != "admin":
        abort(403)
    return render_template("admin.html")

@app.route("/pharmacy")
@login_required
def pharmacy_portal() -> str:
    if session.get("role") != "pharmacy":
        abort(403)
    return render_template("pharmacy.html")
