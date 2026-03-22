# Phase 2: Specialization Phase

**Status:** 🟡 IN PROGRESS (Steps 1-4 Complete)  
**Duration:** Hours 17-40  
**Role:** Builder (engineering for reliability, scale, and governance)

---

## Overview

Phase 2 transforms the incubation prototype into a production-grade Custom Agent using OpenAI Agents SDK, FastAPI, PostgreSQL with pgvector, and prepares for Kubernetes deployment.

---

## What Was Built

### Step 1: PostgreSQL Setup ✅
- Docker container with pgvector extension
- Database: `crm_db`
- Tables: customers, tickets, messages, embeddings
- Vector search enabled (1536 dimensions)

### Step 2: Database Migration Layer ✅
- `src/db/database.py` - Complete database layer
- CRUD operations matching InMemoryStore API
- Connection pooling (2-10 connections)
- Retry logic (3 attempts)
- Vector search methods

### Step 3: Custom Agent (OpenAI SDK + Groq) ✅
- `src/agent/crm_agent.py` - Production agent
- 6 function tools with Pydantic validation
- Groq LPU integration (Llama-3.3-70b)
- System prompt from skills manifest
- Escalation trigger detection

### Step 4: FastAPI Service Layer ✅
- `src/api/main.py` - Production API
- 9 endpoints (health, support, webhooks, metrics)
- CORS enabled for web form
- Background task processing

---

## How to Run Each Component

### 1. Start PostgreSQL (Docker)
```bash
docker-compose up -d

# Verify
docker ps
# Should show: crm-postgres (healthy)
```

### 2. Run Database Tests
```bash
cd src\db
python database.py
```

**Expected Output:**
```
✓ Database pool created: 2-10 connections
============================================================
PHASE 2 STEP 2 — DATABASE LAYER TEST
============================================================

TEST 1: Create Customer
✓ Created customer: test.user@example.com

TEST 2: Create Ticket
✓ Created ticket: TKT-20260322032642-1403

TEST 3: Add Messages
✓ Added message: customer (42 chars)
✓ Added message: agent (55 chars)

...

ALL TESTS COMPLETE
✓ Customer CRUD: PASS
✓ Ticket CRUD: PASS
✓ Message CRUD: PASS
✓ Sentiment Tracking: PASS
✓ Customer Stats: PASS
✓ Escalation: PASS
✓ Vector Search: PASS
```

### 3. Run Custom Agent
```bash
cd src\agent
python crm_agent.py
```

**Expected Output:**
```
======================================================================
PHASE 2 STEP 3 — CUSTOM AGENT TESTS
======================================================================

TEST 1: Email How-To Question
Response: **Ticket Created**: #1234
**Sentiment Tracked**: Neutral (0.5)

To add team members to your workspace, follow these steps:
1. Log in to your account and navigate to your workspace settings.
2. Click...

Escalated: False
Response Time: 1558ms
Status: ✅ PASS

TEST 2: WhatsApp Refund
Escalated: True
Reason: refund_request
Response Time: 63ms
Status: ✅ PASS

TEST 3: Web Form Pricing
Escalated: True
Reason: pricing_inquiry
Response Time: 66ms
Status: ✅ PASS
```

### 4. Run FastAPI Server
```bash
cd src\api
python -m uvicorn main:app --reload --port 8000
```

**Test Endpoints:**
```bash
# Health check
curl http://localhost:8000/health

# Submit support form
curl -X POST http://localhost:8000/support/submit ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"Test User\",\"email\":\"test@example.com\",\"subject\":\"Test\",\"category\":\"how-to\",\"message\":\"Test message\"}"

# Get metrics
curl http://localhost:8000/metrics/channels
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/support/submit` | POST | Web form submission |
| `/support/ticket/{id}` | GET | Ticket status |
| `/webhooks/gmail` | POST | Gmail webhook |
| `/webhooks/whatsapp` | POST | WhatsApp webhook |
| `/webhooks/whatsapp/status` | POST | WhatsApp status |
| `/customers/lookup` | GET | Customer lookup |
| `/metrics/channels` | GET | Channel metrics |
| `/metrics/summary` | GET | Summary metrics |

**Interactive Docs:** `http://localhost:8000/docs`

---

## Files Overview

### database/
| File | Purpose | Lines |
|------|---------|-------|
| `schema.sql` | PostgreSQL schema with pgvector | 100+ |

### src/db/
| File | Purpose | Lines |
|------|---------|-------|
| `database.py` | Database layer with CRUD | 750+ |
| `__init__.py` | Package marker | - |

### src/agent/
| File | Purpose | Lines |
|------|---------|-------|
| `crm_agent.py` | Custom Agent with OpenAI SDK | 830+ |
| `prototype_agent.py` | Phase 1 prototype (reference) | 1000+ |

### src/api/
| File | Purpose | Lines |
|------|---------|-------|
| `main.py` | FastAPI service layer | 500+ |
| `__init__.py` | Package marker | - |

