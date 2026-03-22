# Escalation Rules - Customer Success FTE

**Version:** 1.0  
**Effective:** March 2026

---

## 1. Automatic Escalation (Never Answer Directly)

The AI agent **MUST** escalate immediately when any of these triggers are detected. The agent should **not** attempt to answer or provide workarounds.

### 1.1 Legal & Compliance Triggers
| Trigger | Keywords/Patterns | Escalation Reason |
|---------|-------------------|-------------------|
| **Legal Threats** | "lawyer", "attorney", "sue", "lawsuit", "legal action", "court", "suing" | `legal_threat` |
| **Regulatory Issues** | "GDPR", "compliance violation", "report to authorities", "fine", "penalty" | `compliance_issue` |
| **Data Breach Claims** | "hacked", "data leak", "unauthorized access", "security breach" | `security_incident` |

**Agent Response Template:**
> "I understand this is a serious matter. Let me connect you with a specialist who can assist you properly."

### 1.2 Pricing & Sales Triggers
| Trigger | Keywords/Patterns | Escalation Reason |
|---------|-------------------|-------------------|
| **Pricing Inquiries** | "how much", "pricing", "cost", "enterprise plan", "discount", "volume pricing" | `pricing_inquiry` |
| **Refund Requests** | "refund", "money back", "cancel subscription", "billing issue", "charged incorrectly" | `refund_request` |
| **Upgrade/Downgrade** | "change plan", "upgrade", "downgrade", "switch plan" | `plan_change_request` |
| **Custom Contracts** | "contract", "SLA", "custom agreement", "terms" | `enterprise_sales` |

**Agent Response Template:**
> "I'll connect you with our sales/billing team who can provide accurate pricing information and discuss options for your specific needs."

### 1.3 Human Request Triggers
| Trigger | Keywords/Patterns | Escalation Reason |
|---------|-------------------|-------------------|
| **Explicit Request** | "speak to human", "real person", "agent", "manager", "supervisor" | `human_requested` |
| **Frustration Indicators** | "this is ridiculous", "useless", "worst product", "waste of money" | `frustrated_customer` |
| **Repeated Contact** | "I already asked", "still not resolved", "following up again" | `repeat_contact` |

**Agent Response Template:**
> "I understand you'd like to speak with someone directly. Let me arrange that for you."

---

## 2. Sentiment-Based Escalation

### 2.1 Negative Sentiment Threshold
| Sentiment Score | Action |
|-----------------|--------|
| **0.4 - 0.69** | Standard handling with extra empathy |
| **0.3 - 0.39** | Consider escalation; use careful language |
| **< 0.3** | **ESCALATE immediately** with reason `negative_sentiment` |

### 2.2 Profanity & Abuse Detection
**Automatically escalate** when detected:
- Profanity or swear words
- Personal attacks or insults
- Aggressive/all-caps messages
- Threatening language

**Escalation Reason:** `abusive_language`

**Agent Response Template:**
> "I can see you're frustrated, and I want to make sure you get the help you deserve. Let me connect you with someone who can assist."

---

## 3. Knowledge-Based Escalation

### 3.1 No Relevant Information Found
**Escalate when:**
- 2+ knowledge base searches return no relevant results
- Question is outside product documentation scope
- Customer asks about competitor products

**Escalation Reason:** `no_relevant_info`

**Agent Response Template:**
> "That's a great question, and I want to make sure you get accurate information. Let me connect you with a specialist."

### 3.2 Low Confidence Answers
**Consider escalation when:**
- Agent confidence score < 0.6
- Answer requires assumptions not in documentation
- Question involves edge cases not covered in docs

---

## 4. Technical Issue Escalation

### 4.1 Critical Bugs
**Escalate when:**
- Customer reports data loss
- Multiple users affected (team-wide outage)
- Core functionality broken (login, payments, data access)
- Issue persists after standard troubleshooting

**Escalation Reason:** `critical_bug`

