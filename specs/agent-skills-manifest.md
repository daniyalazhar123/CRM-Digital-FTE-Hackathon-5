# Agent Skills Manifest

**Agent:** Customer Success FTE  
**Version:** 1.0-incubation  
**Date:** March 22, 2026  
**Status:** ✅ COMPLETE

---

## Overview

This manifest defines 6 formal skills for the Customer Success FTE agent. Each skill represents a reusable capability that the agent can invoke to handle specific customer service scenarios.

---

## Channel Constraints

All skills must adhere to these channel-specific constraints:

| Channel | Max Words | Max Characters | Style | Greeting | Signature |
|---------|-----------|----------------|-------|----------|-----------|
| **Email** | 500 | 3000 | Formal | Required | Required |
| **WhatsApp** | 50 | 300 (pref: 160) | Casual | Optional | Optional |
| **Web Form** | 300 | 1800 | Semi-formal | Required | Optional |

---

## Hard Constraints

These rules MUST never be violated:

| ID | Constraint | Action Required | Severity |
|----|------------|-----------------|----------|
| HC-001 | NEVER discuss pricing or provide cost estimates | Escalate with reason `pricing_inquiry` | Critical |
| HC-002 | NEVER promise features not in documentation | Use only documented information | Critical |
| HC-003 | NEVER process refunds or billing adjustments | Escalate with reason `refund_request` | Critical |
| HC-004 | NEVER share internal processes beyond public docs | Redirect to public documentation | High |
| HC-005 | NEVER respond without using send_response tool | Always call send_response | High |
| HC-006 | NEVER exceed response length limits per channel | Truncate or summarize | Medium |
| HC-007 | ALWAYS create ticket before responding | Call create_ticket first | High |
| HC-008 | ALWAYS check customer history across channels | Call get_customer_history | Medium |
| HC-009 | ALWAYS check sentiment before closing | Verify sentiment >= 0.4 | Medium |
| HC-010 | ALWAYS use channel-appropriate tone | Apply channel_constraints | Medium |

---

## Escalation Triggers

| ID | Trigger | Keywords/Conditions | Action |
|----|---------|---------------------|--------|
| ET-001 | legal_threat | "lawyer", "attorney", "sue", "lawsuit" | Escalate immediately |
| ET-002 | pricing_inquiry | "how much", "pricing", "cost", "discount" | Escalate to sales |
| ET-003 | refund_request | "refund", "money back", "cancel" | Escalate to billing |
| ET-004 | human_requested | "human", "manager", "agent" | Escalate to human |
| ET-005 | negative_sentiment | sentiment_score < 0.3 | Escalate with empathy |
| ET-006 | no_relevant_info | 2+ failed KB searches | Escalate to expert |
| ET-007 | frustrated_customer | frustration_flag = true | Escalate for attention |

---

## Skills

### SKILL-001: answer_product_question

**Display Name:** Answer Product Question

**Description:** Handle customer questions about product features, how-to guidance, and technical information.

**Trigger:** Customer asks a how-to or feature question

**Tools Used:**
- `search_knowledge_base`
- `send_response`

**Input:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| query | string | Yes | Customer's question |
| channel | string | Yes | email, whatsapp, or web_form |
| customer_id | string | Yes | Customer identifier |
| ticket_id | string | Yes | Current ticket ID |

**Output:**
| Field | Type | Description |
|-------|------|-------------|
| success | boolean | Whether answer was generated |
| response | string | Formatted response |
| sources | array | KB articles used |
| char_count | integer | Response character count |

**Workflow:**
1. Validate constraints (not pricing/legal)
2. Call `search_knowledge_base` with query
3. If results found (score > 5), proceed
4. Generate answer from top result
5. Call `send_response` with formatted answer

**Success Criteria:**
- Response answers question accurately
- Uses only KB information
- Adheres to channel constraints
- Customer sentiment >= 0.4 after response

**Fallback:** If no KB articles found → escalate with reason `no_relevant_info`

---

### SKILL-002: create_support_ticket

**Display Name:** Create Support Ticket

**Description:** Log every customer interaction as a ticket for tracking and continuity.

**Trigger:** Every new customer interaction (REQUIRED as first step)

**Tools Used:**
- `create_ticket`

