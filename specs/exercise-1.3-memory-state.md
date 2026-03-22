# Exercise 1.3 - Memory & State Management

**Status:** ✅ COMPLETE  
**Date:** March 22, 2026  
**File:** `src/agent/prototype_agent.py`

---

## Overview

Enhanced the prototype agent with comprehensive memory and state management capabilities. The agent now remembers customers across channels, tracks sentiment trends, monitors topics discussed, and maintains conversation history.

---

## Features Implemented

### 1. Conversation Memory ✅

**Implementation:** `InMemoryStore.conversation_memory`

- Stores last **10 messages per customer** (by customer_id)
- Messages include: role, content, channel, timestamp, ticket_id
- Automatically pruned to keep only recent messages

**Code:**
```python
def add_message(self, ticket_id: str, role: str, content: str, channel: str):
    # ... add to ticket ...
    
    # Update conversation memory (last 10 messages per customer)
    customer_id = self.tickets[ticket_id]["customer_id"]
    if customer_id in self.conversation_memory:
        self.conversation_memory[customer_id].append({...})
        # Keep only last 10 messages
        self.conversation_memory[customer_id] = self.conversation_memory[customer_id][-10:]
```

**Test Result:**
```
Sarah's Conversation Memory (4 messages):
  1. [email] customer: Hi, I'm the admin of our team workspace...
  2. [email] agent: Dear Valued Customer, Thank you for reaching out...
  3. [whatsapp] customer: Thanks! Also how do I remove someone...
  4. [whatsapp] agent: based on our documentation about...
```

---

### 2. Sentiment Trend Tracking ✅

**Implementation:** `InMemoryStore.customer_state["sentiment_history"]`

- Tracks sentiment score for every interaction
- Calculates trend: **improving**, **stable**, or **declining**
- Compares recent avg vs older avg to determine direction

**Code:**
```python
def get_sentiment_trend(self, customer_id: str) -> dict:
    history = state["sentiment_history"]
    mid = len(history) // 2
    older_avg = sum(s["score"] for s in history[:mid]) / mid
    recent_avg = sum(s["score"] for s in history[mid:]) / (len(history) - mid)
    
    diff = recent_avg - older_avg
    if diff > 0.1: trend = "improving"
    elif diff < -0.1: trend = "declining"
    else: trend = "stable"
```

**Test Result:**
```
Sentiment Trend Analysis:
  Average Sentiment: 0.38
  Sentiment Trend: declining
  Frustration Flag: False
```

---

### 3. Cross-Channel Continuity ✅

**Implementation:** `InMemoryStore.customers_by_email` + `customers_by_phone` + `link_phone_to_customer()`

- Customers identified by email OR phone
- Phone numbers can be linked to existing email-based customers
- Agent detects returning customers across channels

**Code:**
```python
def get_cross_channel_context(self, customer_id: str, current_channel: str) -> dict:
    channels_used = state["channels_used"]
    other_channels = [c for c in channels_used if c != current_channel]
    
    return {
        "is_returning": len(channels_used) > 0,
        "prior_channels": list(other_channels),
        "total_interactions": state["total_tickets"]
    }
```

**Test Result:**
```
Processing whatsapp message from +14155551234
Customer: Sarah Johnson (Pro plan)
RETURNING CUSTOMER via whatsapp, previously used: ['email']
Customer Stats: 1 tickets, avg sentiment: 0.5
```

---

### 4. State Tracking ✅

**Implementation:** `InMemoryStore.customer_state`

Tracks per customer:
- `total_tickets` - All-time ticket count
- `open_tickets` - Currently open
- `resolved_tickets` - Successfully closed
- `escalated_tickets` - Required human intervention
- `channels_used` - Set of channels customer has used
- `last_interaction` - Timestamp of last contact
- `frustration_flag` - True if 3+ negative interactions

**Code:**
```python
self.customer_state[customer_id] = {
    "total_tickets": 0,
    "open_tickets": 0,
    "resolved_tickets": 0,
    "escalated_tickets": 0,
    "sentiment_history": [],
    "channels_used": set(),
    "last_interaction": None,
    "frustration_flag": False
}
```

**Test Result:**
```
sarah.johnson@techstartup.io:
  Total Tickets: 2
  Open Tickets: 2
  Escalated Tickets: 0
  Channels Used: ['email', 'whatsapp']
  Preferred Channel: email
```

---

### 5. Topic Tracking ✅

