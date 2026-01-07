# app.py — MAXE MVP (Streamlit Cloud) — STABLE VERSION
# Fixes:
# - MAXE fixed size (no CSS dependency)
# - Single-image placeholder (prevents duplicate/stacked images)
# - Thinking animation swaps A<->B in the SAME placeholder
# - Optional typewriter (default OFF for stability). Uses safe renderer.
# - Escalation triggers + email-only coach notification (best effort)
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
from email.message import EmailMessage
from typing import List, Dict, Any, Optional

import streamlit as st

# ----------------------------
# ASSETS
# ----------------------------
ASSET_IDLE = "maxe_assets/maxe_idle.png"
ASSET_THINKING_A = "maxe_assets/maxe_thinking_a.png"
ASSET_THINKING_B = "maxe_assets/maxe_thinking_b.png"
ASSET_ESCALATION = "maxe_assets/maxe_escalation.png"

# ----------------------------
# UI TUNING
# ----------------------------
MAXE_IMG_WIDTH = 260  # small card size (try 240–300)
TYPEWRITER_SPEED = 0.0  # 0.0 = instant (recommended for Streamlit stability). Try 0.01 if you insist.

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
# MAXE image rendering + animation (single placeholder)
# ----------------------------
def maxe_path_for(state: str, frame: str = "A") -> str:
    if state == "THINKING":
        return ASSET_THINKING_A if frame == "A" else ASSET_THINKING_B
    if state == "ESCALATION":
        return ASSET_ESCALATION
    return ASSET_IDLE

def render_maxe_to(placeholder, state: str, frame: str = "A") -> None:
    placeholder.image(maxe_path_for(state, frame), width=MAXE_IMG_WIDTH)

def animate_thinking_to(placeholder, seconds: float = 1.0, interval: float = 0.35) -> None:
    """Swaps A<->B in the SAME placeholder (prevents duplicate images)."""
    end = time.time() + seconds
    frame = "A"
    while time.time() < end:
        render_maxe_to(placeholder, "THINKING", frame)
        frame = "B" if frame == "A" else "A"
        time.sleep(interval)

# ----------------------------
# Safe assistant reply renderer (typewriter optional)
# ----------------------------
def typewriter_in_chat(chat_placeholder, text, speed: float = 0.0, pre_delay: float = 0.15) -> None:
    """
    Stable assistant response renderer.
    - speed==0: instant (recommended)
    - speed>0: types out (can be laggy on Streamlit Cloud)
    """
    try:
        if text is None:
            text = ""
        text = str(text)

        with chat_placeholder:
            with st.chat_message("assistant"):
                bubble = st.empty()
                bubble.markdown("…")
                time.sleep(pre_delay)

                if speed and speed > 0:
                    typed = ""
                    for ch in text:
                        typed += ch
                        bubble.markdown(typed)
                        time.sleep(speed)
                else:
                    bubble.markdown(text)

    except Exception as e:
        # Never hard-crash the app because of typing
        with chat_placeholder:
            with st.chat_message("assistant"):
                st.error("MAXE hit an error while responding. Try again.")
                st.caption(f"Error: {e}")

# ----------------------------
# Placeholder MAXE reply (replace later with AI/rules)
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
# Streamlit App
# ----------------------------
st.set_page_config(page_title="MAXE", layout="wide")

# Session init
if "messages" not in st.session_state:
    st.session_state.messages: List[Dict[str, Any]] = []
if "maxe_state" not in st.session_state:
    st.session_state.maxe_state = "IDLE"
if "pending" not in st.session_state:
    st.session_state.pending = False
if "pending_user_msg" not in st.session_state:
    st.session_state.pending_user_msg = ""
if "pending_escalate" not in st.session_state:
    st.session_state.pending_escalate = False
if "pending_reasons" not in st.session_state:
    st.session_state.pending_reasons = []

left, right = st.columns([0.9, 2.1], gap="large")

# --- LEFT: MAXE (always render first, every run) ---
with left:
    st.markdown("## MAXE")
    status_slot = st.caption(f"Status: {st.session_state.maxe_state}")
    maxe_ph = st.empty()
    # Always show something
    render_maxe_to(maxe_ph, st.session_state.maxe_state)

# --- RIGHT: Chat ---
with right:
    st.markdown("## Chat")

    # 1) Render message history
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    # 2) If we have a pending response, do it now (this makes UI stable)
    if st.session_state.pending:
        user_msg = st.session_state.pending_user_msg
        escalate = st.session_state.pending_escalate
        reasons = st.session_state.pending_reasons

        if escalate:
            # Escalation visuals
            st.session_state.maxe_state = "ESCALATION"
            status_slot.caption("Status: ESCALATION")
            render_maxe_to(maxe_ph, "ESCALATION")
            st.error("COACH NOTIFIED")

            # Email coach (best effort)
            try:
                send_coach_email(
                    subject="MAXE Escalation Alert",
                    body=f"User message:\n\n{user_msg}\n\nContext:\n- App: MAXE\n- State: ESCALATION\n",
                    reasons=reasons
                )
            except Exception as e:
                st.warning(f"Coach email not sent (check Streamlit secrets): {e}")

            reply = maxe_escalation_reply()

        else:
            # Thinking phase
            st.session_state.maxe_state = "THINKING"
            status_slot.caption("Status: THINKING")
            render_maxe_to(maxe_ph, "THINKING", frame="A")
            animate_thinking_to(maxe_ph, seconds=1.0, interval=0.35)

            # Responding
            st.session_state.maxe_state = "RESPONDING"
            status_slot.caption("Status: RESPONDING")
            render_maxe_to(maxe_ph, "IDLE")
            reply = maxe_reply_for(user_msg)

        # Assistant reply (stable)
        chat_placeholder = st.empty()
        typewriter_in_chat(chat_placeholder, reply, speed=TYPEWRITER_SPEED, pre_delay=0.15)
        st.session_state.messages.append({"role": "assistant", "content": reply})

        # Clear pending + return to idle
        st.session_state.pending = False
        st.session_state.pending_user_msg = ""
        st.session_state.pending_escalate = False
        st.session_state.pending_reasons = []
        st.session_state.maxe_state = "IDLE"
        status_slot.caption("Status: IDLE")
        render_maxe_to(maxe_ph, "IDLE")

        # Rerun so the typed/instant message becomes part of "history" cleanly
        st.rerun()

    # 3) Input LAST (keeps it at the bottom)
    user_msg = st.chat_input("Message MAXE…")

    if user_msg:
        # Show user message immediately
        st.session_state.messages.append({"role": "user", "content": user_msg})

        # Decide escalation now, but respond next run (stable pattern)
        escalate, reasons = check_escalation(user_msg)
        st.session_state.pending = True
        st.session_state.pending_user_msg = user_msg
        st.session_state.pending_escalate = escalate
        st.session_state.pending_reasons = reasons

        # Flip MAXE state right away so user sees it
        st.session_state.maxe_state = "ESCALATION" if escalate else "THINKING"

        st.rerun()




