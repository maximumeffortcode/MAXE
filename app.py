# app.py — MAXE MVP (Streamlit Cloud)
# - MAXE image states: IDLE / THINKING / RESPONDING / ESCALATION
# - CSS animation (Gold idle / White thinking / Red escalation)
# - Typed text reply (in-place typewriter)
# - Escalation trigger + email-only coach notification
# - Two-phase "pending" flow so THINKING is visible before responding (reliable in Streamlit)
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
ASSET_THINKING_A = "maxe_assets/maxe_thinking_a.png"
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


# Typewriter 


def typewriter_in_chat(
    chat_placeholder,
    text: str,
    speed: float = 0.02,
    pre_delay: float = 0.25,
    on_error_state: str = "IDLE",
) -> None:
    """
    Types text inside a chat message bubble using a placeholder (updates in place).

    HARDENED:
    - Prevents NameError / NoneType issues
    - Catches runtime errors so the app won't crash
    - Resets MAXE state on failure so MAXE won't "vanish" due to an exception
    """

    try:
        # Ensure text is always a string
        if text is None:
            text = ""
        text = str(text)

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

    except Exception as e:
        # Never let an exception kill the app mid-render
        try:
            st.session_state.maxe_state = on_error_state
        except Exception:
            pass

        # Show a safe fallback message in chat instead of crashing
        with chat_placeholder:
            with st.chat_message("assistant"):
                st.error("MAXE hit a hiccup while responding. Please try again.")
                st.caption(f"Error: {e}")


# ----------------------------
# Placeholder MAXE replies (swap later with AI / rules)
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
# Page + CSS animation
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
  max-width:260px;
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

/* RESPONDING: slightly calmer pulse (still feels active) */
.maxe-responding{
  animation: maxe-pulse 1.6s ease-in-out infinite;
  filter: drop-shadow(0 0 10px rgba(212, 175, 55, 0.55));
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
    We show one static image per state; 'animation' is CSS-based.
    """
    if state == "THINKING":
        img_path = ASSET_THINKING_A
        css_class = "maxe-thinking"
    elif state == "ESCALATION":
        img_path = ASSET_ESCALATION
        css_class = "maxe-escalation"
    elif state == "RESPONDING":
        img_path = ASSET_IDLE
        css_class = "maxe-responding"
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
# Session state init
# ----------------------------
if "messages" not in st.session_state:
    st.session_state.messages: List[Dict[str, Any]] = []

if "maxe_state" not in st.session_state:
    st.session_state.maxe_state = "IDLE"

if "pending" not in st.session_state:
    st.session_state.pending = False

if "pending_user_msg" not in st.session_state:
    st.session_state.pending_user_msg = ""
# ----------------------------
# Layout
# ----------------------------
left, right = st.columns([0.9, 2.1], gap="large")

with left:
    st.markdown("## MAXE")
    status_slot = st.empty()
    maxe_slot = st.empty()  # single render slot (prevents duplicates)

with right:
    st.markdown("## Chat")

    # 1) Render chat history FIRST
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    # 2) If we have a pending response, PROCESS IT HERE (BEFORE chat_input)
    if st.session_state.pending:
        msg = st.session_state.pending_user_msg

        # Let the user see THINKING for a moment
        time.sleep(0.8)

        escalate, reasons = check_escalation(msg)

        if escalate:
            st.session_state.maxe_state = "ESCALATION"
            st.error("COACH NOTIFIED")

            try:
                send_coach_email(
                    subject="MAXE Escalation Alert",
                    body=f"User message:\n\n{msg}\n\nContext:\n- App: MAXE\n- State: ESCALATION\n",
                    reasons=reasons
                )
            except Exception as e:
                st.warning(f"Coach email not sent (check Streamlit secrets): {e}")

            reply = maxe_escalation_reply()
        else:
            st.session_state.maxe_state = "RESPONDING"
            reply = maxe_reply_for(msg)

        # Type reply (this will now appear ABOVE the input box)
        chat_placeholder = st.empty()
        typewriter_in_chat(chat_placeholder, reply, speed=0.02, pre_delay=0.35)

        # Save assistant reply
        st.session_state.messages.append({"role": "assistant", "content": reply})

        # Clear pending + reset state
        st.session_state.pending = False
        st.session_state.pending_user_msg = ""
        st.session_state.maxe_state = "IDLE"

        # OPTIONAL: rerun so the typed placeholder becomes "real" history immediately
        st.rerun()

    # 3) chat_input LAST (always at bottom)
    user_msg = st.chat_input("Message MAXE…")

    # Phase 1: user submits -> queue THINKING -> rerun
    if user_msg:
        st.session_state.messages.append({"role": "user", "content": user_msg})
        st.session_state.pending = True
        st.session_state.pending_user_msg = user_msg
        st.session_state.maxe_state = "THINKING"
        st.rerun()


# ----------------------------
# Render MAXE ONCE per run
# ----------------------------
with left:
    status_slot.caption(f"Status: {st.session_state.maxe_state}")
    with maxe_slot.container():
        render_maxe_animated(st.session_state.maxe_state)