**Implementation:** `InMemoryStore.customer_topics` + `_extract_topics()`

- Extracts topics from customer messages using keyword matching
- Tracks topics discussed per customer
- Agent can acknowledge prior discussions on same topic

**Topic Categories:**
```python
topic_keywords = {
    "permissions": ["permission", "access", "role", "admin"],
    "integration": ["integration", "connect", "sync", "github", "slack"],
    "pricing": ["price", "cost", "plan", "upgrade", "billing"],
    "bug": ["bug", "error", "crash", "broken", "not working"],
    "feature": ["feature", "how to", "can i", "is there"]
}
```

**Test Result:**
```
Topics Discussed: ['permissions', 'feature']
```

---

### 6. Customer Statistics Method ✅

**Implementation:** `InMemoryStore.get_customer_stats(customer_id)`

Returns comprehensive customer profile:
```python
{
    "total_tickets": 2,
    "open_tickets": 2,
    "resolved_tickets": 0,
    "escalated_tickets": 0,
    "avg_sentiment": 0.75,
    "sentiment_trend": "improving",
    "frustration_flag": False,
    "preferred_channel": "email",
    "channels_used": ["email", "whatsapp"],
    "last_interaction": "2026-03-22T12:00:00Z",
    "topics_discussed": ["permissions", "feature"]
}
```

---

## Test Results Summary

### Test 1: Cross-Channel Continuity
- **Customer:** Sarah Johnson
- **Scenario:** Emailed about permissions, then messaged on WhatsApp
- **Result:** ✅ Agent recognized Sarah as returning customer, showed prior channel usage

### Test 2: Sentiment Trend Tracking
- **Customer:** Mike Chen
- **Scenario:** 4 interactions with declining sentiment
- **Result:** ✅ Detected "declining" trend, escalated on 4th interaction (negative sentiment)

### Test 3: Topic Tracking
- **Customer:** Carlos Rivera
- **Scenario:** Asked about Kanban twice
- **Result:** ✅ Topics tracked, agent acknowledges prior discussions

### Test 4: Customer Statistics
- **Result:** ✅ `get_customer_stats()` returns complete profile for all customers

### Test 5: Conversation Memory
- **Result:** ✅ Last 10 messages retained per customer, accessible via `get_customer_history()`

---

## Overall Metrics

| Metric | Value |
|--------|-------|
| **Total Interactions** | 9 |
| **Escalated** | 1 (11.1%) |
| **Handled by AI** | 8 (88.9%) |
| **Customers Tracked** | 3 |
| **Channels Used** | 3 (email, whatsapp, web_form) |

---

## Memory Features Verified

| Feature | Status |
|---------|--------|
| Cross-channel continuity | ✅ |
| Sentiment trend tracking | ✅ |
| Frustration flag (3+ negative) | ✅ |
| Topic tracking | ✅ |
| Customer statistics | ✅ |
| Conversation memory (10 msgs) | ✅ |

---

## Code Changes Summary

### New Methods Added to `InMemoryStore`:
1. `_now()` - Timestamp helper
2. `link_phone_to_customer()` - Cross-channel linking
3. `link_email_to_customer()` - Cross-channel linking
4. `update_sentiment()` - Track sentiment history
5. `get_sentiment_trend()` - Analyze trend direction
6. `get_cross_channel_context()` - Multi-channel awareness
7. `track_topic()` - Record topics discussed
8. `get_topics_discussed()` - Retrieve topic history
9. `get_customer_stats()` - Comprehensive statistics
10. `get_customer_full_profile()` - Debug/profile view

### Enhanced Methods:
1. `get_or_create_customer()` - Now initializes state tracking
2. `create_ticket()` - Now updates customer state
3. `add_message()` - Now updates conversation memory
4. `escalate_ticket()` - Now updates escalated count

### Enhanced `CustomerSuccessAgent`:
1. `process_message()` - Now uses memory features, cross-channel context
2. `_generate_answer()` - Now topic-aware (acknowledges prior discussions)
3. `_handle_escalation()` - Now personalized with customer name
4. `get_customer_full_profile()` - New debug method

---

## Next Steps

**Ready for Exercise 1.4 - Build the MCP Server**

The memory foundation is complete. Next we will:
1. Define MCP tools for external integration
2. Expose agent capabilities via MCP protocol
3. Implement tool handlers for knowledge search, ticket creation, etc.

---

*Exercise 1.3 Complete*
