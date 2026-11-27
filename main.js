/* Interactive scripts for CarePulse Hospital */
document.addEventListener("DOMContentLoaded", () => {
  // Mobile navbar toggle
  const menuBtn = document.getElementById("menuToggle");
  const navLinks = document.getElementById("navLinks");
  if (menuBtn && navLinks) {
    menuBtn.addEventListener("click", () => {
      navLinks.classList.toggle("open");
    });
  }

  // Symptom Checker submission
  const symptomForm = document.getElementById("symptomCheckerForm");
  if (symptomForm) {
    const checkboxes = symptomForm.querySelectorAll('input[name="symptoms"]');
    checkboxes.forEach((cb) => {
      cb.addEventListener("change", () => {
        cb.closest(".symptom-chip")?.classList.toggle("selected", cb.checked);
      });
    });

    symptomForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const selected = Array.from(checkboxes)
        .filter((cb) => cb.checked)
        .map((cb) => cb.value);
      const redFlag = document.getElementById("severeFlag")?.checked || false;
      const resultsEl = document.getElementById("symptomResults");

      if (selected.length === 0 && !redFlag) {
        resultsEl.innerHTML =
          '<div class="alert alert-warning">Please select at least one symptom to evaluate.</div>';
        return;
      }

      resultsEl.innerHTML = '<div class="card"><p>Analyzing symptoms...</p></div>';
      try {
        const res = await fetch("/api/symptom-check", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            symptoms: selected,
            severe_chest_or_breathing: redFlag,
          }),
        });
        const data = await res.json();
        if (!res.ok) {
          resultsEl.innerHTML = `<div class="alert alert-danger">${data.error || "Unable to evaluate symptoms."}</div>`;
          return;
        }

        const badgeClass =
          data.triage_level === "Emergency"
            ? "alert-danger"
            : data.triage_level === "Urgent"
              ? "alert-warning"
              : "alert-info";

        let html = `
          <div class="alert ${badgeClass}">
            <strong>Triage Priority: ${data.triage_level}</strong><br />
            ${data.triage_advice}
          </div>
        `;

        if (!data.matches || data.matches.length === 0) {
          html += `
            <div class="card">
              <h3>No exact match in quick guide</h3>
              <p class="card-muted">We recommend booking a General Medicine consultation for a full clinical assessment.</p>
              <a class="btn btn-primary" href="/appointments/book">Book General Consultation</a>
            </div>
          `;
        } else {
          html += '<div class="grid-2">';
          data.matches.forEach((m) => {
            html += `
              <div class="card">
                <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:8px;">
                  <span class="badge">${m.department_name}</span>
                  <span class="badge ${m.urgency.includes("Emergency") ? "badge-danger" : ""}">${m.match_count} symptom match</span>
                </div>
                <h3>${m.name}</h3>
                <p class="card-muted">${m.summary}</p>
                <p><strong>Matched:</strong> ${m.matched_symptoms.join(", ")}</p>
                <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:12px;">
                  <a class="btn btn-outline btn-sm" href="/health-library/${m.slug}">Read Full Health Guide</a>
                  <a class="btn btn-primary btn-sm" href="/doctors?dept=${m.department_slug}">Find Specialist</a>
                </div>
              </div>
            `;
          });
          html += "</div>";
        }
        resultsEl.innerHTML = html;
      } catch (_err) {
        resultsEl.innerHTML =
          '<div class="alert alert-danger">Network error while checking symptoms. Please try again.</div>';
      }
    });
  }

  // Health Calculators
  const bmiForm = document.getElementById("bmiForm");
  if (bmiForm) {
    bmiForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const weight = parseFloat(document.getElementById("bmiWeight").value);
      const heightCm = parseFloat(document.getElementById("bmiHeight").value);
      const out = document.getElementById("bmiResult");
      if (!weight || !heightCm || heightCm <= 0) return;

      const heightM = heightCm / 100;
      const bmi = weight / (heightM * heightM);
      let category = "Healthy Weight";
      let cls = "alert-success";
      if (bmi < 18.5) {
        category = "Underweight";
        cls = "alert-warning";
      } else if (bmi >= 25 && bmi < 30) {
        category = "Overweight";
        cls = "alert-warning";
      } else if (bmi >= 30) {
        category = "Obesity Range";
        cls = "alert-danger";
      }
      const idealMin = (18.5 * heightM * heightM).toFixed(1);
      const idealMax = (24.9 * heightM * heightM).toFixed(1);
      out.innerHTML = `
        <div class="alert ${cls}">
          <strong>BMI: ${bmi.toFixed(1)} kg/m² (${category})</strong><br/>
          Healthy weight range for ${heightCm} cm: ${idealMin} kg – ${idealMax} kg
        </div>
      `;
    });
  }

  const bpForm = document.getElementById("bpForm");
  if (bpForm) {
    bpForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const sys = parseInt(document.getElementById("bpSys").value, 10);
      const dia = parseInt(document.getElementById("bpDia").value, 10);
      const out = document.getElementById("bpResult");
      if (!sys || !dia) return;

      let label = "Normal";
      let advice = "Maintain healthy sleep, hydration, and regular movement.";
      let cls = "alert-success";
      if (sys >= 180 || dia >= 120) {
        label = "Hypertensive Crisis — Seek Emergency Care";
        advice = "Wait 5 minutes and recheck. If still >=180/120 or you have chest pain/headache, visit ER immediately.";
        cls = "alert-danger";
      } else if (sys >= 140 || dia >= 90) {
        label = "Stage 2 Hypertension";
        advice = "Book a Cardiology or General Medicine visit to review medication and lifestyle care.";
        cls = "alert-danger";
      } else if (sys >= 130 || dia >= 80) {
        label = "Stage 1 Hypertension";
        advice = "Track morning/evening readings for 7 days and consult your doctor.";
        cls = "alert-warning";
      } else if (sys >= 120 && dia < 80) {
        label = "Elevated Blood Pressure";
        advice = "Reduce dietary sodium and aim for 150 minutes/week of aerobic exercise.";
        cls = "alert-warning";
      }
      out.innerHTML = `<div class="alert ${cls}"><strong>${sys}/${dia} mmHg — ${label}</strong><br/>${advice}</div>`;
    });
  }

  const hrForm = document.getElementById("hrForm");
  if (hrForm) {
    hrForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const age = parseInt(document.getElementById("hrAge").value, 10);
      const out = document.getElementById("hrResult");
      if (!age || age < 5 || age > 110) return;
      const maxHr = 220 - age;
      const modLow = Math.round(maxHr * 0.5);
      const modHigh = Math.round(maxHr * 0.7);
      const vigHigh = Math.round(maxHr * 0.85);
      out.innerHTML = `
        <div class="alert alert-info">
          <strong>Estimated Max Heart Rate: ${maxHr} bpm</strong><br/>
          Moderate Exercise Zone (50–70%): <strong>${modLow} – ${modHigh} bpm</strong><br/>
          Vigorous Zone (70–85%): <strong>${modHigh} – ${vigHigh} bpm</strong>
        </div>
      `;
    });
  }

  const waterForm = document.getElementById("waterForm");
  if (waterForm) {
    waterForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const kg = parseFloat(document.getElementById("waterWeight").value);
      const mins = parseInt(document.getElementById("waterExercise").value || "0", 10);
      const out = document.getElementById("waterResult");
      if (!kg || kg <= 0) return;
      const liters = (kg * 0.033 + (mins / 30) * 0.35).toFixed(2);
      out.innerHTML = `
        <div class="alert alert-info">
          <strong>Recommended Daily Water Intake: ~${liters} Liters/day</strong><br/>
          Adjust upward in hot weather, fever, or high-altitude conditions.
        </div>
      `;
    });
  }
});