**Input:**
| Parameter | Type | Required | Default |
|-----------|------|----------|---------|
| customer_id | string | Yes | - |
| message | string | Yes | - |
| channel | string | Yes | - |
| priority | string | No | medium |
| customer_name | string | No | - |

**Output:**
| Field | Type | Description |
|-------|------|-------------|
| ticket_id | string | Generated ID (e.g., TKT-00001) |
| customer_id | string | Internal customer ID |
| status | string | Always "open" |
| created_at | ISO8601 | Creation timestamp |

**Workflow:**
1. Extract metadata (customer_id, message, channel)
2. Determine priority (high if sentiment < 0.4)
3. Call `create_ticket`
4. Store ticket_id for subsequent operations

**Success Criteria:**
- Unique ticket ID generated
- Customer linked to ticket
- Channel metadata recorded
- Message stored in history

**Notes:** This skill MUST execute before any other skill for every new interaction.

---

### SKILL-003: escalate_to_human

**Display Name:** Escalate to Human

**Description:** Hand off complex, sensitive, or restricted issues to human support agents.

**Trigger:** ANY of:
- Legal threat keywords detected
- Pricing/refund inquiry
- Human explicitly requested
- Sentiment < 0.3
- Frustration flag = true

**Tools Used:**
- `escalate_ticket`
- `send_response`

**Input:**
| Parameter | Type | Required | Options |
|-----------|------|----------|---------|
| ticket_id | string | Yes | - |
| reason | string | Yes | pricing_inquiry, refund_request, legal_threat, negative_sentiment, human_requested, no_relevant_info, frustrated_customer, technical_issue |
| notes | string | No | Additional context |
| urgency | string | No | low, normal, high, critical |

**Output:**
| Field | Type | Description |
|-------|------|-------------|
| escalation_id | string | Generated ID (e.g., ESC-FF56A199) |
| ticket_id | string | Original ticket ID |
| status | string | Always "escalated" |
| escalated_at | ISO8601 | Escalation timestamp |

**Workflow:**
1. Detect escalation reason from trigger
2. Gather context (history, stats, prior tickets)
3. Call `escalate_ticket`
4. Notify customer with appropriate message

**Escalation Message Templates:**

| Reason | Message |
|--------|---------|
| pricing_inquiry | "That's a great question about pricing. Our sales team can provide accurate information tailored to your needs." |
| refund_request | "I understand your concern about billing. Let me connect you with our billing team." |
| legal_threat | "I understand this is a serious matter. I'm escalating this to our specialist team." |
| negative_sentiment | "I completely understand your frustration. Let me connect you with a specialist." |
| human_requested | "I understand you'd like to speak with someone directly. I'm arranging for a team member to contact you." |
| frustrated_customer | "I can see you've had a frustrating experience. Let me connect you with a specialist for personal attention." |

---

### SKILL-004: send_channel_response

**Display Name:** Send Channel Response

**Description:** Send formatted response to customer via their channel with appropriate tone and length.

**Trigger:** After answer generated or escalation message prepared

**Tools Used:**
- `send_response`

**Input:**
| Parameter | Type | Required |
|-----------|------|----------|
| ticket_id | string | Yes |
| response_text | string | Yes |
| channel | string | Yes |

**Output:**
| Field | Type | Description |
|-------|------|-------------|
| success | boolean | Delivery success |
| ticket_id | string | Ticket ID |
| channel | string | Channel used |
| response_length | integer | Character count |
| delivery_status | string | sent, delivered, or failed |
| sent_at | ISO8601 | Send timestamp |

**Workflow:**
1. Validate response length against channel constraints
2. Apply channel formatting (greeting, signature, tone)
3. Call `send_response`
4. Confirm delivery_status == "sent"
5. Resolve ticket if issue resolved and sentiment >= 0.4

**Channel Formatting Rules:**

| Element | Email | WhatsApp | Web Form |
|---------|-------|----------|----------|
| Greeting | "Dear [Name]," | None | "Hi [Name]," |
| Opening | "Thank you for reaching out..." | None | None |
| Style | Formal, detailed | Concise, conversational | Semi-formal |
| Closing | "If you have further questions..." | "📱 Reply for more help..." | "Need more help?..." |
| Signature | "Best regards, TechCorp AI Support" | None | None |
| Ticket Ref | "Ticket Reference: {id}" | None | "Ticket: {id}" |

