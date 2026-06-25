"""
QueueStorm Warmup - Mock Preliminary Task
A rules-based CRM ticket classifier for bKash SUST CSE Carnival 2026.

Reads one customer message and returns:
  - case_type, severity, department, agent_summary
  - human_review_required, confidence
"""

import re
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="QueueStorm Ticket Sorter", version="1.0.0")


# ---------- Request / Response Schemas ----------

class TicketRequest(BaseModel):
    ticket_id: str
    channel: Optional[str] = None
    locale: Optional[str] = None
    message: str


class TicketResponse(BaseModel):
    ticket_id: str
    case_type: str
    severity: str
    department: str
    agent_summary: str
    human_review_required: bool
    confidence: float


# ---------- Keyword Rules ----------
# Each case_type maps to a list of lowercase keywords/phrases.
# Order of checking matters: phishing is checked first (highest safety priority).

PHISHING_KEYWORDS = [
    "otp", "pin", "password", "passcode", "cvv", "card number",
    "someone called", "asked my", "asking for my", "share my code",
    "verification code", "scam", "scammer", "fraud", "phishing",
    "suspicious call", "suspicious sms", "claiming to be bkash",
    "claiming to be bank", "give my otp", "told me to send",
    "asked for my pin", "asked for otp",
]

WRONG_TRANSFER_KEYWORDS = [
    "wrong number", "wrong recipient", "wrong account", "wrong person",
    "sent to wrong", "wrong nagad", "wrong bkash number", "mistyped",
    "wrong mobile", "incorrect number", "by mistake to", "wrong receiver",
    "sent money to wrong", "transferred to wrong",
]

PAYMENT_FAILED_KEYWORDS = [
    "payment failed", "transaction failed", "failed but", "balance deducted",
    "money deducted", "amount deducted", "deducted but", "payment did not go",
    "payment didn't go", "transaction declined", "failed transaction",
    "paid but not received", "cut from balance", "debited but failed",
    "stuck transaction", "pending transaction",
]

REFUND_KEYWORDS = [
    "refund", "money back", "return my money", "want my money back",
    "changed my mind", "cancel my order", "give me back", "reverse the payment",
]


def contains_any(text: str, keywords) -> bool:
    return any(kw in text for kw in keywords)


def count_matches(text: str, keywords) -> int:
    return sum(1 for kw in keywords if kw in text)


# ---------- Severity Logic ----------

CRITICAL_HINTS = ["urgent", "emergency", "huge amount", "lakh", "lac",
                  "large amount", "everything", "all my money", "life savings"]


def decide_severity(case_type: str, text: str) -> str:
    """Severity is driven by case_type, with keyword nudges."""
    if case_type == "phishing_or_social_engineering":
        return "critical"

    if case_type == "wrong_transfer":
        return "high"

    if case_type == "payment_failed":
        # balance deducted = high; plain failure = medium
        if "deduct" in text or "debited" in text or "cut from" in text:
            return "high"
        return "medium"

    if case_type == "refund_request":
        # contested/angry refund = medium, simple change-of-mind = low
        if "changed my mind" in text or "by mistake" in text:
            return "low"
        if "not received" in text or "didn't receive" in text or "scam" in text:
            return "medium"
        return "low"

    # other
    if contains_any(text, CRITICAL_HINTS):
        return "medium"
    return "low"


# ---------- Department Routing ----------

def decide_department(case_type: str, severity: str) -> str:
    if case_type == "wrong_transfer":
        return "dispute_resolution"
    if case_type == "payment_failed":
        return "payments_ops"
    if case_type == "phishing_or_social_engineering":
        return "fraud_risk"
    if case_type == "refund_request":
        # low severity refund -> customer_support, contested -> disputes
        if severity == "low":
            return "customer_support"
        return "dispute_resolution"
    return "customer_support"  # other


# ---------- Agent Summary (SAFE) ----------
# Never asks the customer to share PIN/OTP/password/card number.

SUMMARY_TEMPLATES = {
    "wrong_transfer": "Customer reports sending money to the wrong recipient and requests recovery.",
    "payment_failed": "Customer reports a failed payment, possibly with balance deducted.",
    "refund_request": "Customer is requesting a refund for a recent transaction.",
    "phishing_or_social_engineering": "Customer reports a suspicious contact attempting to obtain sensitive account information.",
    "other": "Customer reports a general issue that does not match known categories.",
}

# Forbidden phrases the grader checks for in agent_summary.
FORBIDDEN_IN_SUMMARY = ["pin", "otp", "password", "full card number", "card number", "cvv"]


def build_summary(case_type: str, message: str) -> str:
    summary = SUMMARY_TEMPLATES.get(case_type, SUMMARY_TEMPLATES["other"])
    # Safety guard: ensure no forbidden request slips in.
    lowered = summary.lower()
    for bad in FORBIDDEN_IN_SUMMARY:
        if bad in lowered:
            # Fall back to a guaranteed-safe generic summary.
            return "Customer reports an issue requiring agent review."
    return summary


# ---------- Core Classifier ----------

def classify(message: str):
    text = message.lower()

    # Priority order: phishing > wrong_transfer > payment_failed > refund > other
    if contains_any(text, PHISHING_KEYWORDS):
        case_type = "phishing_or_social_engineering"
        confidence = 0.92
    elif contains_any(text, WRONG_TRANSFER_KEYWORDS):
        case_type = "wrong_transfer"
        confidence = 0.88
    elif contains_any(text, PAYMENT_FAILED_KEYWORDS):
        case_type = "payment_failed"
        confidence = 0.85
    elif contains_any(text, REFUND_KEYWORDS):
        case_type = "refund_request"
        confidence = 0.82
    else:
        case_type = "other"
        confidence = 0.55

    severity = decide_severity(case_type, text)
    department = decide_department(case_type, severity)
    human_review = (severity == "critical") or (case_type == "phishing_or_social_engineering")
    summary = build_summary(case_type, message)

    return {
        "case_type": case_type,
        "severity": severity,
        "department": department,
        "agent_summary": summary,
        "human_review_required": human_review,
        "confidence": confidence,
    }


# ---------- Endpoints ----------

@app.get("/health")
def health():
    return {"status": "ok", "service": "queuestorm-ticket-sorter"}


@app.post("/sort-ticket", response_model=TicketResponse)
def sort_ticket(req: TicketRequest):
    result = classify(req.message)
    return TicketResponse(ticket_id=req.ticket_id, **result)


@app.get("/")
def root():
    return {"message": "QueueStorm Ticket Sorter is running. POST to /sort-ticket"}