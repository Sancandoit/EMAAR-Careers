import re, io
import hashlib
from io import BytesIO
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm

# ---------- Page config ----------
st.set_page_config(
    page_title="EMAAR | AI + Concierge Hiring",
    page_icon="assets/emaar-logo.png",
    layout="wide"
)

# === SESSION STATE FOR LOGGING & ANALYTICS ===
if "audit_log" not in st.session_state:
    st.session_state.audit_log = pd.DataFrame(
        columns=[
            "timestamp", "candidate_id", "candidate_name", "is_emirati",
            "role_title", "fit_score", "matched_criteria", "criteria_weights_json"
        ]
    )

# ---------- Brand CSS ----------
st.markdown("""
<style>
.block-container { padding-top: 3.0rem; }
h1, h2, h3 { color: #2B2B2B; }
hr.gold { border: 0; border-top: 2px solid #D4AF37; margin: 0.5rem 0 1rem 0; }
.stButton>button { background:#D4AF37; color:#2B2B2B; border:0; border-radius:12px; padding:0.5rem 1rem; }
.stButton>button:hover { filter:brightness(0.95); }
[data-testid="stMetric"] { background:#F2E8D5; border-radius:12px; padding:0.75rem; }
textarea, .stTextInput input { background:#FFFFFF !important; border-radius:10px !important; }
</style>
""", unsafe_allow_html=True)

# ---------- Robust logo + title without deprecated flag ----------
APP_DIR = Path(__file__).parent
LOGO_PATH = APP_DIR / "assets" / "emaar-logo.png"
LOGO_WIDTH = 180

col_logo, col_title = st.columns([1, 6], vertical_alignment="center")
with col_logo:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=LOGO_WIDTH)
    else:
        st.caption("Logo not found at assets/emaar-logo.png")

with col_title:
    st.markdown("## AI + Concierge Hiring")
    st.caption("Hospitality-grade candidate experience with transparent, auditable scoring.")

st.markdown("<hr class='gold'/>", unsafe_allow_html=True)

# ---------- Helpers ----------
def clean_text(x: str) -> str:
    return re.sub(r"\s+", " ", x or "").strip().lower()

def read_uploaded_file(uploaded_file) -> str:
    if uploaded_file is None:
        return ""
    data = uploaded_file.read()
    name = (uploaded_file.name or "").lower()
    # Try PDF first
    if name.endswith(".pdf"):
        try:
            from pdfminer.high_level import extract_text
            return extract_text(io.BytesIO(data)) or ""
        except Exception:
            pass
    # Fallback to UTF-8 decode
    try:
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""

def read_local_file(path: Path) -> str:
    if not path.exists():
        return ""
    if path.suffix.lower() == ".pdf":
        try:
            from pdfminer.high_level import extract_text
            with open(path, "rb") as f:
                return extract_text(f) or ""
        except Exception:
            return ""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

def keyword_score(text, criteria):
    text_l = clean_text(text)
    total = 0.0
    details = []
    for c in criteria:
        weight = float(c.get("weight", 0))
        kws = c.get("keywords", [])
        matched = [k for k in kws if k.lower() in text_l]
        part_score = weight if matched else 0.0
        total += part_score
        details.append({"criterion": c["name"], "weight": weight, "matched": matched})
    return round(total, 2), details

def explainability(details):
    lines = []
    for d in details:
        if d["matched"]:
            lines.append(f"• {d['criterion']}: matched {', '.join(d['matched'])} (+{d['weight']})")
        else:
            lines.append(f"• {d['criterion']}: no match (+0)")
    return "\n".join(lines)

def concierge_script(candidate_name, role_title, top_strengths):
    opener = f"Hello {candidate_name}, this is the EMAAR Talent Concierge. Thanks for your interest in the {role_title} role."
    body = "We focus on service excellence and multicultural teamwork. Your background stood out for: " + ", ".join(top_strengths) + "."
    close = "I’d love to walk you through the role expectations and answer your questions. Would you prefer a quick 15-minute call or a 25-minute deep-dive?"
    return f"{opener}\n\n{body}\n\n{close}"

def mock_timeslots(n=5):
    base = datetime.now() + timedelta(hours=2)
    return [(base + timedelta(minutes=30*i)).strftime("%a %d %b, %I:%M %p") for i in range(n)]

def bias_check_panel():
    st.markdown("**Ethics & Audit Checklist**")
    st.checkbox("Job criteria are skills-based and role-relevant only.", value=True)
    st.checkbox("Explainability available to recruiters and candidates.", value=True)
    st.checkbox("Human-in-the-loop for final decision.", value=True)
    st.checkbox("No protected attributes used in scoring.", value=True)
    st.checkbox("Candidate experience SLAs set for response and feedback.", value=True)

