# Discovery Log - Customer Success FTE

**Hackathon:** The CRM Digital FTE Factory Final Hackathon 5  
**Phase:** 1 - Incubation  
**Exercise:** 1.1 - Initial Exploration  
**Date:** March 22, 2026

---

## 1. Channel Pattern Analysis

### 1.1 Message Length & Tone by Channel

| Aspect | Email (Gmail) | WhatsApp | Web Form |
|--------|---------------|----------|----------|
| **Avg Length** | 150-500 words | 10-50 words | 50-200 words |
| **Tone** | Formal, professional | Casual, conversational | Semi-formal, structured |
| **Structure** | Subject line, greeting, body, signature | Free-flowing, fragments | Pre-defined fields |
| **Response Expectation** | Within hours | Immediate (minutes) | Within minutes |
| **Common Elements** | Attachments, signatures, threads | Emojis, abbreviations | Category selection, priority |

### 1.2 Common Question Types (Discovered from Hackathon Spec)

| Category | Description | Example Queries | Priority |
|----------|-------------|-----------------|----------|
| **Product Features** | Questions about what the product does | "Does your API support webhooks?", "Can I export data to CSV?" | Medium |
| **How-To/Usage** | Step-by-step guidance requests | "How do I reset my password?", "Where do I find the API key?" | High |
| **Bug Reports** | Something isn't working | "The dashboard won't load", "Getting error 500 on upload" | High |
| **Billing/Pricing** | Cost, plans, payments | "How much is enterprise?", "Can I get a refund?" | **ESCALATE** |
| **Integration** | Connecting with other tools | "Does this work with Slack?", "Zapier integration?" | Medium |
| **Account Management** | User settings, permissions | "How do I add team members?", "Change my email" | Low |
| **Feedback** | Suggestions, complaints | "You should add dark mode", "This feature is confusing" | Low |

### 1.3 Sentiment Distribution (Expected)

| Sentiment Range | Percentage | Characteristics | Handling Strategy |
|-----------------|------------|-----------------|-------------------|
| **Positive (0.7-1.0)** | 25% | "Love your product!", "Thanks for the help" | Acknowledge, reinforce positivity |
| **Neutral (0.4-0.69)** | 50% | Standard inquiries, factual questions | Direct, helpful responses |
| **Negative (0.3-0.39)** | 15% | Frustrated but constructive | Empathy + quick resolution |
| **Critical (<0.3)** | 10% | Angry, aggressive, threatening | **ESCALATE immediately** |

### 1.4 Frequent Edge Cases (Discovered)

| Edge Case | Channel | Frequency | Handling Strategy |
|-----------|---------|-----------|-------------------|
| **Empty/Blank Message** | All | Medium | Ask for clarification politely |
| **Multi-question Messages** | Email, Web | High | Address each question systematically |
| **Follow-up Without Context** | WhatsApp | High | Load conversation history, reference prior context |
| **Channel Switching Mid-Conversation** | All | Medium | Recognize customer, maintain continuity |
| **Non-English Messages** | All | Low | Detect language, respond appropriately or escalate |
| **Attachments/Media** | Email, WhatsApp | Medium | Process or acknowledge, ask for description if needed |
| **Off-Topic/Spam** | All | Low | Politely redirect or flag for review |
| **Competitor Mentions** | All | Low | Never discuss, redirect to our features |
| **Technical Jargon Overload** | Email | Medium | Ask clarifying questions, don't assume |
| **Ambiguous References** | WhatsApp | High | "it", "this", "that" without context - ask for clarification |

### 1.5 Escalation Triggers (Crystallized from Spec)

#### Automatic Escalation (Never Answer)
| Trigger | Keywords/Patterns | Reason |
|---------|-------------------|--------|
| **Legal Threats** | "lawyer", "attorney", "sue", "legal action", "lawsuit" | Legal liability |
| **Pricing Inquiries** | "how much", "pricing", "cost", "enterprise plan", "discount" | Sales team domain |
| **Refund Requests** | "refund", "money back", "cancel subscription", "billing issue" | Billing team domain |
| **Explicit Human Request** | "speak to human", "real person", "agent", "manager" | Customer preference |
| **Competitor Discussion** | Competitor names, "vs [competitor]" | Strategic sensitivity |

#### Sentiment-Based Escalation
| Condition | Threshold | Action |
|-----------|-----------|--------|
| **Angry Customer** | Sentiment < 0.3 | Escalate with reason "negative_sentiment" |
| **Profanity/Abuse** | Detected aggressive language | Escalate with reason "abusive_language" |

#### Knowledge-Based Escalation
| Condition | Threshold | Action |
|-----------|-----------|--------|
| **No Results After Search** | 2+ failed knowledge base searches | Escalate with reason "no_relevant_info" |
| **Low Confidence Answer** | Agent confidence < 0.6 | Consider escalation |

---

## 2. Channel-Specific Response Templates (Discovered)

### 2.1 Email Template (Formal)
```
Dear [Customer Name],

Thank you for reaching out to TechCorp Support.

[Detailed response - 200-500 words]

If you have any further questions, please don't hesitate to reply to this email.

Best regards,
TechCorp AI Support Team
---
Ticket Reference: [ticket_id]
This response was generated by our AI assistant. For complex issues, you can request human support.
```

### 2.2 WhatsApp Template (Concise)
```
[Direct answer - max 300 chars]

📱 Reply for more help or type 'human' for live support.
```

### 2.3 Web Form Template (Semi-Formal)
```
[Helpful response - 100-300 words]

---
Need more help? Reply to this message or visit our support portal.
```

