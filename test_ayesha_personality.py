"""
Test the updated Ayesha CRM Agent personality.
"""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.dirname(__file__))
os.environ["PYTHONIOENCODING"] = "utf-8"

from agent.crm_agent import process_message, _detect_islamic_greeting, _detect_urdu

# Test detection helpers
print("=" * 60)
print("GREETING & LANGUAGE DETECTION TESTS")
print("=" * 60)

test_cases = [
    ("Assalam o alaikum mera order kahan hai", True, True),     # Islamic greeting + Roman Urdu words
    ("Bhai ap ka naam kya hai", False, True),                   # Roman Urdu words
    ("Ayesha aaj se ap mujhe Ayesha ke naam se bulao", False, True),  # Roman Urdu words
    ("Hello how are you", False, False),                        # Pure English
    ("salam", True, False),                                     # Islamic greeting, no Urdu
]

for msg, exp_greet, exp_urdu in test_cases:
    greet = _detect_islamic_greeting(msg)
    urdu = _detect_urdu(msg)
    status = "OK" if (greet == exp_greet and urdu == exp_urdu) else "FAIL"
    print(f"[{status}] greet={greet} urdu={urdu} | {msg[:50]}")

# Test process_message with the 3 sample messages
print("\n" + "=" * 60)
print("CRM AGENT RESPONSE TESTS (with Ayesha personality)")
print("=" * 60)

test_queries = [
    ("Assalam o alaikum mera order kahan hai", "test_ayesha1@test.com"),
    ("Bhai ap ka naam kya hai", "test_ayesha2@test.com"),
    ("Ayesha aaj se ap mujhe Ayesha ke naam se bulao", "test_ayesha3@test.com"),
]

for msg, email in test_queries:
    print(f"\n{'─' * 50}")
    print(f"CUSTOMER: {msg}")
    print(f"{'─' * 50}")
    try:
        result = process_message(
            customer_email=email,
            message=msg,
            channel="whatsapp",
            customer_name="Customer"
        )
        response_text = result['response']
        print(f"AYESHA:  {response_text}")
        print(f"Ticket:  {result['ticket_id']}")
        print(f"Time:    {result['response_time_ms']:.0f}ms")
    except Exception as e:
        print(f"ERROR: {e}")

print("\n" + "=" * 60)
print("DONE")
print("=" * 60)
