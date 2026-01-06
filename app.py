# app.py — MAXE MVP (Streamlit Cloud)
# - MAXE image states: IDLE / THINKING (A<->B) / ESCALATION
# - Visible thinking animation (in-place loop)
# - Typed text reply (in-place typewriter)
# - Escalation trigger + email-only coach notification
#
# Folder structure expected:
#   app.py
#   requirements.txt
#   notify.py (optional; not used here)
#   safety.py  (optional; not used here)
#   typing.py  (optional; not used here)
#   maxe_assets/
#       maxe_idle.png
#       maxe_thinking_a.png
#       maxe_thinking_b.png
#       maxe_escalation.png

import os
import re
import time
import smtplib
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


# ----------------------------
# UI Helpers: MAXE image + animations
# ----------------------------
def render_maxe(image_placeholder, state: str, frame: str = "A") -> None:
    if state == "THINKING":
        path = ASSET_THINKING_A if frame == "A" else ASSET_THINKING_B
    elif state == "ESCALATION":
        path = ASSET_ESCALATION
    else:
        path = ASSET_IDLE

    image_placeholder.image(path, use_container_width=True)

def animate_thinking(image_placeholder, seconds: float = 1.4, interval: float = 0.45) -> None:
    """
    Visible, blocking animation loop (simple + reliable in Streamlit).
    Swaps A<->B for a short duration.
    """
    end = time.time() + seconds
    frame = "A"
    while time.time() < end:
        render_maxe(image_placeholder, "THINKING", frame=frame)
        frame = "B" if frame == "A" else "A"
        time.sleep(interval)

def typewriter_in_chat(chat_placeholder, text: str, speed: float = 0.02, pre_delay: float = 0.35) -> None:
    """
    Types text inside a chat message bubble.
    Uses a placeholder so it updates in place.
    """
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
    # v1: simple helpful response. Replace with your rule engine / AI later.
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
# Streamlit App
# ----------------------------
st.set_page_config(page_title="MAXE", layout="wide")

# Session state init
if "messages" not in st.session_state:
    st.session_state.messages: List[Dict[str, Any]] = []

left, right = st.columns([1, 2], gap="large")

with left:
    st.markdown("## MAXE")
    maxe_img = st.empty()
    # Default render (idle)
    render_maxe(maxe_img, "IDLE")
    status_line = st.caption("Status: IDLE")

with right:
    st.markdown("## Chat")

    # Render message history
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    user_msg = st.chat_input("Message MAXE…")

    if user_msg:
        # 1) Show user message immediately
        st.session_state.messages.append({"role": "user", "content": user_msg})
        with st.chat_message("user"):
            st.markdown(user_msg)

        # 2) Escalation check
        escalate, reasons = check_escalation(user_msg)

        if escalate:
            # Show escalation visuals
            render_maxe(maxe_img, "ESCALATION")
            status_line.caption("Status: ESCALATION")
            st.error("COACH NOTIFIED")

            # Notify coach (best effort)
            try:
                send_coach_email(
                    subject="MAXE Escalation Alert",
                    body=f"User message:\n\n{user_msg}\n\nContext:\n- App: MAXE\n- State: ESCALATION\n",
                    reasons=reasons
                )
            except Exception as e:
                # Still escalate visually even if email isn't configured
                st.warning(f"Coach email not sent (check Streamlit secrets): {e}")

            # Reply (typed)
            reply = maxe_escalation_reply()
            # Save to history AFTER typing so it matches what user saw
            chat_placeholder = st.empty()
            typewriter_in_chat(chat_placeholder, reply, speed=0.02, pre_delay=0.35)
            st.session_state.messages.append({"role": "assistant", "content": reply})

        else:
            # 3) Thinking animation (visible)
            status_line.caption("Status: THINKING")
            animate_thinking(maxe_img, seconds=1.35, interval=0.45)

            # 4) Respond (typed)
            render_maxe(maxe_img, "IDLE")
            status_line.caption("Status: RESPONDING")

            reply = maxe_reply_for(user_msg)
            chat_placeholder = st.empty()
            typewriter_in_chat(chat_placeholder, reply, speed=0.02, pre_delay=0.35)
            st.session_state.messages.append({"role": "assistant", "content": reply})

            status_line.caption("Status: IDLE")
