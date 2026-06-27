"""
CRM Digital FTE - Customer Success Agent
Phase 2: Specialization — Step 3

Production-grade Customer Success Agent built with OpenAI Agents SDK.
Runs on Groq LPU for fast inference via OpenAI-compatible API.
"""

import os
import json
import logging
import time
import asyncio
from datetime import datetime, timezone
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv

from agents import Agent, Runner, set_default_openai_client

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

try:
    if GROQ_API_KEY and GROQ_API_KEY != "your-groq-api-key-here":
        groq_client = OpenAI(
            api_key=GROQ_API_KEY,
            base_url=BASE_URL
        )
        set_default_openai_client(groq_client)
    else:
        groq_client = None
except Exception as e:
    logger.warning(f"Failed to initialize Groq client: {e}")
    groq_client = None

db = CRMDatabase()

from tools import (
    search_knowledge_base,
    create_ticket,
    get_customer_context,
    escalate_ticket,
    send_response,
    track_sentiment,
    agent_tools
)

from prompts import CUSTOMER_SUCCESS_SYSTEM_PROMPT

customer_success_agent = Agent(
    name="CustomerSuccessFTE",
    instructions=CUSTOMER_SUCCESS_SYSTEM_PROMPT,
    model=MODEL_NAME,
    tools=agent_tools
)


def check_escalation_triggers(message: str, sentiment_score: Optional[float] = None) -> tuple:
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


