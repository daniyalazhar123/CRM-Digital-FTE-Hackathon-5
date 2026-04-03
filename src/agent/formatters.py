"""
CRM Digital FTE - Channel Formatters
Phase 2: Specialization

Channel-specific response formatting functions.
Ensures responses follow channel-appropriate style and length constraints.
"""

from typing import Dict, Tuple

# Channel response limits
CHANNEL_LIMITS: Dict[str, Dict[str, int]] = {
    "email": {"max_words": 500, "max_chars": 3000},
    "whatsapp": {"max_words": 50, "max_chars": 300},
    "web_form": {"max_words": 300, "max_chars": 1800}
}


def format_email_response(response: str, customer_name: str = None, ticket_id: str = None) -> str:
    """
    Format response for email channel.
    
    Args:
        response: Base response text
        customer_name: Optional customer name for greeting
        ticket_id: Optional ticket ID for reference
    
    Returns:
        Formatted email response with greeting, body, and signature
    """
    # Add greeting if not present
    greeting = f"Dear {customer_name}," if customer_name else "Hello,"
    
    # Add ticket reference if provided
    ticket_ref = f"\n\nTicket ID: {ticket_id}" if ticket_id else ""
    
    # Add signature
    signature = "\n\nBest regards,\nTechCorp Support Team"
    
    # Combine all parts
    formatted = f"{greeting}\n\n{response}{ticket_ref}{signature}"
    
    # Enforce length limits
    formatted = _truncate_to_word_limit(formatted, CHANNEL_LIMITS["email"]["max_words"])
    formatted = _truncate_to_char_limit(formatted, CHANNEL_LIMITS["email"]["max_chars"])
    
    return formatted


def format_whatsapp_response(response: str) -> str:
    """
    Format response for WhatsApp channel.
    
    Args:
        response: Base response text
    
    Returns:
        Concise WhatsApp-friendly response (max 300 chars)
    """
    # Remove formal language
    response = response.replace("Dear", "").replace("Best regards", "").replace("Sincerely", "")
    response = response.replace("\nTechCorp Support Team", "")
    
    # Make conversational
    if len(response) > CHANNEL_LIMITS["whatsapp"]["max_chars"]:
        # Truncate and add ellipsis
        response = response[:CHANNEL_LIMITS["whatsapp"]["max_chars"] - 3] + "..."
    
    # Ensure under 300 chars
    response = _truncate_to_char_limit(response, CHANNEL_LIMITS["whatsapp"]["max_chars"])
    
    return response.strip()


def format_web_form_response(response: str, ticket_id: str = None) -> str:
    """
    Format response for web form channel.
    
    Args:
        response: Base response text
        ticket_id: Optional ticket ID for reference
    
    Returns:
        Structured web form response with ticket reference
    """
    # Add ticket reference if provided
    if ticket_id:
        response = f"**Ticket ID: {ticket_id}**\n\n{response}"
    
    # Enforce length limits
    response = _truncate_to_word_limit(response, CHANNEL_LIMITS["web_form"]["max_words"])
    response = _truncate_to_char_limit(response, CHANNEL_LIMITS["web_form"]["max_chars"])
    
    return response


def format_response(response: str, channel: str, customer_name: str = None, ticket_id: str = None) -> str:
    """
    Format response based on channel type.
    
    Args:
        response: Base response text
        channel: Channel type (email, whatsapp, web_form)
        customer_name: Optional customer name
        ticket_id: Optional ticket ID
    
    Returns:
        Channel-appropriate formatted response
    """
    if channel == "email":
        return format_email_response(response, customer_name, ticket_id)
    elif channel == "whatsapp":
        return format_whatsapp_response(response)
    elif channel == "web_form":
        return format_web_form_response(response, ticket_id)
    else:
        # Default: return as-is with length check
        return _truncate_to_char_limit(response, CHANNEL_LIMITS["email"]["max_chars"])


def validate_response_length(response: str, channel: str) -> Tuple[bool, str]:
    """
    Validate response meets channel length requirements.
    
    Args:
        response: Response text to validate
        channel: Channel type
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    limits = CHANNEL_LIMITS.get(channel, CHANNEL_LIMITS["email"])
    
    word_count = len(response.split())
    char_count = len(response)
    
    if word_count > limits["max_words"]:
        return False, f"Response too long: {word_count} words (max {limits['max_words']})"
    
    if char_count > limits["max_chars"]:
        return False, f"Response too long: {char_count} chars (max {limits['max_chars']})"
    
    return True, ""


def _truncate_to_word_limit(text: str, max_words: int) -> str:
    """Truncate text to maximum word count."""
    words = text.split()
    if len(words) <= max_words:
        return text
    
    return " ".join(words[:max_words]) + "..."


def _truncate_to_char_limit(text: str, max_chars: int) -> str:
    """Truncate text to maximum character count."""
    if len(text) <= max_chars:
        return text
    
    return text[:max_chars - 3] + "..."
