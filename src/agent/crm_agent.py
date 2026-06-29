"""
CRM Digital FTE - Customer Success Agent
Phase 2: Specialization — OpenAI Agents SDK

Production-grade Customer Success Agent using OpenAI Agents SDK (Agent, Runner, @function_tool).
Runs on Groq LPU for fast inference via OpenAI-compatible API.
"""

import os
import json
import logging
import time
import asyncio
from typing import Optional, Tuple
from dotenv import load_dotenv

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(__file__))
from db.database import CRMDatabase

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")
BASE_URL = os.getenv("BASE_URL", "https://api.groq.com/openai/v1")

CHANNEL_LIMITS = {
    "email": {"max_words": 500, "max_chars": 3000},
    "whatsapp": {"max_words": 50, "max_chars": 300},
    "web_form": {"max_words": 300, "max_chars": 1800}
}

ESCALATION_KEYWORDS = {
    "legal_threat": ["lawyer", "attorney", "sue", "lawsuit", "legal", "court", "suing"],
    "pricing_inquiry": ["price", "cost", "how much", "pricing", "enterprise plan", "discount"],
    "refund_request": ["refund", "money back", "cancel subscription", "charge", "billing issue"],
    "human_requested": ["human", "real person", "agent", "manager", "supervisor"]
}

from workers.kafka_producer import publish_to_kafka, KafkaTopics

db = CRMDatabase()


def _record_prometheus(kind: str, **labels):
    """Best-effort Prometheus counter increment."""
    try:
        from api.main import (
            CHANNEL_MESSAGES, ESCALATION_COUNT, TICKETS_CREATED,
            CACHE_HITS, CACHE_MISSES
        )
        if kind == "channel_msg" and "channel" in labels:
            CHANNEL_MESSAGES.labels(channel=labels["channel"]).inc()
        elif kind == "escalation" and "reason" in labels:
            ESCALATION_COUNT.labels(reason=labels["reason"]).inc()
        elif kind == "ticket_created":
            TICKETS_CREATED.inc()
    except Exception:
        pass


from tools import (
    search_knowledge_base,
    create_ticket,
    get_customer_context,
    escalate_ticket,
    send_response,
    track_sentiment,
    AGENT_TOOLS,
)

from prompts import CUSTOMER_SUCCESS_SYSTEM_PROMPT

# =============================================================================
# Groq model setup via OpenAI Agents SDK
# =============================================================================

from agents import Agent, Runner
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from openai import AsyncOpenAI

groq_async_client = None
groq_model = None
ayesha_agent = None

if GROQ_API_KEY and GROQ_API_KEY != "your-groq-api-key-here":
    try:
        groq_async_client = AsyncOpenAI(
            api_key=GROQ_API_KEY,
            base_url=BASE_URL,
            timeout=10.0,
            max_retries=0,
        )
        groq_model = OpenAIChatCompletionsModel(
            model=MODEL_NAME,
            openai_client=groq_async_client
        )
        logger.info(f"Groq model '{MODEL_NAME}' initialized via Agents SDK")

        ayesha_agent = Agent(
            name="Ayesha",
            instructions=CUSTOMER_SUCCESS_SYSTEM_PROMPT,
            model=groq_model,
            tools=AGENT_TOOLS,
        )
        logger.info("Ayesha Agent initialized at module level with %s tools", len(AGENT_TOOLS))
    except Exception as e:
        logger.warning(f"Failed to initialize Groq/Ayesha Agent: {e}")
else:
    logger.warning("No GROQ_API_KEY set — agent will use fallback responses")


def check_escalation_triggers(message: str, sentiment_score: Optional[float] = None) -> Tuple[bool, Optional[str]]:
    """Check if message triggers escalation.

    Returns:
        (should_escalate: bool, reason: str or None)
    """
    message_lower = message.lower()

    for reason, keywords in ESCALATION_KEYWORDS.items():
        if any(keyword in message_lower for keyword in keywords):
            logger.info(f"Escalation trigger detected: {reason}")
            return True, reason

    if sentiment_score is not None and sentiment_score < 0.3:
        logger.info(f"Escalation trigger: negative sentiment ({sentiment_score})")
        return True, "negative_sentiment"

    return False, None


