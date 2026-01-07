# app.py — MAXE Hero + MAXE Avatar Chat (Streamlit Cloud)
# ✅ Big centered MAXE "hero" at top (IDLE / THINKING A<->B / ESCALATION)
# ✅ Assistant chat avatar replaced with MAXE (no orange robot icon)
# ✅ Thinking animation updates in-place (no duplicate images, no vanish)
# ✅ Escalation triggers + email-only coach notification (best effort)
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
import base64
import smtplib
from email.message import EmailMessage
from typing import List, Dict, Any, Optional, Tuple

import streamlit as st


# ----------------------------
# ASSETS
# ----------------------------
ASSET_IDLE = "maxe_assets/maxe_idle.png"
ASSET_THINKING_A = "maxe_assets/maxe_thinking_a.png"
ASSET_THINKING_B = "maxe_assets/maxe_thinking_b.png"
ASSET_ESCALATION = "maxe_assets/maxe_escalation.png"

# UI sizing
HERO_WIDTH_PX = 340      # try 280–420
THINK_SECONDS = 0.9
THINK_INTERVAL = 0.25

# If you want the “typed” effect, set True (can feel janky on Streamlit Cloud)
ENABLE_TYPEWRITER = False
TYPE_SPEED = 0.01


# ----------------------------
# SECRETS / ENV helper
# ----------------------------
def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    if hasattr(st, "secrets") and key in st.secrets:
        return str(st.secrets[key])
    return os.getenv(key, default)


# ----------------------------
# CSS (hero glow)
# ----------------------------
st.markdown(
    """
<style>
.maxe-hero {
    border-radius: 16px;
    transition: box-shadow 0.25s ease, transform 0.25s ease;
    display: block;
}

.maxe-idle { box-shadow: none; }

.maxe-thinking {
    box-shadow:
        0 0 25px rgba(212, 175, 55, 0.35),
        0 0 60px rgba(212, 175, 55, 0.25);
}

.maxe-escalation {
    box-shadow:
        0 0 25px rgba(255, 60, 60, 0.55),
        0 0 70px rgba(255, 60, 60, 0.35);
}

/* Center the app a bit tighter */
.block-container { padding-top: 2rem; }
</style>
""",
    unsafe_allow_html=True,
)


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

def check_escalation(user_msg: str) -> Tuple[bool, List[str]]:
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
# Replies (stubs for now)
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
# Image helpers (base64 to prevent broken <img src="localpath">)
# ----------------------------
@st.cache_data(show_spinner=False)
def img_to_data_uri(path: str) -> str:
    with open(path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:image/png;base64,{b64}"

def hero_path_for_state(state: str, frame: str = "A") -> str:
    if state == "ESCALATION":
        return ASSET_ESCALATION
    if state == "THINKING":
        return ASSET_THINKING_A if frame == "A" else ASSET_THINKING_B
    return ASSET_IDLE

def css_class_for_state(state: str) -> str:
    return {
        "IDLE": "maxe-idle",
        "THINKING": "maxe-thinking",
        "ESCALATION": "maxe-escalation",
    }.get(state, "maxe-idle")

def render_hero(slot, state: str, frame: str = "A", width_px: int = HERO_WIDTH_PX) -> None:
    asset_path = hero_path_for_state(state, frame=frame)
    data_uri = img_to_data_uri(asset_path)
    cls = css_class_for_state(state)

    slot.markdown(
        f"""
        <div style="display:flex; justify-content:center;">
            <img src="{data_uri}" class="maxe-hero {cls}" width="{width_px}" />
        </div>
        """,
        unsafe_allow_html=True
    )

def assistant_avatar_data_uri(state: str = "IDLE", frame: str = "A") -> str:
    # Use the same art as the hero for the avatar
    return img_to_data_uri(hero_path_for_state(state, frame=frame))


# ----------------------------
# “Thinking” animation (in-place)
# ----------------------------
def animate_thinking(hero_slot, status_slot, bubble_slot) -> None:
    end = time.time() + THINK_SECONDS
    frame = "A"
    while time.time() < end:
        status_slot.caption("Status: THINKING")
        render_hero(hero_slot, "THINKING", frame=frame)

        # Keep the assistant bubble showing activity
        bubble_slot.markdown("…")

        frame = "B" if frame == "A" else "A"
        time.sleep(THINK_INTERVAL)


def typewriter(bubble_slot, text: str) -> None:
    if not ENABLE_TYPEWRITER:
        bubble_slot.markdown(text)
        return

    typed = ""
    for ch in text:
        typed += ch
        bubble_slot.markdown(typed)
        time.sleep(TYPE_SPEED)


# ----------------------------
# Streamlit App
# ----------------------------
st.set_page_config(page_title="MAXE", layout="centered")

if "messages" not in st.session_state:
    st.session_state.messages: List[Dict[str, Any]] = []
if "hero_state" not in st.session_state:
    st.session_state.hero_state = "IDLE"


# Title
st.markdown("<h1 style='text-align:center; margin-bottom: 0.5rem;'>MAXE</h1>", unsafe_allow_html=True)

# Hero (single stable placeholders)
hero_left, hero_center, hero_right = st.columns([1, 2, 1])
with hero_center:
    hero_slot = st.empty()
    status_slot = st.empty()

    status_slot.caption(f"Status: {st.session_state.hero_state}")
    render_hero(hero_slot, st.session_state.hero_state, frame="A")

st.divider()


# Chat history (assistant uses MAXE avatar)
for m in st.session_state.messages:
    if m["role"] == "user":
        with st.chat_message("user"):
            st.markdown(m["content"])
    else:
        with st.chat_message("assistant", avatar=assistant_avatar_data_uri("IDLE")):
            st.markdown(m["content"])


# Input
user_msg = st.chat_input("Message MAXE…")

if user_msg:
    # User message
    st.session_state.messages.append({"role": "user", "content": user_msg})
    with st.chat_message("user"):
        st.markdown(user_msg)

    escalate, reasons = check_escalation(user_msg)

    if escalate:
        # Escalation state
        st.session_state.hero_state = "ESCALATION"
        status_slot.caption("Status: ESCALATION")
        render_hero(hero_slot, "ESCALATION", frame="A")

        reply = maxe_escalation_reply()

        with st.chat_message("assistant", avatar=assistant_avatar_data_uri("ESCALATION")):
            bubble_slot = st.empty()
            typewriter(bubble_slot, reply)

        st.session_state.messages.append({"role": "assistant", "content": reply})

        # Email coach (best effort)
        try:
            send_coach_email(
                subject="MAXE Escalation Alert",
                body=f"User message:\n\n{user_msg}\n\nContext:\n- App: MAXE\n- State: ESCALATION\n",
                reasons=reasons,
            )
        except Exception as e:
            st.warning(f"Coach email not sent (check Streamlit secrets): {e}")

    else:
        # Thinking state + animation (no duplicates / no vanish)
        st.session_state.hero_state = "THINKING"
        status_slot.caption("Status: THINKING")
        render_hero(hero_slot, "THINKING", frame="A")

        with st.chat_message("assistant", avatar=assistant_avatar_data_uri("THINKING", frame="A")):
            bubble_slot = st.empty()
            animate_thinking(hero_slot, status_slot, bubble_slot)

            # Return to IDLE and respond
            st.session_state.hero_state = "IDLE"
            status_slot.caption("Status: IDLE")
            render_hero(hero_slot, "IDLE", frame="A")

            reply = maxe_reply_for(user_msg)
            typewriter(bubble_slot, reply)

        st.session_state.messages.append({"role": "assistant", "content": reply})

    st.rerun()
