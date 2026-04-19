/**
 * DiabetesGuard — Frontend Logic (script.js)
 * ─────────────────────────────────────────────────────────
 * Handles:
 *   1. Form submission → POST /predict (or /wearable for hybrid mode)
 *   2. Result display with animated score ring + probability bars
 *   3. Lifestyle simulation chart → POST /simulate
 *   4. Feature importance bars → GET /feature-importance
 *   5. BMI slider + segmented control helpers
 *   6. Wearable section toggle
 *   7. Step progress indicator highlight
 */

// ── API base URL ──────────────────────────────────────────
const API_BASE = "http://127.0.0.1:5000";

// ── Wearable toggle ───────────────────────────────────────
function toggleWearable() {
  const section = document.getElementById("wearableSection");
  section.classList.toggle("hidden");
}

// ── BMI slider ────────────────────────────────────────────
function updateBMI(val) {
  const v = parseFloat(val);
  const display = document.getElementById("bmiVal");
  display.textContent = v.toFixed(1);
  document.getElementById("bmiHidden").value = v;

  // Color the badge
  if      (v < 18.5) { display.style.background = "var(--green-muted)"; display.style.color = "var(--green)"; display.style.borderColor = "var(--green-border)"; }
  else if (v < 25)   { display.style.background = "var(--blue-muted)";  display.style.color = "var(--blue)";  display.style.borderColor = "var(--blue-border)"; }
  else if (v < 30)   { display.style.background = "var(--orange-muted)";display.style.color = "var(--orange)";display.style.borderColor = "var(--orange-border)"; }
  else               { display.style.background = "var(--red-muted)";   display.style.color = "var(--red)";   display.style.borderColor = "var(--red-border)"; }
}

// ── Segmented control (GenHlth) ───────────────────────────
function setSeg(fieldName, val, btn) {
  btn.closest(".seg-control").querySelectorAll(".seg-btn")
     .forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
  document.getElementById(fieldName + "Hidden").value = val;
}

// ── Collect form values ───────────────────────────────────
function collectFormData() {
  const form = document.getElementById("assessForm");
  const data = {};
  const formData = new FormData(form);
  for (const [key, val] of formData.entries()) {
    data[key] = parseFloat(val);
  }
  data["BMI"]     = parseFloat(document.getElementById("bmiHidden").value);
  data["GenHlth"] = parseFloat(document.getElementById("GenHlthHidden").value);
  return data;
}

// ── Collect wearable values ───────────────────────────────
function collectWearableData() {
  return {
    steps_per_day:   parseFloat(document.getElementById("w_steps").value)  || 0,
    avg_heart_rate:  parseFloat(document.getElementById("w_hr").value)     || 70,
    sleep_hours:     parseFloat(document.getElementById("w_sleep").value)  || 7,
    calories_burned: parseFloat(document.getElementById("w_cal").value)    || 0,
  };
}

// ── Main submit handler ───────────────────────────────────
async function submitForm(event) {
  event.preventDefault();

  const btn    = document.getElementById("submitBtn");
  const text   = document.getElementById("submitText");
  const loader = document.getElementById("submitLoader");

  text.classList.add("hidden");
  loader.classList.remove("hidden");
  btn.disabled = true;

  try {
    const useWearable = document.getElementById("wearableToggle").checked;
    const manualData  = collectFormData();
    let prediction;

    if (useWearable) {
      const wearableData = collectWearableData();
      const resp = await fetch(`${API_BASE}/wearable`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ wearable: wearableData, manual: manualData }),
      });
      prediction = await resp.json();
    } else {
      const resp = await fetch(`${API_BASE}/predict`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(manualData),
      });
      prediction = await resp.json();
    }

    if (prediction.error) throw new Error(prediction.error);

    displayResults(prediction);
    fetchSimulation(manualData);
    fetchFeatureImportance();

    document.getElementById("result").classList.remove("hidden");
    setTimeout(() => {
      document.getElementById("result").scrollIntoView({ behavior: "smooth" });
    }, 100);

  } catch (err) {
    alert(`Error: ${err.message}\n\nMake sure Flask is running:\n  python backend/app.py`);
    console.error(err);
  } finally {
    text.classList.remove("hidden");
    loader.classList.add("hidden");
    btn.disabled = false;
  }
}