def detect_escalation(message: str) -> dict:
    """Wrapper for check_escalation_triggers that returns dict format for tests."""
    should_escalate, reason = check_escalation_triggers(message)

    escalation_messages = {
        "legal_threat": "I understand this is a serious matter. I'm escalating this to our specialist team.",
        "pricing_inquiry": "That's a great question about pricing. Our sales team can provide accurate information.",
        "refund_request": "I understand your concern about billing. Let me connect you with our billing team.",
        "human_requested": "I understand you'd like to speak with someone directly. I'm arranging for a team member.",
        "negative_sentiment": "I completely understand your frustration. Let me connect you with a specialist.",
        "no_relevant_info": "Let me connect you with a specialist who has deeper expertise.",
        "frustrated_customer": "I can see you've had a frustrating experience. Let me connect you with someone."
    }

    return {
        "is_escalation": should_escalate,
        "reason": reason,
        "message": escalation_messages.get(reason, "I'm connecting you with a specialist.") if should_escalate else ""
    }


def analyze_sentiment_simple(message: str) -> float:
    """Simple rule-based sentiment analysis."""
    positive_words = {
        "love", "great", "awesome", "excellent", "amazing", "wonderful",
        "fantastic", "perfect", "helpful", "thanks", "thank", "appreciate",
        "happy", "pleased", "satisfied", "good", "best"
    }

    negative_words = {
        "hate", "terrible", "awful", "horrible", "worst", "broken", "useless",
        "garbage", "waste", "frustrated", "angry", "disappointed", "issue",
        "problem", "error", "crash", "fail", "failed", "doesn't work",
        "ridiculous", "unacceptable"
    }

    words = set(message.lower().split())
    positive_count = len(words & positive_words)
    negative_count = len(words & negative_words)

    total = positive_count + negative_count
    if total == 0:
        return 0.5

    score = 0.5 + (positive_count - negative_count) / (total * 2)
    return max(0.0, min(1.0, score))


def _detect_islamic_greeting(message: str) -> bool:
    """Check if customer used an Islamic greeting."""
    greetings = [
        "assalam o alaikum", "assalam-o-alaikum", "assalamualaikum",
        "as-salamu alaykum", "walaikum assalam",
        "salam", "سلام", "السلام علیکم", "السلام عليكم",
        "salam alaikum", "salam-o-alaikum"
    ]
    msg_lower = message.lower().strip()
    return any(g in msg_lower for g in greetings)


def _detect_urdu(message: str) -> bool:
    """Check if message contains Urdu script characters or Roman Urdu keywords."""
    for c in message:
        cp = ord(c)
        if (0x0600 <= cp <= 0x06FF) or (0x0750 <= cp <= 0x077F) or (0xFB50 <= cp <= 0xFDFF) or (0xFE70 <= cp <= 0xFEFF):
            return True
    roman_urdu_keywords = ["mera", "tera", "kya", "kahan", "kahaan", "kaise", "kyun", "kyu", "nahi", "haan",
                           "bhai", "aap", "tum", "hum", "yeh", "woh", "hai", "ho", "hain", "tha", "the",
                           "thi", "apna", "tumhara", "karo", "karta", "karti", "kar", "raha", "rahi",
                           "sakta", "sakti", "chahiye", "hoga", "hogee", "aaya", "aayi", "aaye",
                           "jao", "ja", "jata", "jati", "aa", "ao", "lo", "do", "de", "le", "se", "ko"]
    words = message.lower().split()
    roman_count = sum(1 for w in words if w.strip("?.,!;:") in roman_urdu_keywords)
    return roman_count >= 2