---

### SKILL-005: track_customer_sentiment

**Display Name:** Track Customer Sentiment

**Description:** Monitor and track customer sentiment over time to detect frustration trends.

**Trigger:** Every customer message received

**Tools Used:**
- `get_customer_stats`

**Input:**
| Parameter | Type | Required |
|-----------|------|----------|
| customer_id | string | Yes |
| message | string | Yes |

**Output:**
| Field | Type | Description |
|-------|------|-------------|
| sentiment_score | number (0-1) | Current sentiment |
| sentiment_category | string | positive, neutral, or negative |
| trend | string | improving, stable, declining, or insufficient_data |
| frustration_flag | boolean | True if 3+ negative interactions |
| avg_sentiment | number | Average across all interactions |

**Sentiment Thresholds:**

| Category | Score Range |
|----------|-------------|
| Positive | >= 0.7 |
| Neutral | 0.4 - 0.69 |
| Negative | < 0.4 |
| Escalation Required | < 0.3 |

**Workflow:**
1. Analyze sentiment (word counting)
2. Update sentiment_history
3. Calculate trend (recent vs older avg)
4. Check frustration (3+ negative in last 5)
5. If frustration_flag OR sentiment < 0.3 → escalate

---

### SKILL-006: retrieve_customer_context

**Display Name:** Retrieve Customer Context

**Description:** Get complete customer context including history, stats, and cross-channel information.

**Trigger:** Customer identified as returning (has prior interactions)

**Tools Used:**
- `get_customer_history`
- `get_customer_stats`

**Input:**
| Parameter | Type | Required | Default |
|-----------|------|----------|---------|
| customer_identifier | string | Yes | - |
| identifier_type | string | No | email |

**Output:**
| Field | Type | Description |
|-------|------|-------------|
| customer_id | string | Internal ID |
| history | array | Last 10 messages across channels |
| stats | object | total_tickets, avg_sentiment, etc. |
| cross_channel_context | object | is_returning, prior_channels, channels_used |

**Workflow:**
1. Identify customer by email or phone
2. Call `get_customer_history` (limit: 10)
3. Call `get_customer_stats`
4. Detect cross-channel usage
5. Generate personalized greeting if returning

**Cross-Channel Greeting Templates:**

| Scenario | Greeting |
|----------|----------|
| Email → WhatsApp | "Hi {name}! Following up from our email conversation about {topic}..." |
| WhatsApp → Email | "Dear {name}, continuing our WhatsApp discussion about {topic}..." |
| Web → Any | "Hi {name}, regarding your web form submission about {topic}..." |
| Same Channel | "Welcome back, {name}! I see you previously asked about {topic}..." |

---

## Skill Execution Order

```
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 1: INTAKE (Parallel Execution)                            │
│ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ │
│ │ create_support_  │ │ track_customer_  │ │ retrieve_        │ │
│ │ ticket           │ │ sentiment        │ │ customer_context │ │
│ └──────────────────┘ └──────────────────┘ └──────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 2: PROCESSING (Sequential)                                │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ answer_product_question                                   │   │
│ └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 3: RESPONSE (Sequential)                                  │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ send_channel_response                                     │   │
│ └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 4: ESCALATION (Conditional Override)                      │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ escalate_to_human (if any escalation trigger detected)    │   │
│ └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Metrics & Targets

| Metric | Target | Description |
|--------|--------|-------------|
| Response Time | < 3000 ms | Processing time per message |
| Escalation Rate | < 20% | Percentage escalated |
| Resolution Rate | > 80% | Percentage resolved by AI |
| Avg Sentiment | > 0.6 | Average customer sentiment |
| First Contact Resolution | > 70% | Resolved in first interaction |

---

## Skill-to-Tool Mapping

| Skill | Primary Tool | Secondary Tool |
|-------|--------------|----------------|
| answer_product_question | search_knowledge_base | send_response |
| create_support_ticket | create_ticket | - |
| escalate_to_human | escalate_ticket | send_response |
| send_channel_response | send_response | - |
| track_customer_sentiment | get_customer_stats | - |
| retrieve_customer_context | get_customer_history | get_customer_stats |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0-incubation | 2026-03-22 | Initial skills manifest created |

---

*Exercise 1.5 Complete — Incubation Phase Done!*
