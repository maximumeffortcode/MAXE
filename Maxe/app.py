# app.py
# MAXE MVP (Web / Streamlit)
# Features:
# - MAXE mascot panel (IDLE / THINKING pulse / ESCALATION)
# - Thinking animation: swaps THINKING_A <-> THINKING_B every 450ms (via autorefresh)
# - Chat history (persistent in session)
# - Typed-text “talking” effect
# - Escalation detection + email-only coach notification

import os
import re
import time
import smtplib
from email.message import EmailMessage
from typing import List, Optional

import streamlit as st
from streamlit_autorefresh import st_autorefresh

# ----------------------------
# CONFIG / ASSETS
# ----------------------------

# Put your images in:
#   maxe_assets/maxe_idle.png
#   maxe_assets/maxe_thinking_a.png
#   maxe_assets/maxe_thinking_b.png
#   maxe_assets/maxe_escalation.png
ASSET_IDLE = "maxe_assets/maxe_idle.png"
ASSET_THINKING_A = "maxe_assets/maxe_thinking_a.png"
ASSET_THINKING_B = "maxe_assets/maxe_thinking_b.png"
ASSET_ESCALATION = "maxe_assets/maxe_escalation.png"


# ----------------------------
# SECRETS HELPERS (Streamlit Cloud or Env Vars)
# ----------------------------

