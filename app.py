import os
import io
import base64
import time
import json
from dotenv import load_dotenv

import streamlit as st
import fitz

from google import genai
from gtts import gTTS
from audio_recorder_streamlit import audio_recorder
import speech_recognition as sr

# Load environment variables from .env file
load_dotenv()

# =========================================================
# 1. GEMINI API KEY SETUP (READ FROM ENV FILE)
# =========================================================

MY_GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")

client = None
_startup_error = None

if MY_GEMINI_KEY and len(MY_GEMINI_KEY.strip()) > 10 and "PASTE_YOUR" not in MY_GEMINI_KEY:
    try:
        client = genai.Client(api_key=MY_GEMINI_KEY.strip())
    except Exception as e:
        _startup_error = str(e)

st.set_page_config(
    page_title="SimuHire - AI Voice Recruiter Pro",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    * { font-family: 'Plus Jakarta Sans', sans-serif; }

    .stApp {
        background-color: #f8fafc !important;
        color: #0f172a !important;
    }

    section[data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e2e8f0 !important;
    }

    .header-card {
        background: linear-gradient(135deg, #1e3a8a 0%, #0f172a 100%);
        color: #ffffff;
        padding: 32px;
        border-radius: 22px;
        text-align: center;
        box-shadow: 0 14px 30px rgba(30, 58, 138, 0.18);
        margin-bottom: 26px;
        border: 1px solid #334155;
    }
    .header-title { font-size: 34px; font-weight: 800; margin: 0; color: #ffffff; letter-spacing: -0.5px; }
    .header-subtitle { font-size: 15px; color: #7dd3fc; margin-top: 8px; font-weight: 600; }

    .cv-summary-card {
        background: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
        color: #1e293b;
    }

    .q-card {
        background: #f8fbff;
        padding: 28px;
        border-radius: 18px;
        border-left: 6px solid #2563eb;
        box-shadow: 0 10px 25px rgba(37, 99, 235, 0.06);
        font-size: 21px;
        color: #0f172a;
        line-height: 1.65;
        font-weight: 600;
        margin-bottom: 20px;
        border-top: 1px solid #dbeafe;
        border-right: 1px solid #dbeafe;
        border-bottom: 1px solid #dbeafe;
    }

    .robot-container {
        text-align: center;
        background: #ffffff;
        padding: 18px;
        border-radius: 18px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.03);
        border: 1px solid #e2e8f0;
    }
    .robot-img { width: 100px; height: auto; border-radius: 12px; }
    .robot-badge {
        display: inline-block;
        background-color: #eff6ff;
        color: #1d4ed8;
        font-size: 12px;
        font-weight: 700;
        padding: 6px 14px;
        border-radius: 20px;
        margin-top: 8px;
        border: 1px solid #bfdbfe;
    }

    .timer-card {
        background: #ffffff;
        border: 2px solid #0284c7;
        padding: 12px;
        border-radius: 16px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(2, 132, 199, 0.08);
    }

    .metric-card-pro {
        background: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
    }
    .metric-title-pro { font-size: 12px; color: #64748b; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }
    .metric-value-pro { font-size: 34px; font-weight: 800; color: #2563eb; margin-top: 4px; }

    .badge-strength {
        background: #f0fdf4;
        color: #15803d;
        border: 1px solid #bbf7d0;
        padding: 12px 16px;
        border-radius: 12px;
        margin-bottom: 10px;
        font-size: 14px;
        font-weight: 600;
    }

    .badge-weakness {
        background: #fef2f2;
        color: #b91c1c;
        border: 1px solid #fecaca;
        padding: 12px 16px;
        border-radius: 12px;
        margin-bottom: 10px;
        font-size: 14px;
        font-weight: 600;
    }

    .stButton>button {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border-radius: 12px !important;
        padding: 14px 28px !important;
        border: none !important;
        box-shadow: 0 4px 15px rgba(37, 99, 235, 0.2) !important;
        width: 100%;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="header-card">
        <div class="header-title">🤖 SimuHire - AI Voice Recruiter Pro</div>
        <div class="header-subtitle">Intelligent HR Screening & Technical Assessment System</div>
    </div>
    """,
    unsafe_allow_html=True
)

# =========================================================
# 2. SIDEBAR CONTROL PANEL
# =========================================================

st.sidebar.title("📌 Recruiter Control Panel")

uploaded_file = st.sidebar.file_uploader("Upload Candidate CV (PDF)", type=["pdf"])

ALLOWED_ROLES = [
    "Software Engineer",
    "AI/ML Engineer",
    "Electronics Engineer",
    "Electrical Engineer",
    "Telecommunication Engineer"
]

selected_role = st.sidebar.selectbox(
    "Target Job Position",
    ["Select Position..."] + ALLOWED_ROLES + ["Other / Custom Role"]
)

job_position = ""
if selected_role == "Other / Custom Role":
    job_position = st.sidebar.text_input("Enter Custom Position Name", placeholder="e.g. Systems Engineer")
elif selected_role != "Select Position...":
    job_position = selected_role

if "ai_mode" not in st.session_state:
    st.session_state.ai_mode = "Checking Engine..."

if "last_ai_error" not in st.session_state:
    st.session_state.last_ai_error = _startup_error or ""

# Debug Info in Sidebar
st.sidebar.markdown(f"**⚡ AI Engine Status:**\n\n{st.session_state.ai_mode}")
if st.session_state.last_ai_error:
    with st.sidebar.expander("🔎 Last Gemini Error"):
        st.code(st.session_state.last_ai_error)

# =========================================================
# 3. LOCAL FALLBACK & ROLES SETUP
# =========================================================

LOCAL_QUESTIONS = {
    "software engineer": [
        "Explain Object-Oriented Programming principles with practical examples.",
        "What is the difference between an array and a linked list?",
        "Explain the difference between a stack and a queue.",
        "What is time complexity? Explain O(n) vs O(log n).",
        "How would you design a scalable web application for high traffic?"
    ],
    "ai/ml engineer": [
        "What is the difference between supervised and unsupervised learning?",
        "What is overfitting and how can you reduce it?",
        "Why do we split datasets into train, validation, and test sets?",
        "Explain precision, recall, and accuracy metrics.",
        "How would you deploy an end-to-end Machine Learning pipeline?"
    ],
    "electronics engineer": [
        "What is the operational difference between BJT and MOSFET transistors?",
        "Explain the concept and practical application of pulse-width modulation (PWM).",
        "What is the difference between analog and digital filters in signal processing?",
        "How do you design an embedded circuit to minimize power consumption?",
        "Explain the role and working principle of a micro-controller interrupt system."
    ],
    "electrical engineer": [
        "Explain the primary differences between Single-Phase and Three-Phase AC power systems.",
        "How does a transformer function, and what are the key causes of transformer power losses?",
        "What is the purpose of power factor correction in industrial electrical networks?",
        "Explain the working mechanism of a circuit breaker versus a standard electrical fuse.",
        "How do synchronous motors differ from induction motors in industrial applications?"
    ],
    "telecommunication engineer": [
        "Explain the basic principle of Orthogonal Frequency Division Multiplexing (OFDM) in wireless networks.",
        "What is the difference between circuit switching and packet switching networks?",
        "How does fiber optic communication achieve high data transmission speeds using total internal reflection?",
        "Explain the concept of handover (handoff) in cellular mobile networks.",
        "What are the main differences between time division multiple access (TDMA) and code division multiple access (CDMA)?"
    ]
}

def detect_role(job_position):
    job = job_position.lower().strip()
    if "software" in job: return "software engineer"
    if "ai" in job or "ml" in job or "machine" in job: return "ai/ml engineer"
    if "electronic" in job: return "electronics engineer"
    if "electrical" in job: return "electrical engineer"
    if "telecom" in job or "telecommunication" in job: return "telecommunication engineer"
    return None

def get_local_question(job_position, question_number):
    role = detect_role(job_position)
    if role and role in LOCAL_QUESTIONS:
        questions = LOCAL_QUESTIONS[role]
        index = (question_number - 1) % len(questions)
        return questions[index]
    return f"Can you explain a key technical project relevant to {job_position}?"

# =========================================================
# 4. GEMINI CALL ENGINE
# =========================================================

def call_ai(prompt, response_type="question", job_position="", question_number=1, candidate_name="Candidate"):
    if client is not None:
        models_to_try = [
            "gemini-2.5-flash",
            "gemini-1.5-flash"
        ]

        errors = []
        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                if response and response.text:
                    st.session_state.ai_mode = f"🟢 Gemini Active ({model_name})"
                    st.session_state.last_ai_error = ""
                    if response_type == "json":
                        clean_txt = response.text.strip()
                        if "```json" in clean_txt:
                            clean_txt = clean_txt.split("```json")[1].split("```")[0]
                        elif "```" in clean_txt:
                            clean_txt = clean_txt.split("```")[1].split("```")[0]
                        return json.loads(clean_txt.strip())
                    return response.text.strip()
            except Exception as e:
                errors.append(f"{model_name}: {e}")
                continue

        st.session_state.last_ai_error = "\n".join(errors)

    st.session_state.ai_mode = "🔴 Local Engine (Fallback Mode)"
    if response_type == "question":
        return get_local_question(job_position, question_number)
    if response_type == "json":
        return {
            "summary": "Candidate profile loaded successfully.",
            "skills": ["Technical Knowledge", "Problem Solving"],
            "experience": "Relevant background detected",
            "education": "Technical Degree",
            "candidate": candidate_name,
            "position": job_position,
            "overall_score": 40,
            "technical_score": 35,
            "voice_confidence": 50,
            "skill_match": 45,
            "problematic_ideas": ["Responses lack complete detail"],
            "strengths": ["Submitted basic interview responses"],
            "weaknesses": ["Voice transcript incomplete or answers lack depth"],
            "question_breakdown": [],
            "recommendation": "Reject",
            "strict_decision_reason": "Low response clarity and incomplete technical accuracy."
        }
    return "Response generated."

# =========================================================
# 5. AUDIO TTS & STT ENGINE
# =========================================================

def text_to_speech_autoplay(text, q_num=1):
    played_key = f"audio_played_{q_num}"
    if played_key not in st.session_state:
        try:
            tts = gTTS(text=text, lang="en")
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            b64 = base64.b64encode(fp.read()).decode()

            audio_html = f"""
            <audio id="player_{q_num}" autoplay style="display:none;">
                <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
            st.components.v1.html(audio_html, height=0)
            st.session_state[played_key] = True
        except Exception:
            pass

def transcribe_audio(audio_bytes):
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    try:
        audio_file = io.BytesIO(audio_bytes)
        with sr.AudioFile(audio_file) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.3)
            audio_data = recognizer.record(source)
        return recognizer.recognize_google(audio_data, language="en-US")
    except Exception:
        return ""

# =========================================================
# 6. MAIN INTERVIEW ENGINE
# =========================================================

ROBOT_AVATAR = "https://img.freepik.com/free-vector/cute-robot-holding-phone-hand-waving-vector-icon-illustration-robot-technology-icon-concept-isolated_138676-5080.jpg"

if uploaded_file is not None and job_position:
    matched_role = detect_role(job_position)

    if matched_role is None:
        st.markdown(
            """
            <div style="background: #ffffff; border: 2px solid #ef4444; border-radius: 16px; padding: 30px; text-align: center;">
                <h3 style="color: #dc2626; margin: 0;">🚫 Position Unavailable</h3>
                <p style="color: #475569; margin-top: 10px;">Automated screening is active for engineering domains only.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        try:
            pdf = fitz.open(stream=uploaded_file.read(), filetype="pdf")
            cv_text = "".join([page.get_text() for page in pdf])
            candidate_name = uploaded_file.name.replace(".pdf", "")
        except Exception:
            st.error("Error reading CV file.")
            st.stop()

        candidate_id = f"{uploaded_file.name}_{matched_role}"

        # SESSION STATE INITIALIZATION
        if "candidate_id" not in st.session_state or st.session_state.candidate_id != candidate_id:
            st.session_state.candidate_id = candidate_id
            st.session_state.current_q_num = 1
            st.session_state.interview_history = []
            st.session_state.cv_analysis = None
            st.session_state.final_eval = None
            for key in list(st.session_state.keys()):
                if key.startswith("question_") or key.startswith("audio_played_") or key.startswith("transcript_"):
                    del st.session_state[key]

        if "cv_analysis" not in st.session_state:
            st.session_state.cv_analysis = None

        if "final_eval" not in st.session_state:
            st.session_state.final_eval = None

        # DETAILED CV ANALYSIS SUMMARY
        if st.session_state.cv_analysis is None:
            with st.spinner("🤖 Extracting CV Information & Skills..."):
                cv_prompt = f"""
                Analyze candidate CV for position {job_position}:
                {cv_text[:2000]}

                Return strictly JSON format:
                {{
                    "summary": "<2 line professional summary>",
                    "skills": ["Skill 1", "Skill 2", "Skill 3", "Skill 4"],
                    "experience": "<Brief experience highlight>",
                    "education": "<Brief education highlight>"
                }}
                """
                st.session_state.cv_analysis = call_ai(
                    cv_prompt,
                    response_type="json",
                    job_position=job_position,
                    candidate_name=candidate_name
                )

        cv_info = st.session_state.cv_analysis or {}
        with st.expander("📄 Extracted CV Summary & Skill Profile", expanded=True):
            st.markdown(
                f"""
                <div class="cv-summary-card">
                    <h4 style="color:#2563eb; margin-top:0;">👤 {candidate_name}</h4>
                    <p style="color:#334155;"><b>Overview:</b> {cv_info.get('summary', 'N/A')}</p>
                    <p style="color:#334155;"><b>Key Experience:</b> {cv_info.get('experience', 'N/A')}</p>
                    <p style="color:#334155;"><b>Education:</b> {cv_info.get('education', 'N/A')}</p>
                    <p style="color:#334155;"><b>Extracted Skills:</b> {", ".join(cv_info.get('skills', [])) if cv_info.get('skills') else 'N/A'}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

        st.divider()

        if st.session_state.current_q_num <= 5:
            q_num = st.session_state.current_q_num

            question_key = f"question_{q_num}"
            if question_key not in st.session_state:
                with st.spinner(f"🤖 Gemini generating Question {q_num}..."):
                    prompt = (
                        f"You are a strict technical interviewer hiring for {job_position}. "
                        f"Ask 1 concise technical question for Question {q_num} of 5. "
                        f"CV Context: {cv_text[:1000]}. Ask directly without intro."
                    )
                    st.session_state[question_key] = call_ai(
                        prompt,
                        response_type="question",
                        job_position=job_position,
                        question_number=q_num
                    )

            current_question = st.session_state[question_key]

            # HEADER TOP ROW
            c_bot, c_info, c_timer = st.columns([1.5, 3.5, 2])

            with c_bot:
                st.markdown(
                    f"""
                    <div class="robot-container">
                        <img src="{ROBOT_AVATAR}" class="robot-img" alt="AI Bot">
                        <br><span class="robot-badge">AI Interviewer</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            with c_info:
                st.markdown(f"### 🎤 Question {q_num} of 5")
                st.progress(q_num / 5)

            # TIMER
            with c_timer:
                timer_html = f"""
                <div class="timer-card">
                    <span style="font-size: 11px; color: #64748b; font-weight: 700;">TIME REMAINING</span>
                    <div id="timer_{q_num}" style="font-size: 28px; font-weight: 800; color: #0284c7;">02:00</div>
                </div>
                <script>
                    var duration = 120;
                    var display = document.querySelector('#timer_{q_num}');
                    var timer = duration, minutes, seconds;
                    var interval = setInterval(function () {{
                        minutes = parseInt(timer / 60, 10);
                        seconds = parseInt(timer % 60, 10);
                        minutes = minutes < 10 ? "0" + minutes : minutes;
                        seconds = seconds < 10 ? "0" + seconds : seconds;
                        display.textContent = minutes + ":" + seconds;

                        if (--timer < 0) {{
                            clearInterval(interval);
                            display.textContent = "00:00";
                            var targetBtn = window.parent.document.querySelector('button[kind="primary"]');
                            if (targetBtn) {{ targetBtn.click(); }}
                        }}
                    }}, 1000);
                </script>
                """
                st.components.v1.html(timer_html, height=110)

            st.markdown(f"<div class='q-card'><b>🤖 Gemini ({job_position}):</b><br>{current_question}</div>", unsafe_allow_html=True)
            text_to_speech_autoplay(current_question, q_num=q_num)

            st.write("")
            st.markdown("##### 🎙️ Voice Record & Speech Answer")

            audio_data = audio_recorder(
                text="Click to Record Voice",
                recording_color="#ef4444",
                neutral_color="#2563eb",
                icon_name="microphone",
                icon_size="2x",
                key=f"recorder_{q_num}"
            )

            transcript_key = f"transcript_{q_num}"
            if transcript_key not in st.session_state:
                st.session_state[transcript_key] = ""

            if audio_data and not st.session_state[transcript_key]:
                with st.spinner("🎧 Transcribing response..."):
                    st.session_state[transcript_key] = transcribe_audio(audio_bytes=audio_data)

            user_ans = st.text_area(
                "Speech Transcript (Editable):",
                value=st.session_state[transcript_key],
                key=f"answer_box_{q_num}",
                height=110
            )

            if st.button(f"Submit Answer Q{q_num} ➡️", type="primary"):
                final_text = user_ans.strip() if user_ans.strip() else "[Skipped / No Answer Provided]"
                st.session_state.interview_history.append({
                    "question": current_question,
                    "answer": final_text
                })
                st.session_state.current_q_num += 1
                st.rerun()

        else:
            st.balloons()
            st.markdown("## 📊 Strict Assessment & Final Hiring Verdict")

            if st.session_state.final_eval is None:
                eval_prompt = f"""
                You are a very strict Hiring Manager evaluating candidate performance.
                Candidate Name: {candidate_name}
                Position: {job_position}
                CV Skills: {json.dumps(cv_info.get('skills', []))}
                Interview Transcript: {json.dumps(st.session_state.interview_history)}

                Detailed Instructions for Evaluation:
                1. Check each question one-by-one. Identify if the user skipped the question, provided incorrect answers, or gave incomplete responses.
                2. Explain explicitly where the candidate made mistakes or what technical details were missing.
                3. Calculate scores (0-100) based strictly on accurate answers.
                4. Recommendation must strictly be one of: "Strong Hire", "Conditional Hire", or "Reject".

                Return strictly JSON format:
                {{
                    "candidate": "{candidate_name}",
                    "position": "{job_position}",
                    "overall_score": <0-100>,
                    "technical_score": <0-100>,
                    "voice_confidence": <0-100>,
                    "skill_match": <0-100>,
                    "strengths": ["Strength 1", "Strength 2"],
                    "weaknesses": ["Weakness 1", "Weakness 2"],
                    "problematic_ideas": ["Red flag 1", "Skipped question issue"],
                    "question_breakdown": [
                        {{
                            "question": "<Question Text>",
                            "candidate_answer": "<Candidate Response>",
                            "status": "<Correct / Incomplete / Skipped / Incorrect>",
                            "feedback": "<Specific feedback on mistake or missing concepts>"
                        }}
                    ],
                    "recommendation": "<Strong Hire / Conditional Hire / Reject>",
                    "strict_decision_reason": "<Clear detailed justification explaining overall performance and mistakes>"
                }}
                """
                with st.spinner("📊 Gemini evaluating final scorecard..."):
                    st.session_state.final_eval = call_ai(
                        eval_prompt,
                        response_type="json",
                        job_position=job_position,
                        candidate_name=candidate_name
                    )

            res = st.session_state.final_eval or {}

            # DASHBOARD METRICS
            m1, m2, m3, m4 = st.columns(4)
            m1.markdown(f'<div class="metric-card-pro"><div class="metric-title-pro">Overall Rating</div><div class="metric-value-pro">{res.get("overall_score", 0)}%</div></div>', unsafe_allow_html=True)
            m2.markdown(f'<div class="metric-card-pro"><div class="metric-title-pro">Technical Score</div><div class="metric-value-pro">{res.get("technical_score", 0)}%</div></div>', unsafe_allow_html=True)
            m3.markdown(f'<div class="metric-card-pro"><div class="metric-title-pro">Voice & Communication</div><div class="metric-value-pro">{res.get("voice_confidence", 0)}%</div></div>', unsafe_allow_html=True)
            m4.markdown(f'<div class="metric-card-pro"><div class="metric-title-pro">Skill Relevance</div><div class="metric-value-pro">{res.get("skill_match", 0)}%</div></div>', unsafe_allow_html=True)

            st.write("")

            rec = res.get('recommendation', 'Reject')
            color_map = {"Strong Hire": "#16a34a", "Conditional Hire": "#d97706", "Reject": "#dc2626"}
            decision_color = color_map.get(rec, "#dc2626")

            st.markdown(
                f"""
                <div style="background:#ffffff; border-radius:20px; padding:28px; border:2px solid {decision_color}; box-shadow: 0 8px 25px rgba(0,0,0,0.05);">
                    <h3 style="margin:0; color:#0f172a;">👤 Candidate: <b>{res.get('candidate', candidate_name)}</b> | Position: <b>{res.get('position', job_position)}</b></h3>
                    <h2 style="margin-top:10px; color:{decision_color};">🎯 Decision Verdict: {rec}</h2>
                    <p style="color:#334155; font-size:15px;"><b>Reasoning:</b> {res.get('strict_decision_reason', 'Evaluation complete.')}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.write("")

            # QUESTION-BY-QUESTION FEEDBACK BREAKDOWN
            st.markdown("### 🔍 Question-by-Question Detailed Analysis")
            breakdown = res.get("question_breakdown", [])

            if breakdown:
                for idx, q_item in enumerate(breakdown, start=1):
                    status = q_item.get("status", "Evaluated")
                    status_color = "#16a34a" if status == "Correct" else "#d97706" if status == "Incomplete" else "#dc2626"

                    with st.expander(f"Question {idx}: {q_item.get('question', '')} — [{status}]", expanded=True):
                        st.write(f"**Candidate Answer:** {q_item.get('candidate_answer', 'N/A')}")
                        st.markdown(f"<span style='color:{status_color}; font-weight:bold;'>Feedback / Mistake:</span> {q_item.get('feedback', 'No detailed feedback provided.')}", unsafe_allow_html=True)
            else:
                for idx, item in enumerate(st.session_state.interview_history, start=1):
                    with st.expander(f"Question {idx}: {item['question']}", expanded=True):
                        st.write(f"**Answer:** {item['answer']}")

            st.write("")
            col_s, col_w, col_p = st.columns(3)

            with col_s:
                st.markdown("#### ✅ Strengths")
                for s in res.get("strengths", []):
                    st.markdown(f'<div class="badge-strength">✔ {s}</div>', unsafe_allow_html=True)

            with col_w:
                st.markdown("#### ⚠️ Weaknesses")
                for w in res.get("weaknesses", []):
                    st.markdown(f'<div class="badge-weakness">✖ {w}</div>', unsafe_allow_html=True)

            with col_p:
                st.markdown("#### 🚨 Problematic Ideas & Red Flags")
                for p in res.get("problematic_ideas", ["No critical issues detected"]):
                    st.markdown(f'<div class="badge-weakness" style="background: #fff1f2; color: #991b1b; border: 1px solid #fecdd3;">🚩 {p}</div>', unsafe_allow_html=True)

            st.write("")
            if st.button("🔄 Assessment Completed - Reset"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()

elif uploaded_file is not None:
    st.info("👈 Select a target job position from the sidebar.")
else:
    st.info("👈 Upload candidate CV to begin.")