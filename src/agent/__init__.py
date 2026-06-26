"""
CRM Digital FTE - Agent Package

Customer Success Agent with OpenAI Agents SDK and Groq backend.
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(__file__))

from crm_agent import process_message, process_message_async, detect_escalation, analyze_sentiment_simple
from tools import (
    search_knowledge_base,
    create_ticket,
    get_customer_context,
    escalate_ticket,
    send_response,
    track_sentiment
)