def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Try Streamlit secrets first, then env vars."""
    if hasattr(st, "secrets") and key in st.secrets:
        return str(st.secrets[key])
    return os.getenv(key, default)


# ----------------------------
# EMAIL NOTIFY (Email-only MVP)
# ----------------------------

def send_coach_email(subject: str, body: str, reasons: List[str]) -> None:
    """
    Sends escalation email using SMTP.
    Required secrets/env:
      COACH_EMAIL
      SMTP_HOST
      SMTP_PORT (optional; default 587)
      SMTP_USER
      SMTP_PASS
      SMTP_FROM (optional; default SMTP_USER)
    """
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
# ESCALATION LOGIC (MVP)
# ----------------------------

def contains_any(text: str, patterns: List[str]) -> bool:
    return any(re.search(p, text, flags=re.IGNORECASE) for p in patterns)

def check_escalation(user_msg: str) -> tuple[bool, List[str]]:
    """
    Returns (escalate, reasons).
    Keyword/regex MVP: fast, effective, tune later.
    """
    t = user_msg.strip()
    reasons: List[str] = []

    medical_red_flags = [
        r"\bchest pain\b|\bchest pressure\b",
        r"\bfaint(ed|ing)?\b|\bpassed out\b|\bblack(ed)? out\b",
        r"\b(can't|cannot) breathe\b|\bshort(ness)? of breath\b|\bsevere shortness of breath\b",
        r"\bnumb(ness)?\b|\btingl(e|ing)\b|\bweak(ness)?\b|\bface droop\b|\bconfus(ed|ion)\b",
        r"\bpalpitation(s)?\b|\bheart flutter\b|\birregular heartbeat\b",
        r"\baorta\b|\baneurysm\b",
        r"\bblood pressure\b.*\b(high|spike|spiking)\b",
    ]

    injury_red_flags = [
        r"\bsharp pain\b",
        r"\bpop(ped)?\b.*\bpain\b|\bheard a pop\b",
        r"\bswelling\b|\bbruise\b|\bbruising\b",
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

    if contains_any(t, medical_red_flags):
        reasons.append("medical_red_flag")
    if contains_any(t, injury_red_flags):
        reasons.append("injury_red_flag")
    if contains_any(t, requires_coach):
        reasons.append("requires_coach_judgment")

    return (len(reasons) > 0, reasons)


# ----------------------------
# TYPED TEXT (MAXE “talking” illusion)
# ----------------------------

def type_text(text: str, container, typing_speed: float = 0.035, pre_delay: float = 0.7) -> None:
    """
    Types text into a Streamlit placeholder.
    NOTE: This blocks briefly, which is fine for MVP.
    """
    container.markdown("…")
    time.sleep(pre_delay)

    typed = ""
    for ch in text:
        typed += ch
        container.markdown(typed)
        time.sleep(typing_speed)


# ----------------------------
# MAXE STATE MACHINE
# ----------------------------

STATE_IDLE = "IDLE"
STATE_THINKING = "THINKING"
STATE_ESCALATION = "ESCALATION"

def init_session_state():
    if "maxe_state" not in st.session_state:
        st.session_state.maxe_state = STATE_IDLE
    if "thinking_frame" not in st.session_state:
        st.session_state.thinking_frame = "A"  # toggles A/B
    if "messages" not in st.session_state:
        st.session_state.messages = []  # list[dict]: {role: "user"/"assistant", content: str}
    if "last_user_msg" not in st.session_state:
        st.session_state.last_user_msg = ""
    if "escalation_banner" not in st.session_state:
        st.session_state.escalation_banner = False

def current_maxe_image_path() -> str:
    if st.session_state.maxe_state == STATE_THINKING:
        return ASSET_THINKING_A if st.session_state.thinking_frame == "A" else ASSET_THINKING_B
    if st.session_state.maxe_state == STATE_ESCALATION:
        return ASSET_ESCALATION
    return ASSET_IDLE


# ----------------------------
# UI
# ----------------------------

st.set_page_config(page_title="MAXE", layout="wide")

init_session_state()

# Auto-refresh ONLY while thinking so the eyes pulse (no constant reruns)
if st.session_state.maxe_state == STATE_THINKING:
    st_autorefresh(interval=450, key="maxe_thinking_refresh")
    st.session_state.thinking_frame = "B" if st.session_state.thinking_frame == "A" else "A"

left, right = st.columns([1, 2], gap="large")

with left:
    st.markdown("## MAXE")
    st.image(current_maxe_image_path(), use_container_width=True)

    # Optional status line
    if st.session_state.maxe_state == STATE_THINKING:
        st.caption("Status: THINKING")
    elif st.session_state.maxe_state == STATE_ESCALATION:
        st.caption("Status: ESCALATION")
    else:
        st.caption("Status: IDLE")

with right:
    st.markdown("## Chat")

    if st.session_state.escalation_banner:
        st.error("COACH NOTIFIED")
        # Keep it visible once triggered for the session; comment next line if you want it to persist.
        st.session_state.escalation_banner = False

    # Render chat history
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    user_msg = st.chat_input("Message MAXE…")

    if user_msg:
        # Save user msg
        st.session_state.messages.append({"role": "user", "content": user_msg})
        st.session_state.last_user_msg = user_msg

        # Escalation check
        escalate, reasons = check_escalation(user_msg)

        if escalate:
            # 1) Escalate state + banner
            st.session_state.maxe_state = STATE_ESCALATION
            st.session_state.escalation_banner = True

            # 2) Notify coach via email (best-effort)
            try:
                send_coach_email(
                    subject="MAXE Escalation Alert",
                    body=(
                        f"User message:\n\n{user_msg}\n\n"
                        f"Context:\n- App: MAXE\n- State: ESCALATION\n"
                    ),
                    reasons=reasons
                )
            except Exception as e:
                # We still escalate visually even if email isn't configured yet
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"Coach notification failed (email config missing): `{e}`"
                })

            # 3) Safe MAXE reply
            escalation_reply = (
                "Coach notified.\n\n"
                "Stop the session if symptoms worsen.\n"
                "If you have chest pain, fainting, or severe shortness of breath, seek urgent medical care."
            )
            st.session_state.messages.append({"role": "assistant", "content": escalation_reply})

            # Rerun to show new state + banner + chat
            st.rerun()

        # NORMAL FLOW
        st.session_state.maxe_state = STATE_THINKING
        st.session_state.thinking_frame = "A"
        st.rerun()


# ----------------------------
# AFTER RERUN: If we are in THINKING, generate response once and type it out.
# We do it here so the UI has already switched to THINKING before typing begins.
# ----------------------------
if st.session_state.maxe_state == STATE_THINKING and st.session_state.last_user_msg:
    # IMPORTANT: stop thinking animation before typing so only one illusion runs at a time
    st.session_state.maxe_state = STATE_IDLE
    msg = st.session_state.last_user_msg
    st.session_state.last_user_msg = ""  # consume it so we don't respond twice

    # TODO: Replace this with your real AI call later.
    # For now, a deterministic “MAXE-style” placeholder response:
    maxe_reply = (
        "Acknowledged.\n"
        "If you need a substitution, tell me your available equipment and what feels limited.\n"
        "I will preserve the intent and keep risk low."
    )

    # Add assistant message first (empty), then type into it visually
    st.session_state.messages.append({"role": "assistant", "content": maxe_reply})

    # Re-render page so typed text happens in-place
    st.rerun()
