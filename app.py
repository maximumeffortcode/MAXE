# app.py — MAXE MVP (Streamlit Cloud)
# - MAXE image states: IDLE / THINKING / ESCALATION
# - CSS animation (Gold idle / White thinking / Red escalation)
# - Typed text reply (in-place typewriter)
# - Escalation trigger + email-only coach notification
#
# Folder structure expected:
#   app.py
#   requirements.txt
#   maxe_assets/
#       maxe_idle.png
#       maxe_thinking_a.png
#       maxe_thinking_b.png
#       maxe_escalation.png

import os
import re
import time
import smtplib
import base64
from pathlib import Path
from email.message import EmailMessage
from typing import List, Optional, Dict, Any

import streamlit as st


# ----------------------------
# ASSETS
# ----------------------------
ASSET_IDLE = "maxe_assets/maxe_idle.png"
ASSET_THINKING_A = "maxe_assets/maxe_thinking_a.png"   # You can keep both; we’ll default to A.
ASSET_THINKING_B = "maxe_assets/maxe_thinking_b.png"
ASSET_ESCALATION = "maxe_assets/maxe_escalation.png"


# ----------------------------
# SECRETS / ENV helper
# ----------------------------
def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    if hasattr(st, "secrets") and key in st.secrets:
        return str(st.secrets[key])
    return os.getenv(key, default)


# ----------------------------
# EMAIL (Email-only MVP)
# ----------------------------
def send_coach_email(subject: str, body: str, reasons: List[str]) -> None:
    to_email = get_secret("COACH_EMAIL")
    smtp_host = get_secret("SMTP_HOST")
    smtp_port = int(get_secret("SMTP_PORT", "587"))
    smtp_user = get_secret("SMTP_USER")
    smtp_pass = get_secret("SMTP_PASS")
    smtp_from = get_secret("SMTP_FROM", smtp_user)

    missing = [k for k, v in {
        "COACH_EMAIL": to_email,
        "SMTP_HOST": smtp_host,
        "SMTP_USER": smtp_user,
        "SMTP_PASS": smtp_pass,
        "SMTP_FROM": smtp_from,
    }.items() if not v]

    if missing:
        raise RuntimeError(f"Missing email config keys: {', '.join(missing)}")

    msg = EmailMessage()
    msg["From"] = smtp_from
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body + f"\n\nEscalation reasons: {', '.join(reasons)}")

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)


# ----------------------------
# ESCALATION (MVP)
# ----------------------------
def _contains_any(text: str, patterns: List[str]) -> bool:
    return any(re.search(p, text, flags=re.IGNORECASE) for p in patterns)

def check_escalation(user_msg: str) -> tuple[bool, List[str]]:
    t = user_msg.strip()
    reasons: List[str] = []

    medical_red_flags = [
        r"\bchest pain\b|\bchest pressure\b",
        r"\bfaint(ed|ing)?\b|\bpassed out\b|\bblack(ed)? out\b",
        r"\b(can't|cannot) breathe\b|\bsevere shortness of breath\b|\bshort(ness)? of breath\b",
        r"\bnumb(ness)?\b|\btingl(e|ing)\b|\bweak(ness)?\b|\bface droop\b|\bconfus(ed|ion)\b",
        r"\bpalpitation(s)?\b|\birregular heartbeat\b|\bheart flutter\b",
        r"\baorta\b|\baneurysm\b",
        r"\bblood pressure\b.*\b(high|spike|spiking)\b",
    ]

    injury_red_flags = [
        r"\bsharp pain\b",
        r"\bheard a pop\b|\bpop(ped)?\b.*\bpain\b",
        r"\bswelling\b|\bbruis(e|ing)\b",
        r"\b(can't|cannot) bear weight\b|\bcan't walk\b",
        r"\bshoot(ing)? pain\b|\bpain down (my|the) (arm|leg)\b",
        r"\bunstable\b|\bgiving out\b|\blocks up\b",
    ]

    requires_coach = [
        r"\bmax out\b|\b1rm\b|\bPR\b",
        r"\bchange (my|the) program\b|\bmodify (my|the) program\b",
        r"\bskip (this|the) week\b|\bdeload\b.*\bnow\b",
        r"\bwhat did you mean\b|\bwhat do you want me to do\b",
    ]

    if _contains_any(t, medical_red_flags):
        reasons.append("medical_red_flag")
    if _contains_any(t, injury_red_flags):
        reasons.append("injury_red_flag")
    if _contains_any(t, requires_coach):
        reasons.append("requires_coach_judgment")

    return (len(reasons) > 0, reasons)


# ----------------------------
# Typed reply (typewriter)
# ----------------------------
def typewriter_in_chat(chat_placeholder, text: str, speed: float = 0.02, pre_delay: float = 0.35) -> None:
    with chat_placeholder:
        with st.chat_message("assistant"):
            bubble = st.empty()
            bubble.markdown("…")
            time.sleep(pre_delay)

            typed = ""
            for ch in text:
                typed += ch
                bubble.markdown(typed)
                time.sleep(speed)


# ----------------------------
# Placeholder MAXE reply (replace later with AI / rules)
# ----------------------------
def maxe_reply_for(user_msg: str) -> str:
    return (
        "Acknowledged.\n\n"
        "If you need a substitution, tell me:\n"
        "- what exercise you’re replacing\n"
        "- available equipment\n"
        "- what feels limited (pain vs tightness vs fatigue)\n\n"
        "I will preserve the intent and keep risk low."
    )

