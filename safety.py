import re
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class EscalationResult:
    escalate: bool
    reasons: List[str]

def _contains_any(text: str, patterns: List[str]) -> bool:
    return any(re.search(p, text, flags=re.IGNORECASE) for p in patterns)

def check_escalation(user_msg: str) -> EscalationResult:
    """
    MVP escalation logic using regex patterns.
    Returns whether to escalate and why.
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

    needs_coach = [
        r"\bmax out\b|\b1rm\b|\bPR\b",
        r"\bchange (my|the) program\b|\bmodify (my|the) program\b",
        r"\bskip (this|the) week\b|\bdeload\b.*\bnow\b",
        r"\bwhat did you mean\b|\bwhat do you want me to do\b",
    ]

    if _contains_any(t, medical_red_flags):
        reasons.append("medical_red_flag")

    if _contains_any(t, injury_red_flags):
        reasons.append("injury_red_flag")

    if _contains_any(t, needs_coach):
        reasons.append("requires_coach_judgment")

    return EscalationResult(escalate=len(reasons) > 0, reasons=reasons)