### 4.2 Integration Failures
**Escalate when:**
- Integration was a key purchase factor (mentioned by customer)
- Standard troubleshooting steps failed
- Integration affects multiple team members

**Escalation Reason:** `integration_issue`

---

## 5. Escalation Workflow

### Step 1: Create Ticket (Always First)
```python
ticket_id = create_ticket(
    customer_id=customer_id,
    issue=customer_message,
    priority=determine_priority(),
    channel=channel
)
```

### Step 2: Determine Escalation Reason
```python
escalation_reason = detect_escalation_trigger(customer_message, sentiment_score)
```

### Step 3: Call Escalation Tool
```python
result = escalate_to_human(
    ticket_id=ticket_id,
    reason=escalation_reason,
    urgency=determine_urgency()
)
```

### Step 4: Inform Customer
```python
send_response(
    ticket_id=ticket_id,
    message=appropriate_template(escalation_reason),
    channel=channel
)
```

---

## 6. Priority & Urgency Levels

### Priority Assignment
| Priority | Criteria | Response Target |
|----------|----------|-----------------|
| **Critical** | Data loss, security breach, complete outage | Immediate |
| **High** | Core feature broken, multiple users affected | 1-2 hours |
| **Medium** | Single user issue, workaround available | 24 hours |
| **Low** | Feature request, general question | 48 hours |

### Urgency Modifiers
Increase urgency when:
- Customer mentions deadline ("presentation in 30 minutes")
- Multiple failed resolution attempts
- High-value customer (Business/Enterprise plan)
- Negative sentiment + valid complaint

---

## 7. Escalation Handoff Quality

### Required Context for Human Agents
Every escalation must include:
1. **Full conversation history** - All messages exchanged
2. **Customer profile** - Plan type, tenure, prior tickets
3. **Escalation reason** - Specific trigger detected
4. **Sentiment analysis** - Current and trend
5. **Actions taken** - What the AI already tried
6. **Suggested next steps** - If applicable

### Escalation Metadata Format
```json
{
  "ticket_id": "uuid",
  "escalation_reason": "pricing_inquiry",
  "urgency": "normal",
  "sentiment_score": 0.5,
  "sentiment_trend": "stable",
  "customer_plan": "Pro",
  "prior_tickets_count": 2,
  "ai_actions_taken": [
    "searched_knowledge_base",
    "provided_troubleshooting_steps"
  ],
  "suggested_action": "Connect with sales team for pricing discussion"
}
```

---

## 8. What NOT to Escalate

The AI should **handle directly** (no escalation needed):
- ✅ Basic how-to questions (covered in docs)
- ✅ Feature explanations
- ✅ Simple troubleshooting (password reset, basic setup)
- ✅ Positive feedback or thank-you messages
- ✅ General product inquiries

**Goal:** Keep escalation rate below 20% of total tickets.

---

## 9. Edge Cases & Gray Areas

### Pricing Adjacent (Handle, Don't Escalate)
| Question | Action |
|----------|--------|
| "What features are in Pro vs Business?" | ✅ Answer from docs |
| "Is there a free trial?" | ✅ Answer from docs |
| "Do you offer student discounts?" | ❓ ESCALATE (discount inquiry) |
| "How much is the Business plan?" | ❓ ESCALATE (direct pricing) |

### Technical Complexity
| Situation | Action |
|-----------|--------|
| API rate limit question | ✅ Answer from docs |
| Custom integration architecture | ❓ ESCALATE (requires expertise) |
| "How do I use webhooks?" | ✅ Answer from docs |
| "Can you build a custom integration for us?" | ❓ ESCALATE (professional services) |

---

## 10. Continuous Improvement

### Weekly Escalation Review
- Review top 10 escalation reasons
- Identify patterns that could be handled by AI with more training
- Update knowledge base with gaps discovered
- Refine escalation thresholds based on data

### Metrics to Track
- Escalation rate by channel
- Escalation rate by category
- Customer satisfaction post-escalation
- Time to human response
- Resolution rate after escalation

---

*End of Escalation Rules Document*
