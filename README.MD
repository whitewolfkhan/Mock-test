# QueueStorm Ticket Sorter

A rules-based CRM ticket classifier for the **bKash SUST CSE Carnival 2026 – Codex Community Hackathon (Mock Preliminary)**.

It reads one customer support message and returns a structured classification: problem type, severity, owning department, a safe one-line agent summary, a human-review flag, and a confidence score. No LLM, no GPU, no external API calls — fully deterministic.

## Endpoints

| Method | Path           | Purpose                                       |
|--------|----------------|-----------------------------------------------|
| GET    | `/health`      | Service health check                          |
| POST   | `/sort-ticket` | Classify one CRM ticket                       |

### Example request

```bash
curl -X POST https://YOUR-URL/sort-ticket \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": "T-001",
    "channel": "app",
    "locale": "en",
    "message": "I sent 5000 taka to a wrong number this morning, please help me get it back"
  }'
```

### Example response

```json
{
  "ticket_id": "T-001",
  "case_type": "wrong_transfer",
  "severity": "high",
  "department": "dispute_resolution",
  "agent_summary": "Customer reports sending money to the wrong recipient and requests recovery.",
  "human_review_required": false,
  "confidence": 0.88
}
```

## How it works

1. **case_type** is decided by priority-ordered keyword matching: phishing → wrong_transfer → payment_failed → refund_request → other. Phishing is checked first so safety-critical tickets are never missed.
2. **severity** is derived from case_type plus keyword nudges (e.g. "balance deducted" makes a failed payment `high`).
3. **department** is routed from case_type (disputes, payments_ops, fraud_risk, customer_support).
4. **agent_summary** uses safe neutral templates that never request PIN/OTP/password/card number. A guard re-checks the output before returning.
5. **human_review_required** is `true` for any critical severity or any phishing case.

## Run locally

Requires Python 3.9+.

```bash
# 1. Clone
git clone https://github.com/YOUR-USERNAME/queuestorm-ticket-sorter.git
cd queuestorm-ticket-sorter

# 2. Create a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
uvicorn main:app --reload
```

Server runs at `http://127.0.0.1:8000`.
Interactive docs (Swagger UI) at `http://127.0.0.1:8000/docs`.

## Test

With the server running, in a second terminal:

```bash
python test_cases.py
```

All 5 public sample cases should print `PASS`.