// ── Display prediction results ────────────────────────────
function displayResults(data) {
  const score = data.risk_score;
  const cat   = data.risk_category;
  const probs = data.probabilities;

  // Score number
  document.getElementById("scoreNum").textContent = Math.round(score);

  // Category badge
  const catEl = document.getElementById("scoreCat");
  catEl.textContent = cat;
  catEl.className   = "score-cat";
  if (cat === "Low Risk")    catEl.classList.add("low");
  if (cat === "Medium Risk") catEl.classList.add("medium");
  if (cat === "High Risk")   catEl.classList.add("high");

  // SVG ring: circumference = 2π×80 ≈ 502
  const circ   = 502;
  const offset = circ - (score / 100) * circ;
  const circle = document.getElementById("scoreCircle");

  let ringColor = "#16a34a";
  if      (score >= 60) ringColor = "#dc2626";
  else if (score >= 30) ringColor = "#d97706";
  circle.style.stroke = ringColor;

  setTimeout(() => { circle.style.strokeDashoffset = offset; }, 200);

  // Probability bars
  setProbBar("pb0", "pt0", probs.no_diabetes);
  setProbBar("pb1", "pt1", probs.pre_diabetes);
  setProbBar("pb2", "pt2", probs.diabetes);

  // Advice banner
  const banner = document.getElementById("adviceBanner");
  banner.className = "advice-banner";

  if (cat === "Low Risk") {
    banner.classList.add("low");
    banner.innerHTML = `✅ <strong>Great news!</strong> Your lifestyle indicators suggest a LOW diabetes risk. Maintain your healthy habits and schedule regular health check-ups.`;
  } else if (cat === "Medium Risk") {
    banner.classList.add("medium");
    banner.innerHTML = `⚠️ <strong>Moderate Risk Detected.</strong> Some risk factors are present. The lifestyle improvement roadmap below can significantly reduce your score — small changes now prevent bigger issues later.`;
  } else {
    banner.classList.add("high");
    banner.innerHTML = `🚨 <strong>High Risk Detected.</strong> Several significant risk factors are identified. Please consult a qualified doctor and follow the personalised improvement plan shown below.`;
  }

  updateHeroDial(score);
}

// ── Helper: animate a probability bar ────────────────────
function setProbBar(barId, textId, pct) {
  setTimeout(() => {
    document.getElementById(barId).style.width  = pct + "%";
    document.getElementById(textId).textContent = pct.toFixed(1) + "%";
  }, 300);
}

// ── Fetch & display lifestyle simulation ─────────────────
async function fetchSimulation(manualData) {
  try {
    const resp = await fetch(`${API_BASE}/simulate`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(manualData),
    });
    const data = await resp.json();
    renderSimulation(data.stages);
  } catch (err) {
    document.getElementById("simChart").innerHTML =
      `<p style="color:var(--red);font-size:.8rem;padding:12px 0">Could not load simulation. Is Flask running?</p>`;
  }
}

function renderSimulation(stages) {
  const container = document.getElementById("simChart");
  container.innerHTML = "";

  stages.forEach((s, i) => {
    const colorClass = s.category.split(" ")[0].toLowerCase();

    const item = document.createElement("div");
    item.className = "sim-bar-item";
    item.innerHTML = `
      <div class="sim-bar-header">
        <span class="sim-stage-label">
          Stage ${s.stage}
          <span class="sim-cat-badge ${s.category.replace(/ /g, ".")}">${s.category}</span>
        </span>
        <span class="sim-score" style="color:${scoreColor(s.score)}">${s.score.toFixed(0)}</span>
      </div>
      <div class="sim-track">
        <div class="sim-fill ${colorClass}"
             style="width:0%; --delay:${i}"
             data-width="${s.score}%"></div>
      </div>
      <div style="font-size:.72rem;color:var(--ink-faint);margin-top:3px">${s.label}</div>
    `;
    container.appendChild(item);
  });

  setTimeout(() => {
    container.querySelectorAll(".sim-fill").forEach(el => {
      el.style.width = el.dataset.width;
    });
  }, 120);
}