def process_message(customer_email: str, message: str, channel: str,
                    customer_name: Optional[str] = None) -> dict:
    """
    Process a customer message through the complete agent flow.
    Uses OpenAI Agents SDK Runner for LLM interaction and tool orchestration.
    Backward-compatible sync wrapper.

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
    tool_calls_count = 0
    ticket_id = None
    customer_id = None
    sentiment_score = 0.5
    should_escalate = False
    escalation_reason = None

    logger.info(f"Processing {channel} message from {customer_email}")

    try:
        context_result = get_customer_context(customer_email)
        context = json.loads(context_result)
        tool_calls_count += 1

        customer_id = context.get('customer', {}).get('id')
        is_returning = context.get('is_returning_customer', False)

        logger.info(f"Customer: {customer_id}, Returning: {is_returning}")

        ticket_result = create_ticket(
            customer_email=customer_email,
            message=message,
            channel=channel,
            priority="medium",
            customer_name=customer_name
        )
        ticket = json.loads(ticket_result)
        tool_calls_count += 1

        ticket_id = ticket.get('ticket_id')
        logger.info(f"Created ticket: {ticket_id}")

        sentiment_score = analyze_sentiment_simple(message)
        sentiment_result = track_sentiment(
            customer_id=customer_id,
            sentiment_score=sentiment_score
        )
        sentiment = json.loads(sentiment_result)
        tool_calls_count += 1

        should_escalate, escalation_reason = check_escalation_triggers(
            message, sentiment_score
        )

        if sentiment.get('frustration_flag') and not should_escalate:
            should_escalate = True
            escalation_reason = "frustrated_customer"

        if should_escalate:
            logger.info(f"Escalating ticket: {escalation_reason}")

            escalate_result = escalate_ticket(
                ticket_id=ticket_id,
                reason=escalation_reason,
                notes=f"Auto-escalated from {channel}. Sentiment: {sentiment_score}"
            )
            escalation = json.loads(escalate_result)
            tool_calls_count += 1

            response = escalation.get('message',
                "I'm connecting you with a specialist who can better assist you.")

            try:
                send_response(
                    ticket_id=ticket_id,
                    response=response,
                    channel=channel
                )
                tool_calls_count += 1
            except Exception as resp_error:
                logger.warning(f"Failed to send response: {resp_error}")

            response_time = (time.time() - start_time) * 1000

            return {
                "response": response,
                "ticket_id": ticket_id,
                "escalated": True,
                "escalation_reason": escalation_reason,
                "tool_calls_count": tool_calls_count,
                "response_time_ms": response_time
            }

        search_result = search_knowledge_base(query=message, max_results=5)
        search = json.loads(search_result)
        tool_calls_count += 1

        kb_context = "\n\n".join([
            f"**{r.get('title', 'Documentation')}**:\n{r.get('content', r.get('results', 'Information not found.'))}"
            for r in search['results'][:3]
        ]) if search.get('results') and len(search['results']) > 0 else "No relevant documentation found."

        try:
            token_limit = 300
            if channel == 'whatsapp':
                token_limit = 150

            groq_response = groq_client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": CUSTOMER_SUCCESS_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Context:\n{kb_context}\n\nCustomer question: {message}"}
                ],
                max_tokens=token_limit,
                temperature=0.7
            )

            if groq_response and groq_response.choices:
                response = groq_response.choices[0].message.content
            else:
                response = None
            tool_calls_count += 1
        except Exception as llm_error:
            logger.warning(f"Groq LLM error ({type(llm_error).__name__}): {llm_error}")
            response = None

        if response:
            try:
                response_result = send_response(
                    ticket_id=ticket_id,
                    response=response,
                    channel=channel
                )
                response_data = json.loads(response_result)
                tool_calls_count += 1
            except Exception as resp_error:
                logger.warning(f"Failed to send response: {resp_error}")
                response_data = {}

            response = response_data.get('response', response)

            response_time = (time.time() - start_time) * 1000

            return {
                "response": response,
                "ticket_id": ticket_id,
                "escalated": False,
                "escalation_reason": None,
                "tool_calls_count": tool_calls_count,
                "response_time_ms": response_time,
                "char_count": response_data.get('char_count', len(response)),
                "truncated": response_data.get('truncated', False)
            }

        fallback_msg = "Our AI is busy, a human will assist you shortly."
        try:
            send_response(
                ticket_id=ticket_id,
                response=fallback_msg,
                channel=channel
            )
            tool_calls_count += 1
        except Exception as resp_error:
            logger.warning(f"Failed to send fallback response: {resp_error}")

        response_time = (time.time() - start_time) * 1000

        return {
            "response": fallback_msg,
            "ticket_id": ticket_id,
            "escalated": False,
            "escalation_reason": None,
            "tool_calls_count": tool_calls_count,
            "response_time_ms": response_time
        }

    except Exception as e:
        logger.error(f"Agent processing error: {e}")
        response_time = (time.time() - start_time) * 1000

        return {
            "response": "Our AI is busy, a human will assist you shortly.",
            "ticket_id": ticket_id,
            "escalated": should_escalate,
            "escalation_reason": escalation_reason if should_escalate else None,
            "tool_calls_count": tool_calls_count,
            "response_time_ms": response_time,
            "error": str(e)
        }


async def process_message_async(customer_email: str, message: str, channel: str,
                                 customer_name: Optional[str] = None) -> dict:
    """Process message using OpenAI Agents SDK Runner."""
    start_time = time.time()
    try:
        agent_input = (
            f"Channel: {channel}\n"
            f"Customer email: {customer_email}\n"
            f"Customer name: {customer_name or 'N/A'}\n\n"
            f"Message: {message}"
        )
        result = await Runner.run(customer_success_agent, input=agent_input)

        response_time = (time.time() - start_time) * 1000
        return {
            "response": result.final_output,
            "ticket_id": None,
            "escalated": False,
            "escalation_reason": None,
            "tool_calls_count": len(result.raw_responses),
            "response_time_ms": response_time
        }
    except Exception as e:
        logger.error(f"Agent SDK processing error: {e}")
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
    import asyncio
    asyncio.run(process_message_async(
        customer_email="john.doe@techcorp.com",
        message="How do I add team members to my workspace?",
        channel="email",
        customer_name="John Doe"
    ))