---

## 3. Required Workflow (Discovered)

The agent MUST follow this order for EVERY interaction:

```
1. FIRST: Call create_ticket() to log the interaction
   - Include channel metadata
   - Assign priority based on category/sentiment

2. THEN: Call get_customer_history() to check for prior context
   - Look up customer by email/phone
   - Load conversations across ALL channels
   - Identify if this is continuation

3. THEN: Call search_knowledge_base() if product questions arise
   - Use semantic search with embeddings
   - Return top 5 relevant results

4. FINALLY: Call send_response() to reply
   - NEVER respond without this tool
   - Automatically formats for channel
```

---

## 4. Data Model Discoveries

### 4.1 Customer Identification Strategy
| Identifier Type | Primary Key | Matching Strategy |
|-----------------|-------------|-------------------|
| **Email** | customers.email | Exact match, case-insensitive |
| **Phone/WhatsApp** | customer_identifiers | Normalize to E.164 format |
| **Cross-Channel** | Unified customer_id | Merge by email OR phone |

### 4.2 Conversation Continuity
- Conversations remain "active" for 24 hours
- After 24 hours of inactivity → new conversation
- Customer can switch channels mid-conversation
- All messages linked to conversation_id

### 4.3 Ticket Lifecycle States
```
open → processing → waiting_customer → resolved
                  ↓
              escalated → human_resolved
```

---

## 5. Performance Requirements (From Spec)

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Response Time (Processing)** | < 3 seconds | Agent execution time |
| **Response Time (Delivery)** | < 30 seconds | End-to-end latency |
| **Accuracy** | > 85% | On test set evaluation |
| **Escalation Rate** | < 20% | Percentage of tickets escalated |
| **Cross-Channel ID** | > 95% | Correct customer identification |

---

## 6. MCP Tools Discovered (For Exercise 1.4)

| Tool Name | Purpose | Input Schema | Output |
|-----------|---------|--------------|--------|
| `search_knowledge_base` | Find relevant docs | query (str), max_results (int), category (optional) | Formatted results with relevance scores |
| `create_ticket` | Log interactions | customer_id, issue, priority, channel | ticket_id (UUID) |
| `get_customer_history` | Get prior context | customer_id | Conversation history across all channels |
| `escalate_to_human` | Hand off complex issues | ticket_id, reason, urgency | escalation_id, confirmation |
| `send_response` | Reply to customer | ticket_id, message, channel | delivery_status |

---

## 7. Agent Skills Manifest (For Exercise 1.5)

### Skill 1: Knowledge Retrieval
- **When to use:** Customer asks product questions
- **Inputs:** query text, optional category filter
- **Outputs:** Relevant documentation snippets with scores
- **Fallback:** "No relevant documentation found" → escalate

### Skill 2: Sentiment Analysis
- **When to use:** Every incoming message
- **Inputs:** Message text
- **Outputs:** Sentiment score (0-1), confidence, trend
- **Action:** Trigger escalation if < 0.3

### Skill 3: Escalation Decision
- **When to use:** After generating response
- **Inputs:** Conversation context, sentiment trend, topic
- **Outputs:** should_escalate (bool), reason, urgency
- **Triggers:** Legal, pricing, refunds, negative sentiment, no info

### Skill 4: Channel Adaptation
- **When to use:** Before sending any response
- **Inputs:** Response text, target channel, customer context
- **Outputs:** Formatted response (length, tone, structure)
- **Constraints:** Email=500 words, WhatsApp=300 chars, Web=300 words

### Skill 5: Customer Identification
- **When to use:** On every incoming message
- **Inputs:** Email, phone, or other identifiers
- **Outputs:** Unified customer_id, merged history, confidence score
- **Edge Case:** New customer → create record

---

## 8. Open Questions & Clarifications Needed

### 8.1 Sample Tickets
- ❓ **Do we have actual sample tickets data?** The spec mentions `sample-tickets.json` with 50+ tickets, but file is not present in the project directory.
- ❓ **What is the product?** The spec references "TechCorp SaaS" but doesn't specify what the product does. We need product documentation to build the knowledge base.

### 8.2 Company Specifics
- ❓ **What are the actual product features?** Need product docs to populate knowledge base for semantic search.
- ❓ **What is the brand voice?** The spec mentions "brand-voice.md" but we need specifics on tone, values, and communication style.

### 8.3 Technical Setup
- ❓ **Do we have API credentials?** Gmail API, Twilio, OpenAI API keys needed for implementation.
- ❓ **PostgreSQL setup?** Should we use local PostgreSQL or a cloud service for incubation?

---

## 9. Next Steps (Exercise 1.2 Preparation)

Before building the prototype core loop, we need:

1. **Sample Tickets Data** - Create or obtain 50+ realistic support tickets across all channels
2. **Product Documentation** - At least 10-20 knowledge base entries for search testing
3. **Company Profile** - Basic info about the fictional SaaS company
4. **Escalation Rules Document** - Formalize the escalation criteria

---

## Summary

This discovery log captures the patterns, requirements, and edge cases identified during initial exploration of the Customer Success FTE problem space. Key findings:

- **Three distinct channels** require different response formatting and handling
- **Clear escalation triggers** must be enforced (pricing, legal, refunds, sentiment)
- **Cross-channel continuity** is critical - customers expect memory across channels
- **Strict workflow order** ensures proper ticket tracking and context loading
- **Performance targets** are aggressive (<3s processing, >85% accuracy)

**Ready to proceed to Exercise 1.2 - Prototype the Core Loop** once sample data and product context are available.