// ── Fetch & display feature importance ───────────────────
async function fetchFeatureImportance() {
  try {
    const resp = await fetch(`${API_BASE}/feature-importance`);
    const data = await resp.json();
    renderFeatureImportance(data.features);
  } catch (err) {
    document.getElementById("featureImportance").innerHTML =
      `<p style="color:var(--red);font-size:.8rem;padding:12px 0">Could not load features. Is Flask running?</p>`;
  }
}

function renderFeatureImportance(features) {
  const container = document.getElementById("featureImportance");
  container.innerHTML = "";
  const maxImp = features[0].importance;

  features.slice(0, 7).forEach((f) => {
    const pct = (f.importance / maxImp) * 100;
    const item = document.createElement("div");
    item.className = "feat-item";
    item.innerHTML = `
      <div class="feat-name">
        <span>${friendlyName(f.name)}</span>
        <span>${(f.importance * 100).toFixed(2)}%</span>
      </div>
      <div class="feat-bar-track">
        <div class="feat-bar-fill" style="width:0%" data-width="${pct}%"></div>
      </div>
    `;
    container.appendChild(item);
  });

  setTimeout(() => {
    container.querySelectorAll(".feat-bar-fill").forEach(el => {
      el.style.width = el.dataset.width;
    });
  }, 120);
}

// ── Update hero dial ──────────────────────────────────────
function updateHeroDial(score) {
  const maxArc = 188;
  const offset = maxArc - (score / 100) * maxArc;
  const arc    = document.getElementById("dial-arc");
  if (arc) arc.style.strokeDashoffset = offset;

  const numEl = document.querySelector(".risk-dial text");
  if (numEl) numEl.textContent = Math.round(score);
}

// ── Reset form ────────────────────────────────────────────
function resetForm() {
  document.getElementById("result").classList.add("hidden");
  document.getElementById("home").scrollIntoView({ behavior: "smooth" });
  document.getElementById("scoreCircle").style.strokeDashoffset = 502;
}

// ── Helpers ───────────────────────────────────────────────
function scoreColor(score) {
  if (score >= 60) return "var(--red)";
  if (score >= 30) return "var(--orange)";
  return "var(--green)";
}

const FRIENDLY = {
  BMI: "BMI (Body Mass Index)", GenHlth: "General Health Rating",
  Age: "Age Group", HighBP: "High Blood Pressure",
  PhysHlth: "Physical Health Bad Days", PhysActivity: "Physical Activity",
  Income: "Income Level", DiffWalk: "Difficulty Walking",
  HighChol: "High Cholesterol", MentHlth: "Mental Health Bad Days",
  Smoker: "Smoking History", HeartDiseaseorAttack: "Heart Disease",
  Stroke: "Stroke History", Fruits: "Daily Fruit Intake",
  Veggies: "Daily Vegetable Intake", HvyAlcoholConsump: "Heavy Alcohol Use",
  AnyHealthcare: "Has Healthcare", NoDocbcCost: "Avoided Dr Due to Cost",
  Education: "Education Level", Sex: "Sex", CholCheck: "Cholesterol Check",
};
function friendlyName(key) { return FRIENDLY[key] || key; }

// ── Active nav link on scroll ─────────────────────────────
const sections = ["home", "assess", "result"];
window.addEventListener("scroll", () => {
  let current = "home";
  sections.forEach(id => {
    const el = document.getElementById(id);
    if (el && window.scrollY >= el.offsetTop - 80) current = id;
  });
  document.querySelectorAll(".nav-link").forEach(link => {
    link.classList.toggle("active", link.getAttribute("href") === `#${current}`);
  });
});

// ── Step progress highlight (visual only) ────────────────
function updateStepIndicator(activeStep) {
  document.querySelectorAll(".step-item").forEach(item => {
    const step = parseInt(item.dataset.step);
    item.classList.toggle("active", step === activeStep);
  });
}

// Observe form sections to update step indicator
if ("IntersectionObserver" in window) {
  const stepMap = { "section-1": 1, "section-2": 2, "section-3": 3, "section-4": 4 };
  const observer = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting && stepMap[e.target.id]) {
        updateStepIndicator(stepMap[e.target.id]);
      }
    });
  }, { threshold: 0.5 });

  Object.keys(stepMap).forEach(id => {
    const el = document.getElementById(id);
    if (el) observer.observe(el);
  });
}