def _extract_agent_metadata(items: list) -> dict:
    """Parse Agent SDK conversation items for tool call results (ticket_id, customer_id, escalation)."""
    meta: dict = {
        "ticket_id": None,
        "customer_id": None,
        "escalated": False,
        "escalation_reason": None,
        "tool_calls_count": 0,
        "send_count": 0,
    }
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "function_call":
            meta["tool_calls_count"] += 1
        elif item.get("type") == "function_call_output":
            try:
                output = json.loads(item.get("output", "{}"))
                # ticket_id from create_ticket
                if output.get("ticket_id") and not meta["ticket_id"]:
                    meta["ticket_id"] = output["ticket_id"]
                # customer_id from create_ticket or get_customer_context
                cid = output.get("customer_id") or output.get("customer", {}).get("id")
                if cid and not meta["customer_id"]:
                    meta["customer_id"] = cid
                # escalation from escalate_ticket
                if output.get("escalated") and output.get("reason"):
                    meta["escalated"] = True
                    meta["escalation_reason"] = output.get("reason")
                # count send_response calls
                if output.get("delivery_status") == "sent":
                    meta["send_count"] += 1
            except (json.JSONDecodeError, TypeError):
                pass
    return meta


def process_message(customer_email: str, message: str, channel: str,
                    customer_name: Optional[str] = None) -> dict:
    """
    Process a customer message through the complete agent flow.
    Uses OpenAI Agents SDK (Agent, Runner, @function_tool) to orchestrate ALL tool calls automatically.

    Args:
        customer_email: Customer email address
        message: Customer message
        channel: Source channel (email, whatsapp, web_form)
        customer_name: Optional customer name

    Returns:
        dict with response, ticket_id, escalated, escalation_reason,
        tool_calls_count, response_time_ms
    """
    start_time = time.time()
    logger.info(f"Processing {channel} message from {customer_email}")

    if groq_model is None or ayesha_agent is None:
        logger.error("Ayesha Agent not initialized: check GROQ_API_KEY in .env")
        return {
            "response": "Service unavailable — Groq API not configured. Please set GROQ_API_KEY in .env",
            "ticket_id": None,
            "escalated": False,
            "escalation_reason": None,
            "tool_calls_count": 0,
            "response_time_ms": (time.time() - start_time) * 1000,
            "error": "Groq model not initialized"
        }

    try:
        # --- Build dynamic system prompt additions ---
        prompt_additions = ""
        if _detect_islamic_greeting(message):
            prompt_additions += "\n\n## Current Interaction\nCustomer opened with an Islamic greeting. You MUST begin your response with 'Assalam o alaikum!' (with exclamation mark)."
        if _detect_urdu(message):
            prompt_additions += "\n\n## Language\nCustomer is writing in Urdu or mixing Urdu with English. Respond naturally in the same style."
        name_ask_patterns = ["ap ka naam", "aap ka naam", "your name", "naam kya hai", "name kya hai", "kaun ho", "kon ho", "who are you"]
        if any(kw in message.lower() for kw in name_ask_patterns):
            prompt_additions += "\n\n## Name Question\nThe customer asked for your name. Introduce yourself as Ayesha, your role as a customer support agent, and ask for their name warmly."
        name_preference_patterns = ["ke naam se bulao", "naam se bulao", "call me", "bulao", "mera naam", "mujhe ... bulao"]
        if any(kw in message.lower() for kw in name_preference_patterns):
            prompt_additions += "\n\n## Name Preference\nThe customer wants you to address them by a specific name or preference. Ackowledge this warmly (e.g., 'Bilkul!') and use their requested name going forward."
        order_keywords = ["order", "ticket", "kahan", "kahaan", "status", "track", "delivery", "shipping", "tracking"]
        if any(kw in message.lower() for kw in order_keywords):
            prompt_additions += "\n\n## Order Status\nCustomer is asking about their order/ticket status. Look up their account with get_customer_context and reference their ticket."

        instructions = CUSTOMER_SUCCESS_SYSTEM_PROMPT + prompt_additions

        # --- Create Agent with dynamic instructions each call ---
        logger.info("[AGENT] Creating Agent with %s tools", len(AGENT_TOOLS))
        agent = Agent(
            name="Ayesha",
            instructions=instructions,
            model=groq_model,
            tools=AGENT_TOOLS,
        )

        input_text = (
            f"Customer: {customer_name or 'Unknown'} ({customer_email})\n"
            f"Channel: {channel}\n\n"
            f"Customer message: {message}"
        )

        logger.info("[RUNNER] Calling Runner.run() (async via explicit event loop) — SDK orchestrates all tool calls")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            run_result = loop.run_until_complete(
                Runner.run(agent, input=input_text, max_turns=15)
            )
        finally:
            loop.close()
        logger.info("[RUNNER] Runner.run() completed")

        response = run_result.final_output_as(str) or ""

        # --- Parse tool call metadata from conversation history ---
        items = run_result.to_input_list()
        meta = _extract_agent_metadata(items)
        logger.info("[META] ticket_id=%s, customer_id=%s, tool_calls=%s, escalated=%s",
                    meta["ticket_id"], meta["customer_id"], meta["tool_calls_count"], meta["escalated"])

        response_time = (time.time() - start_time) * 1000

        # ── Record channel metrics ──
        _record_prometheus("channel_msg", channel=channel)

        if meta["ticket_id"]:
            _record_prometheus("ticket_created")
            publish_to_kafka(KafkaTopics.TICKET_CREATED, {
                "event_type": "ticket_created",
                "ticket_id": meta["ticket_id"],
                "customer_email": customer_email,
                "channel": channel,
            })

        if meta["escalated"]:
            _record_prometheus("escalation", reason=meta["escalation_reason"])
            publish_to_kafka(KafkaTopics.METRICS_EVENTS, {
                "event_type": "escalation",
                "channel": channel,
                "reason": meta["escalation_reason"],
                "customer_email": customer_email,
                "response_time_ms": response_time,
            })
            return {
                "response": response,
                "ticket_id": meta["ticket_id"],
                "escalated": True,
                "escalation_reason": meta["escalation_reason"],
                "tool_calls_count": meta["tool_calls_count"],
                "response_time_ms": response_time,
            }

        if response and meta["ticket_id"]:
            return {
                "response": response,
                "ticket_id": meta["ticket_id"],
                "escalated": False,
                "escalation_reason": None,
                "tool_calls_count": meta["tool_calls_count"],
                "response_time_ms": response_time,
                "char_count": len(response),
            }

        # --- Fallback if Agent didn't produce a valid response ---
        fallback_msg = "Our AI is busy, a human will assist you shortly."
        if meta["ticket_id"]:
            try:
                send_response(
                    ticket_id=meta["ticket_id"],
                    response=fallback_msg,
                    channel=channel
                )
            except Exception as e:
                logger.warning(f"Fallback send_response failed: {e}")

        return {
            "response": fallback_msg,
            "ticket_id": meta["ticket_id"],
            "escalated": meta["escalated"],
            "escalation_reason": meta["escalation_reason"],
            "tool_calls_count": meta["tool_calls_count"],
            "response_time_ms": response_time,
        }

    except Exception as e:
        logger.error(f"Agent processing error: {e}")
        response_time = (time.time() - start_time) * 1000
        return {
            "response": "Our AI is busy, a human will assist you shortly.",
            "ticket_id": None,
            "escalated": False,
            "escalation_reason": None,
            "tool_calls_count": 0,
            "response_time_ms": response_time,
            "error": str(e)
        }


if __name__ == "__main__":
    if groq_model is None:
        logger.error("Cannot run agent: Groq model not initialized. Check GROQ_API_KEY in .env")
        sys.exit(1)
    result = process_message(
        customer_email="john.doe@techcorp.com",
        message="How do I add team members to my workspace?",
        channel="email",
        customer_name="John Doe"
    )
    print(json.dumps(result, indent=2))