# === PDF CONFIRMATION GENERATOR (Candidate View) ===
def build_confirmation_pdf(candidate_name: str, slot: str, role_title: str) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    # Header band
    c.setFillColorRGB(0.96, 0.94, 0.88)  # light beige band
    c.rect(0, height - 2.2*cm, width, 2.2*cm, fill=1, stroke=0)
    # Title
    c.setFillColorRGB(0.17, 0.17, 0.17)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(2*cm, height - 1.5*cm, "EMAAR Talent Concierge — Call Confirmation")

    y = height - 3.2*cm
    c.setFont("Helvetica", 11)
    c.drawString(2*cm, y, f"Candidate: {candidate_name}")
    y -= 0.8*cm
    c.drawString(2*cm, y, f"Role: {role_title}")
    y -= 0.8*cm
    c.drawString(2*cm, y, f"Scheduled Slot: {slot}")
    y -= 1.2*cm

    c.setFont("Helvetica", 10)
    text = (
        "Thank you for choosing a concierge call. This brief conversation will outline the role, "
        "highlight your strengths, and answer any questions you have. You will receive the next steps after the call."
    )
    c.drawString(2*cm, y, text)
    y -= 1.2*cm

    # Footer
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(2*cm, 1.5*cm, "This confirmation is for demonstration purposes. © EMAAR (demo)")

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()

# ---------- Utility: compute + render + log ----------
def render_candidate_result(candidate_name: str, role_title: str, criteria_input, text: str, is_emirati=False):
    total, details = keyword_score(text, criteria_input)

    # Display
    st.metric("Fit Score", f"{total} / 100")
    st.markdown("**Explainability**")
    st.code(explainability(details))

    # Personalized concierge script (top 2 strengths)
    top_two = [d["criterion"] for d in details if d["matched"]][:2] or ["service mindset"]
    st.markdown("**Concierge Call Script**")
    st.code(concierge_script(candidate_name, role_title, top_two))

    # Audit log
    matched = []
    for d in details:
        if d["matched"]:
            matched.append(f"{d['criterion']} ({', '.join(d['matched'])})")
    criteria_weights = {c["name"]: c["weight"] for c in criteria_input}
    candidate_id = hashlib.md5(f"{candidate_name}{datetime.utcnow().isoformat()}".encode()).hexdigest()[:8]
    new_row = {
        "timestamp": datetime.utcnow().isoformat(timespec="seconds"),
        "candidate_id": candidate_id,
        "candidate_name": candidate_name,
        "is_emirati": bool(is_emirati),
        "role_title": role_title,
        "fit_score": float(total),
        "matched_criteria": "; ".join(matched) if matched else "None",
        "criteria_weights_json": str(criteria_weights),
    }
    st.session_state.audit_log = pd.concat(
        [st.session_state.audit_log, pd.DataFrame([new_row])],
        ignore_index=True
    )
    return total

# ---------- Sidebar ----------
st.sidebar.title("Navigation")
mode = st.sidebar.radio("Choose a view", ["Recruiter View", "Candidate View"])