def maxe_escalation_reply() -> str:
    return (
        "Coach notified.\n\n"
        "Stop the session if symptoms worsen.\n"
        "If you have chest pain, fainting, or severe shortness of breath, seek urgent medical care."
    )


# ----------------------------
# CSS Animation (Gold idle / White thinking / Red escalation)
# ----------------------------
st.set_page_config(page_title="MAXE", layout="wide")

st.markdown("""
<style>
.maxe-container{
  display:flex;
  justify-content:center;
  align-items:center;
}

.maxe-img{
  width:100%;
  max-width:420px;
  border-radius: 10px;
}

/* IDLE: gold glow + slow breathe */
.maxe-idle{
  animation: maxe-breathe 4.8s ease-in-out infinite;
  filter: drop-shadow(0 0 8px rgba(212, 175, 55, 0.45));
}

/* THINKING: white glow + faster pulse */
.maxe-thinking{
  animation: maxe-pulse 1.15s ease-in-out infinite;
  filter: drop-shadow(0 0 14px rgba(245, 242, 234, 0.85));
}

/* ESCALATION: red glow + urgent pulse */
.maxe-escalation{
  animation: maxe-pulse 0.85s ease-in-out infinite;
  filter: drop-shadow(0 0 16px rgba(210, 45, 45, 0.95));
}

@keyframes maxe-breathe{
  0%{ transform:scale(1.0); }
  50%{ transform:scale(1.015); }
  100%{ transform:scale(1.0); }
}

@keyframes maxe-pulse{
  0%{ transform:scale(1.0); opacity:0.93; }
  50%{ transform:scale(1.02); opacity:1.0; }
  100%{ transform:scale(1.0); opacity:0.93; }
}
</style>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def img_to_data_uri(path: str) -> str:
    data = Path(path).read_bytes()
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def render_maxe_animated(state: str) -> None:
    """
    CSS-animated render. Uses base64 data URI so it works on Streamlit Cloud.
    We use one static image per state; the 'animation' is CSS-based.
    """
    if state == "THINKING":
        # Use one thinking image; the white glow CSS will signal thinking.
        img_path = ASSET_THINKING_A
        css_class = "maxe-thinking"
    elif state == "ESCALATION":
        img_path = ASSET_ESCALATION
        css_class = "maxe-escalation"
    else:
        img_path = ASSET_IDLE
        css_class = "maxe-idle"

    uri = img_to_data_uri(img_path)
    st.markdown(
        f"""
        <div class="maxe-container">
          <img class="maxe-img {css_class}" src="{uri}" />
        </div>
        """,
        unsafe_allow_html=True
    )


# ----------------------------
# Streamlit App
# ----------------------------

# Session state init
if "messages" not in st.session_state:
    st.session_state.messages: List[Dict[str, Any]] = []

left, right = st.columns([1, 2], gap="large")

# Default state
if "maxe_state" not in st.session_state:
    st.session_state.maxe_state = "IDLE"

with left:
    st.markdown("## MAXE")
    status_slot = st.empty()
    maxe_slot = st.empty()  # <-- IMPORTANT: use empty, not container

with right:
    st.markdown("## Chat")

    # Render message history
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    user_msg = st.chat_input("Message MAXE…")

# Process message if provided
if user_msg:
    # Save user message
    st.session_state.messages.append({"role": "user", "content": user_msg})

    # Set THINKING immediately so user sees the animation/glow
    st.session_state.maxe_state = "THINKING"
    with left:
        status_slot_caption(f"Status: {st.session_state.maxe_state}")
        with maxe_slot.container():
            render_maxe_animated(st.session_state.maxe_state)
    time.sleep(0.8)

    # Escalation check
    escalate, reasons = check_escalation(user_msg)

    if escalate:
        st.session_state.maxe_state = "ESCALATION"

        with right:
            st.error("COACH NOTIFIED")

        # Notify coach (best effort)
        try:
            send_coach_email(
                subject="MAXE Escalation Alert",
                body=f"User message:\n\n{user_msg}\n\nContext:\n- App: MAXE\n- State: ESCALATION\n",
                reasons=reasons
            )
        except Exception as e:
            with right:
                st.warning(f"Coach email not sent (check Streamlit secrets): {e}")

        # Reply (typed)
        reply = maxe_escalation_reply()
        chat_placeholder = st.empty()
        typewriter_in_chat(chat_placeholder, reply, speed=0.02, pre_delay=0.35)
        st.session_state.messages.append({"role": "assistant", "content": reply})

    else:
        # Normal response
        st.session_state.maxe_state = "RESPONDING"
        reply = maxe_reply_for(user_msg)

        chat_placeholder = st.empty()
        typewriter_in_chat(chat_placeholder, reply, speed=0.02, pre_delay=0.35)
        st.session_state.messages.append({"role": "assistant", "content": reply})

        st.session_state.maxe_state = "IDLE"

# ✅ Render MAXE ONCE per run (always)
with left:
    status_slot.caption(f"Status: {st.session_state.maxe_state}")
    with maxe_slot.container():
        render_maxe_animated(st.session_state.maxe_state)
