import streamlit as st
import re
import io
from datetime import datetime, timedelta

st.set_page_config(page_title="EMAAR | AI + Concierge Hiring", page_icon="✨", layout="wide")

# Inside your app.layout

html.Div([
    html.Img(src='assets/emaar-logo.png', style={'height':'100px', 'width':'auto', 'marginBottom':'25px'}),
    # ... rest of your layout
])
# ----------------------------
# Helpers
# ----------------------------
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

def keyword_score(text, criteria):
    """
    criteria: list of dicts [{name, weight, keywords: [..]}]
    returns: total_score (0-100), details list
    """
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

# ----------------------------
# Sidebar
# ----------------------------
st.sidebar.title("EMAAR | AI + Concierge Hiring")
mode = st.sidebar.radio("Choose a view", ["Recruiter View", "Candidate View"])
st.sidebar.caption("A hospitality-grade candidate experience with transparent, auditable scoring.")

# ----------------------------
# Recruiter View
# ----------------------------
if mode == "Recruiter View":
    st.title("Recruiter Console")
    st.write("Define the job, set weighted criteria, upload resumes, and generate an explainable fit score plus a concierge call script.")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Job Description")
        role_title = st.text_input("Role Title", value="Guest Experience Supervisor")
        jd_text = st.text_area(
            "Paste Job Description",
            height=200,
            value=("We seek a Guest Experience Supervisor to lead service teams in a luxury retail/hospitality setting. "
                   "Must demonstrate customer empathy, Arabic or multilingual skills, stakeholder management, and basic analytics.")
        )
        st.caption("Tip: try the sample at sample_data/sample_jd.txt")

    with col2:
        st.subheader("Weighted Criteria")
        criteria_input = [
            {
                "name": "Customer Empathy",
                "weight": st.number_input("Customer Empathy (0-100)", 0.0, 100.0, 30.0, 1.0),
                "keywords": ["customer empathy", "guest experience", "service excellence", "hospitality"]
            },
            {
                "name": "Arabic / Multilingual",
                "weight": st.number_input("Arabic / Multilingual (0-100)", 0.0, 100.0, 20.0, 1.0),
                "keywords": ["arabic", "bilingual", "multilingual"]
            },
            {
                "name": "Retail/Hospitality Ops",
                "weight": st.number_input("Retail/Hospitality Ops (0-100)", 0.0, 100.0, 20.0, 1.0),
                "keywords": ["retail operations", "hospitality operations", "pos", "store operations", "front office", "front desk"]
            },
            {
                "name": "Stakeholder Management",
                "weight": st.number_input("Stakeholder Mgmt (0-100)", 0.0, 100.0, 15.0, 1.0),
                "keywords": ["stakeholder management", "cross-functional", "influencing", "vendor management"]
            },
            {
                "name": "Analytics & Reporting",
                "weight": st.number_input("Analytics (0-100)", 0.0, 100.0, 15.0, 1.0),
                "keywords": ["excel", "analytics", "reporting", "dashboard", "kpi"]
            }
        ]
        total_weight = sum([c["weight"] for c in criteria_input])
        st.caption(f"Total weight: {total_weight:.0f} (tip: aim near 100)")

    st.divider()
    st.subheader("Upload a Candidate Resume for Scoring")
    up = st.file_uploader("Upload TXT or PDF", type=["txt", "pdf"])
    candidate_name = st.text_input("Candidate Name", value="Samay Raina")

    if "last_score" not in st.session_state:
        st.session_state.last_score = None
        st.session_state.last_details = []
        st.session_state.last_script = ""

    colA, colB = st.columns([1,1])
    with colA:
        if st.button("Compute Fit Score"):
            text = read_uploaded_file(up)
            if not text:
                st.warning("Please upload a readable resume file.")
            else:
                total, details = keyword_score(text, criteria_input)
                st.session_state.last_score = total
                st.session_state.last_details = details
                top_strengths = [d["criterion"] for d in details if d["matched"]][:3] or ["service mindset"]
                st.session_state.last_script = concierge_script(candidate_name, role_title, top_strengths)

        if st.session_state.last_score is not None:
            st.metric("Fit Score", f"{st.session_state.last_score} / 100")
            st.markdown("**Explainability**")
            st.code(explainability(st.session_state.last_details))
            st.markdown("**Concierge Call Script (auto-generated)**")
            st.code(st.session_state.last_script)

    with colB:
        st.markdown("### Ethics & Audit")
        bias_check_panel()

    st.caption("This is a transparent, rules-based demo. In production, add secure storage, assessments, and interview scheduling integrations.")

# ----------------------------
# Candidate View
# ----------------------------
else:
    st.title("Candidate Experience")
    st.write("Welcome to the EMAAR Talent Concierge. We blend efficiency with a world-class human experience.")

    col1, col2 = st.columns(2)
    with col1:
        your_name = st.text_input("Your Name", value="Samay Raina")
        your_email = st.text_input("Email", value="samay@damac.com")
        resume = st.file_uploader("Upload your resume (TXT or PDF)", type=["txt", "pdf"], key="cand_up")
        note = st.text_area("Tell us briefly why you’re excited about this role")
        st.caption("Tip: try the sample at sample_data/sample_resume.txt")

    with col2:
        st.markdown("**Concierge Scheduling**")
        slots = mock_timeslots()
        slot = st.selectbox("Choose a call slot", slots)
        st.markdown("**What to expect**")
        st.write("• A warm, 15–25 minute conversation")
        st.write("• Clarity on next steps")
        st.write("• Your questions answered")

    if st.button("Submit"):
        if not your_name or not resume:
            st.warning("Please enter your name and upload a resume.")
        else:
            st.success(f"Thank you, {your_name}! Your EMAAR Talent Concierge call is booked for {slot}.")
            st.info("You’ll receive a confirmation with a brief call agenda. We look forward to meeting you.")
    st.caption("This demo keeps data local during the session for classroom use.")
