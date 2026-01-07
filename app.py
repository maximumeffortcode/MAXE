# app.py — MAXE Hero + Avatar Chat (Streamlit Cloud)
# - Big MAXE "hero" at top that reflects state: IDLE / THINKING (A<->B) / ESCALATION
# - Small MAXE avatar beside assistant text in chat
# - Thinking animation swaps A<->B in-place (single placeholders, no duplicates)
# - Escalation triggers + email-only coach notification (best effort)
#
# Folder:
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

# Sizes
HERO_WIDTH = 340        # top image size (try 260–420)
AVATAR_SIZE = 56        # chat avatar size (try 44–72)

# Thinking animation
THINK_SECONDS = 0.9
THINK_INTERVAL = 0.25

# ----------------------------
# SECRETS / ENV helper
# ----------------------------
def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    if hasattr(st, "secrets") and key in st.secrets:
        return str(st.secrets[key])
    return os.getenv(key, default)

#CSS
st.markdown("""
<style>
.maxe-hero {
    border-radius: 16px;
    transition: box-shadow 0.4s ease, transform 0.4s ease;
}

.maxe-idle {
    box-shadow: 0 0 0 rgba(0,0,0,0);
}

.maxe-thinking {
    box-shadow:
        0 0 25px rgba(212, 175, 55, 0.35),
        0 0 60px rgba(212, 175, 55, 0.25);
}

.maxe-escalation {
    box-shadow:
        0 0 25px rgba(255, 60, 60, 0.5),
        0 0 70px rgba(255, 60, 60, 0.4);
}
</style>
""", unsafe_allow_html=True)


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
# ESCALATION CHECK (MVP)
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
# Reply stubs (replace later)
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
# Rendering helpers
# ----------------------------
def hero_path_for_state(state: str, frame: str = "A") -> str:
    if state == "ESCALATION":
        return ASSET_ESCALATION
    if state == "THINKING":
        return ASSET_THINKING_A if frame == "A" else ASSET_THINKING_B
    return ASSET_IDLE

def avatar_path_for_state(state: str, frame: str = "A") -> str:
    # same as hero (kept separate in case you later want different crops)
    return hero_path_for_state(state, frame)

def render_hero(image_path: str, state: str):
    cls = {
        "IDLE": "maxe-idle",
        "THINKING": "maxe-thinking",
        "ESCALATION": "maxe-escalation"
    }.get(state, "maxe-idle")

    st.markdown(
        f"""
        <div style="display:flex; justify-content:center;">
            <img src="{image_path}" class="maxe-hero {cls}" width="320"/>
        </div>
        """,
        unsafe_allow_html=True
    )


def avatar_row(avatar_path: str, content_md: str, placeholder=None):
    def _render():
        col_img, col_text = st.columns([0.12, 0.88], vertical_alignment="top")
        with col_img:
            st.image(avatar_path, width=56)
        with col_text:
            st.markdown(content_md)

    if placeholder:
        with placeholder:
            _render()
    else:
        _render()


def animate_thinking(hero_placeholder, bubble_placeholder) -> None:
    end = time.time() + THINK_SECONDS
    frame = "A"
    while time.time() < end:
        # Update hero
        render_hero(hero_placeholder, "THINKING", frame=frame)
        # Update current assistant bubble ("…")
        avatar_row(avatar_path_for_state("THINKING", frame), "…", placeholder=bubble_placeholder)

        frame = "B" if frame == "A" else "A"
        time.sleep(THINK_INTERVAL)

# ----------------------------
# Streamlit App
# ----------------------------
st.set_page_config(page_title="MAXE", layout="centered")

# Session init
if "messages" not in st.session_state:
    st.session_state.messages: List[Dict[str, Any]] = []
if "hero_state" not in st.session_state:
    st.session_state.hero_state = "IDLE"

# Top HERO area (single placeholder; never duplicate)
st.title("MAXE")

# Centered hero using columns
hero_left, hero_center, hero_right = st.columns([1, 2, 1])

with hero_center:
    hero_slot = st.empty()
    status_slot = st.caption(f"Status: {st.session_state.hero_state}")
    render_hero(hero_slot, st.session_state.hero_state)


# Render history
def avatar_row(avatar_path: str, content_md: str, placeholder=None):
    def _render():
        col_img, col_text = st.columns([0.12, 0.88], vertical_alignment="top")
        with col_img:
            st.image(avatar_path, width=56)
        with col_text:
            st.markdown(content_md)

    if placeholder:
        with placeholder:
            _render()
    else:
        _render()

for m in st.session_state.messages:
    if m["role"] == "user":
        with st.chat_message("user"):
            st.markdown(m["content"])
    else:
        with st.chat_message("assistant"):
            avatar_row(ASSET_IDLE, reply)


# Input
user_msg = st.chat_input("Message MAXE…")

if user_msg:
    # Show user message immediately
    st.session_state.messages.append({"role": "user", "content": user_msg})
    with st.chat_message("user"):
        st.markdown(user_msg)

    escalate, reasons = check_escalation(user_msg)

    if escalate:
        # Set hero escalation immediately
        st.session_state.hero_state = "ESCALATION"
        status_slot.caption("Status: ESCALATION")
        render_hero(hero_slot, "ESCALATION")

        # Bubble escalation
        reply = maxe_escalation_reply()
        with st.chat_message("assistant"):
            avatar_row(ASSET_ESCALATION, reply)

        # Save message
        st.session_state.messages.append({"role": "assistant", "content": reply})

        # Notify coach (best effort)
        try:
            send_coach_email(
                subject="MAXE Escalation Alert",
                body=f"User message:\n\n{user_msg}\n\nContext:\n- App: MAXE\n- State: ESCALATION\n",
                reasons=reasons,
            )
        except Exception as e:
            st.warning(f"Coach email not sent (check Streamlit secrets): {e}")

    else:
        # Thinking phase: animate in-place (hero + current bubble placeholder)
        st.session_state.hero_state = "THINKING"
        status_slot.caption("Status: THINKING")
        render_hero(hero_slot, "THINKING", frame="A")

        with st.chat_message("assistant"):
            bubble_slot = st.empty()
            animate_thinking(hero_slot, bubble_slot)

            # Final reply (stable)
            reply = maxe_reply_for(user_msg)
            st.session_state.hero_state = "IDLE"
            status_slot.caption("Status: IDLE")
            render_hero(hero_slot, "IDLE")

            avatar_row(ASSET_IDLE, reply, placeholder=bubble_slot)

        # Save message
        st.session_state.messages.append({"role": "assistant", "content": reply})

    st.rerun()




