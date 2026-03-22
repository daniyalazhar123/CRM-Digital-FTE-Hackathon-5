# The CRM Digital FTE - Project Context

## Project Overview

This is **Hackathon 5** of the Agent Factory series: **"Build Your First 24/7 AI Employee"**. The goal is to build a **Customer Success Digital FTE (Full-Time Equivalent)** - an AI-powered support agent that works 24/7 across multiple communication channels.

### Business Problem
A growing SaaS company needs a Customer Success FTE that can:
- Handle customer questions 24/7 from product documentation
- Accept inquiries from **three channels**: Gmail (Email), WhatsApp, and Web Form
- Triage and escalate complex issues appropriately
- Track all interactions in a PostgreSQL-based ticket management system (your CRM)
- Generate daily reports on customer sentiment
- Learn from resolved tickets to improve responses

**Target Cost:** \<$1,000/year vs $75,000/year for human FTE

---

## Multi-Channel Architecture

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│    Gmail     │    │   WhatsApp   │    │   Web Form   │
│   (Email)    │    │  (Messaging) │    │  (Website)   │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                   │
       ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Gmail API    │    │   Twilio     │    │   FastAPI    │
│   Webhook    │    │   Webhook    │    │   Endpoint   │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           ▼
                   ┌─────────────────┐
                   │  Unified Ticket │
                   │  Ingestion      │
                   │  (Kafka)        │
                   └────────┬────────┘
                            ▼
                   ┌─────────────────┐
                   │   Customer      │
                   │   Success FTE   │
                   │   (Agent)       │
                   └────────┬────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
         Reply via     Reply via    Reply via
          Email        WhatsApp      Web/API
```

### Channel Requirements

| Channel | Integration Method | Response Method |
|---------|-------------------|-----------------|
| **Gmail** | Gmail API + Pub/Sub or Polling | Send via Gmail API |
| **WhatsApp** | Twilio WhatsApp API | Reply via Twilio |
| **Web Form** | Next.js/HTML Form (Required Build) | API response + Email |

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| **Agent Framework** | OpenAI Agents SDK |
| **API Layer** | FastAPI |
| **Database/CRM** | PostgreSQL 16 + pgvector (vector search) |
| **Event Streaming** | Apache Kafka (aiokafka) |
| **Orchestration** | Kubernetes |
| **Email Integration** | Gmail API + Google Cloud Pub/Sub |
| **WhatsApp Integration** | Twilio WhatsApp API |
| **Web Form** | React/Next.js |
| **LLM** | GPT-4o |

---

## Project Structure

```
production/
├── agent/
│   ├── __init__.py
│   ├── customer_success_agent.py    # OpenAI Agents SDK definition
│   ├── tools.py                      # @function_tool decorated functions
│   ├── prompts.py                    # System prompts with channel awareness
│   └── formatters.py                 # Channel-specific response formatting
├── channels/
│   ├── __init__.py
│   ├── gmail_handler.py              # Gmail integration
│   ├── whatsapp_handler.py           # Twilio/WhatsApp integration
│   └── web_form_handler.py           # Web form API
├── workers/
│   ├── __init__.py
│   ├── message_processor.py          # Kafka consumer + agent runner
│   └── metrics_collector.py          # Background metrics
├── api/
│   ├── __init__.py
│   └── main.py                       # FastAPI application
├── database/
│   ├── schema.sql                    # PostgreSQL schema
│   ├── migrations/                   # Database migrations
│   └── queries.py                    # Database access functions
├── tests/
│   ├── test_agent.py
│   ├── test_channels.py
│   └── test_e2e.py
├── k8s/                              # Kubernetes manifests
├── web-form/
│   └── SupportForm.jsx               # React web form component
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## Key Components

### 1. Database Schema (Your CRM)
The PostgreSQL database serves as your complete CRM system with tables for:
- `customers` - Unified customer records across all channels
- `customer_identifiers` - Cross-channel identification (email, phone, WhatsApp)
- `conversations` - Conversation threads with channel tracking
- `messages` - All message history with channel metadata
- `tickets` - Support ticket lifecycle
- `knowledge_base` - Product documentation with vector embeddings
- `channel_configs` - Channel-specific configurations
- `agent_metrics` - Performance tracking