# ---------- Recruiter View ----------
if mode == "Recruiter View":
    st.subheader("Recruiter Console")
    st.write("Define the job, set weighted criteria, upload resumes, and generate an explainable fit score plus a concierge call script.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Job Description**")
        role_title = st.text_input("Role Title", value="Guest Experience Supervisor")
        jd_text = st.text_area(
            "Paste Job Description",
            height=200,
            value=("We seek a Guest Experience Supervisor to lead service teams in a luxury retail/hospitality setting. "
                   "Must demonstrate customer empathy, Arabic or multilingual skills, stakeholder management, and basic analytics.")
        )
        st.caption("Tip: try the sample at sample_data/sample_jd.txt")

    with col2:
        st.markdown("**Weighted Criteria**")
        criteria_input = [
            {"name": "Customer Empathy", "weight": st.number_input("Customer Empathy", 0.0, 100.0, 30.0, 1.0),
             "keywords": ["customer empathy", "guest experience", "service excellence", "hospitality"]},
            {"name": "Arabic / Multilingual", "weight": st.number_input("Arabic / Multilingual", 0.0, 100.0, 20.0, 1.0),
             "keywords": ["arabic", "bilingual", "multilingual"]},
            {"name": "Retail/Hospitality Ops", "weight": st.number_input("Retail/Hospitality Ops", 0.0, 100.0, 20.0, 1.0),
             "keywords": ["retail operations", "hospitality operations", "pos", "front office"]},
            {"name": "Stakeholder Management", "weight": st.number_input("Stakeholder Mgmt", 0.0, 100.0, 15.0, 1.0),
             "keywords": ["stakeholder management", "cross-functional", "vendor management"]},
            {"name": "Analytics & Reporting", "weight": st.number_input("Analytics & Reporting", 0.0, 100.0, 15.0, 1.0),
             "keywords": ["excel", "analytics", "reporting", "dashboard", "kpi"]}
        ]
        st.caption(f"Total weight: {sum([c['weight'] for c in criteria_input]):.0f}")

    st.markdown("<hr class='gold'/>", unsafe_allow_html=True)
    st.markdown("**Upload a Candidate Resume for Scoring**")
    up = st.file_uploader("Upload TXT or PDF", type=["txt", "pdf"])
    candidate_name = st.text_input("Candidate Name", value="Aisha Khan")

    # === 2) Emiratisation flag ===
    is_emirati = st.checkbox("Candidate is a UAE National (Emirati)", value=False)
    if is_emirati:
        st.info("This candidate counts toward Emiratisation targets for skilled roles.")

    # === Primary scoring path (manual upload) ===
    if st.button("Compute Fit Score"):
        text = read_uploaded_file(up)
        if not text:
            st.warning("Please upload a resume.")
        else:
            render_candidate_result(candidate_name, role_title, criteria_input, text, is_emirati=is_emirati)

    # === Demo: Aisha vs Armaan (built-in samples) ===
    st.markdown("### Quick Demo: Score our sample resumes")
    demo_col1, demo_col2 = st.columns(2)
    with demo_col1:
        if st.button("Demo: Score Aisha (Hospitality fit)"):
            aisha_path = APP_DIR / "sample_data" / "Aisha_Khan_Resume.pdf"
            aisha_text = read_local_file(aisha_path)
            if not aisha_text:
                st.error("Aisha_Khan_Resume.pdf not found in sample_data/.")
            else:
                render_candidate_result("Aisha Khan", role_title, criteria_input, aisha_text, is_emirati=True)

    with demo_col2:
        if st.button("Demo: Score Armaan (Non-fit)"):
            armaan_path = APP_DIR / "sample_data" / "Armaan_Satish_Resume.pdf"
            armaan_text = read_local_file(armaan_path)
            if not armaan_text:
                st.error("Armaan_Satish_Resume.pdf not found in sample_data/.")
            else:
                render_candidate_result("Armaan Satish", role_title, criteria_input, armaan_text, is_emirati=False)

    st.markdown("### Ethics & Audit")
    bias_check_panel()

    # 3) Audit log viewer + CSV download
    with st.expander("Bias & Audit Tracker (view log)"):
        if len(st.session_state.audit_log) == 0:
            st.caption("No entries yet.")
        else:
            st.dataframe(st.session_state.audit_log, use_container_width=True)
            csv_bytes = st.session_state.audit_log.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download CSV log",
                data=csv_bytes,
                file_name="emaar_hiring_audit_log.csv",
                mime="text/csv"
            )

    # 6) Recruiter analytics
    st.markdown("### Recruiter Analytics")
    log = st.session_state.audit_log.copy()
    if len(log) == 0:
        st.caption("No analytics yet. Score a few candidates first.")
    else:
        # Buckets for scores
        bins = [0, 30, 60, 100]
        labels = ["0–30%", "30–60%", "60–100%"]
        log["score_bucket"] = pd.cut(log["fit_score"], bins=bins, labels=labels, include_lowest=True)

        colA, colB, colC = st.columns(3)
        with colA:
            st.metric("Total candidates", len(log))
        with colB:
            st.metric("Emirati candidates", int(log["is_emirati"].sum()))
        with colC:
            pct_emirati = 100 * log["is_emirati"].mean() if len(log) else 0
            st.metric("Emirati share", f"{pct_emirati:.0f}%")

        st.caption("Score distribution")
        dist = log["score_bucket"].value_counts().reindex(labels, fill_value=0)
        st.bar_chart(dist)

        st.caption("Average score by Emiratisation flag")
        avg_by_flag = log.groupby("is_emirati")["fit_score"].mean().rename({False: "Non-Emirati", True: "Emirati"})
        st.bar_chart(avg_by_flag)

# ----------------------------
# Candidate View
# ----------------------------
else:
    st.subheader("Candidate Experience")
    st.write("Welcome to the EMAAR Talent Concierge. We blend efficiency with a world-class human experience.")

    col1, col2 = st.columns(2)
    with col1:
        your_name = st.text_input("Your Name", value="Aisha Khan")
        resume = st.file_uploader("Upload resume", type=["txt", "pdf"], key="cand_up")
        note = st.text_area("Why are you excited about this role?")
        st.caption("Tip: try the sample at sample_data/sample_resume.txt")

    with col2:
        st.markdown("**Concierge Scheduling**")
        slots = mock_timeslots()
        slot = st.selectbox("Choose a call slot", slots)
        st.write("• Warm 15–25 minute conversation")
        st.write("• Clarity on next steps")
        st.write("• Your questions answered")

    if st.button("Submit"):
        if not your_name or not resume:
            st.warning("Please enter your name and upload a resume.")
        else:
            st.success(f"Thank you, {your_name}! Your EMAAR Talent Concierge call is booked for {slot}.")
            st.info("You’ll receive a confirmation with a brief call agenda.")

            # 5) Generate confirmation PDF and offer download
            pdf_bytes = build_confirmation_pdf(your_name, slot, role_title="Guest Experience Supervisor")
            st.download_button(
                "Download confirmation PDF",
                data=pdf_bytes,
                file_name=f"{your_name.replace(' ', '_')}_Concierge_Confirmation.pdf",
                mime="application/pdf"
            )