### src/mcp_server/
| File | Purpose | Lines |
|------|---------|-------|
| `mcp_server.py` | MCP server (Phase 1, reference) | 600+ |

### specs/
| File | Purpose | Lines |
|------|---------|-------|
| `exercise-2.3-custom-agent.md` | Custom Agent test report | 400+ |
| `exercise-2.4-fastapi.md` | FastAPI test report | 300+ |

---

## Key Deliverables

### Step 1: PostgreSQL Setup ✅
- [x] Docker container running
- [x] Database `crm_db` created
- [x] pgvector extension enabled
- [x] 4 tables created (customers, tickets, messages, embeddings)
- [x] Schema saved to `database/schema.sql`
- [x] docker-compose.yml created

### Step 2: Database Migration Layer ✅
- [x] `src/db/database.py` created
- [x] CRUD operations (7 methods)
- [x] Vector search (2 methods)
- [x] Connection pooling
- [x] Retry logic
- [x] Migration function
- [x] All 9 tests passing

### Step 3: Custom Agent ✅
- [x] `src/agent/crm_agent.py` created
- [x] 6 function tools with Pydantic
- [x] Groq API integration
- [x] System prompt from manifest
- [x] 10 hard constraints encoded
- [x] 7 escalation triggers
- [x] All 3 tests passing (100% escalation accuracy)

### Step 4: FastAPI Service Layer ✅
- [x] `src/api/main.py` created
- [x] 9 endpoints implemented
- [x] CORS enabled
- [x] Integration with CRM agent
- [x] Request/response models
- [x] Error handling

### Step 5: Channel Handlers 🟡
- [ ] Gmail handler
- [ ] WhatsApp handler
- [ ] Web form handler

### Step 6: Web Support Form 🟡
- [ ] React component
- [ ] Form validation
- [ ] Submission handling

### Step 7: Kafka Event Streaming 🟡
- [ ] Kafka in docker-compose
- [ ] Topics defined
- [ ] Producer/Consumer workers

### Step 8: Kubernetes Manifests 🟡
- [ ] Namespace
- [ ] Deployments
- [ ] Services
- [ ] HPA

---

## Test Results

### Database Layer Tests
| Test | Status |
|------|--------|
| Customer CRUD | ✅ PASS |
| Ticket CRUD | ✅ PASS |
| Message CRUD | ✅ PASS |
| Sentiment Tracking | ✅ PASS |
| Customer Stats | ✅ PASS |
| Escalation | ✅ PASS |
| Vector Search | ✅ PASS |

### Custom Agent Tests
| Test | Expected | Actual | Status |
|------|----------|--------|--------|
| Email How-To | AI answers | Groq LLM response | ✅ PASS |
| WhatsApp Refund | ESCALATE | refund_request detected | ✅ PASS |
| Web Form Pricing | ESCALATE | pricing_inquiry detected | ✅ PASS |

**Performance:**
- Average Response Time: 62-1600ms
- Escalation Detection: 100% accurate
- Groq API: Working (HTTP 200)

---

## Architecture (Phase 2)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PHASE 2: SPECIALIZATION ARCHITECTURE                      │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    FASTAPI SERVICE LAYER                              │   │
│  │  - POST /support/submit                                               │   │
│  │  - POST /webhooks/gmail                                               │   │
│  │  - POST /webhooks/whatsapp                                            │   │
│  │  - GET /customers/lookup                                              │   │
│  │  - GET /metrics/channels                                              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              ↑                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    CUSTOM AGENT (OpenAI SDK + Groq)                   │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                │   │
│  │  │ search_      │ │ create_      │ │ escalate_    │                │   │
│  │  │ knowledge_   │ │ ticket       │ │ ticket       │                │   │
│  │  │ base         │ │              │ │              │                │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              ↑                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    PostgreSQL + pgvector                              │   │
│  │  - customers (unified across channels)                                │   │
│  │  - tickets (with channel tracking)                                    │   │
│  │  - messages (conversation history)                                    │   │
│  │  - embeddings (vector search for KB)                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Environment Setup

### Required (.env)
```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=crm_db
DB_USER=postgres
DB_PASSWORD=your_password

# Groq API
GROQ_API_KEY=your_groq_api_key_here
MODEL_NAME=llama-3.3-70b-versatile
BASE_URL=https://api.groq.com/openai/v1
```

### Get Groq API Key
1. Visit: https://console.groq.com/keys
2. Create new API key
3. Copy to `.env`

**Free Tier:** 30 requests/minute, 200 requests/day

---

## Next Steps

### Immediate (Complete Phase 2)
1. **Channel Handlers** - Gmail, WhatsApp, Web Form parsers
2. **Web Support Form** - React component (REQUIRED deliverable)
3. **Kafka Integration** - Event streaming
4. **Kubernetes Manifests** - Production deployment

### Testing
- E2E multi-channel tests
- Load testing
- 24-hour continuous operation test

---

*Phase 2: Specialization Phase — Steps 1-4 Complete!*