### 2. OpenAI Agents SDK Implementation
The Customer Success FTE agent uses:
- **5 core tools**: `search_knowledge_base`, `create_ticket`, `get_customer_history`, `escalate_to_human`, `send_response`
- **Channel-aware responses**: Different formatting for Email (formal), WhatsApp (concise), Web Form (semi-formal)
- **Strict constraints**: Never discuss pricing, never promise undocumented features, always escalate legal/refund requests

### 3. Channel Integrations
- **Gmail Handler**: Pub/Sub webhook processing, message parsing, reply sending
- **WhatsApp Handler**: Twilio webhook validation, message processing, response formatting
- **Web Form Handler**: FastAPI endpoints, form validation, ticket creation

### 4. Kafka Event Streaming
Topics for multi-channel processing:
- `fte.tickets.incoming` - Unified ticket queue
- `fte.channels.email.inbound`, `fte.channels.whatsapp.inbound`, `fte.channels.webform.inbound`
- `fte.escalations` - Human escalation events
- `fte.metrics` - Performance metrics
- `fte.dlq` - Dead letter queue for failed processing

### 5. Kubernetes Deployment
- **API Deployment**: 3+ replicas for FastAPI service
- **Worker Deployment**: 3+ replicas for message processing
- **HPA**: Auto-scaling based on CPU (70% target)
- **Health Checks**: Liveness and readiness probes on `/health`

---

## Development Phases

### Phase 1: Incubation (Hours 1-16)
Use Claude Code as your "Agent Factory" to:
1. Explore the problem space with sample tickets
2. Prototype the core customer interaction loop
3. Add memory and state management
4. Build an MCP server with tools
5. Define agent skills

**Deliverables**: Working prototype, discovery log, MCP server, agent skills manifest

### Phase 2: Specialization (Hours 17-40)
Transform prototype into production system:
1. Extract discoveries to formal specifications
2. Convert MCP tools to OpenAI SDK `@function_tool`
3. Build PostgreSQL schema with pgvector
4. Implement channel handlers (Gmail, WhatsApp, Web Form)
5. Set up Kafka event streaming
6. Create Kubernetes manifests

**Deliverables**: Production code, database schema, channel integrations, K8s manifests

### Phase 3: Integration & Testing (Hours 41-48)
1. Multi-channel E2E testing
2. Load testing (100+ submissions over 24 hours)
3. 24-hour continuous operation test
4. Chaos testing (random pod kills)

**Validation Metrics**: Uptime \>99.9%, P95 latency \<3s, Escalation rate \<25%

---

## Key Constraints & Guardrails

### Hard Constraints (Never Violate)
- NEVER discuss pricing → escalate immediately
- NEVER promise features not in documentation
- NEVER process refunds → escalate to billing
- NEVER share internal processes or system details
- ALWAYS use `send_response` tool to reply
- NEVER exceed response limits: Email=500 words, WhatsApp=300 chars, Web=300 words

### Escalation Triggers
- Customer mentions "lawyer", "legal", "sue", or "attorney"
- Customer uses profanity or aggressive language (sentiment \< 0.3)
- Cannot find relevant information after 2 search attempts
- Customer explicitly requests human help
- WhatsApp customer sends "human", "agent", or "representative"

---

## Important Notes

### What You DON'T Need
- ❌ External CRM (Salesforce, HubSpot) - PostgreSQL IS your CRM
- ❌ Full website - Only the support form component
- ❌ Production WhatsApp Business account - Twilio Sandbox suffices

### Required Builds
- ✅ **Web Support Form** - Complete React/Next.js component with validation
- ✅ **Gmail Integration** - Webhook handler + send functionality
- ✅ **WhatsApp Integration** - Twilio webhook handler + send functionality

---

## Resources

- [Agent Maturity Model](https://agentfactory.panaversity.org/docs/General-Agents-Foundations/agent-factory-paradigm/the-2025-inflection-point#the-agent-maturity-model)
- [OpenAI Agents SDK Documentation](https://platform.openai.com/docs/agents)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Gmail API Documentation](https://developers.google.com/gmail/api)
- [Twilio WhatsApp API](https://www.twilio.com/docs/whatsapp)

---

## File Reference

The main specification document is:
- `The CRM Digital FTE Factory Final Hackathon 5.md` - Complete hackathon instructions (2852 lines)

This file contains:
- Executive summary and business context
- Multi-channel architecture diagrams
- Step-by-step incubation phase exercises
- Transition checklist from prototype to production
- Specialization phase implementation details
- Kubernetes deployment manifests
- Testing requirements and scoring rubric
- FAQ and resources
