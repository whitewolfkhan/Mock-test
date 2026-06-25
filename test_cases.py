"""
Quick test runner. Start the server first:
    uvicorn main:app --reload
Then in another terminal:
    python test_cases.py
"""
import json
import urllib.request

BASE = "http://127.0.0.1:8000"

CASES = [
    {"ticket_id": "T-1", "message": "I sent 3000 to wrong number",
     "expect_type": "wrong_transfer", "expect_sev": "high"},
    {"ticket_id": "T-2", "message": "Payment failed but balance deducted",
     "expect_type": "payment_failed", "expect_sev": "high"},
    {"ticket_id": "T-3", "message": "Someone called asking my OTP, is that bKash?",
     "expect_type": "phishing_or_social_engineering", "expect_sev": "critical"},
    {"ticket_id": "T-4", "message": "Please refund my last transaction, I changed my mind",
     "expect_type": "refund_request", "expect_sev": "low"},
    {"ticket_id": "T-5", "message": "App crashed when I opened it",
     "expect_type": "other", "expect_sev": "low"},
]


def post(path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def main():
    # health
    with urllib.request.urlopen(BASE + "/health") as r:
        print("HEALTH:", json.loads(r.read()))
    print("-" * 70)

    all_pass = True
    for c in CASES:
        resp = post("/sort-ticket", {"ticket_id": c["ticket_id"], "message": c["message"]})
        ok = resp["case_type"] == c["expect_type"] and resp["severity"] == c["expect_sev"]
        all_pass = all_pass and ok
        print(f"[{'PASS' if ok else 'FAIL'}] {c['message'][:38]:38} -> "
              f"{resp['case_type']:30} {resp['severity']:8} review={resp['human_review_required']}")
    print("-" * 70)
    print("ALL PASS" if all_pass else "SOME FAILED")


if __name__ == "__main__":
    main()