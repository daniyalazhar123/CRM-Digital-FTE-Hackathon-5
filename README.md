# CRM Digital FTE Factory — Hackathon 5

## Build Your First 24/7 AI Employee: From Incubation to Production

[![Phase 1: Complete](https://img.shields.io/badge/Phase%201-Incubation-green)]()
[![Phase 2: Complete](https://img.shields.io/badge/Phase%202-Specialization-blue)]()
[![Python 3.14](https://img.shields.io/badge/Python-3.14-yellow)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)]()
[![PostgreSQL + pgvector](https://img.shields.io/badge/PostgreSQL-pgvector-blue)]()

---

## Overview

**CRM Digital FTE** is a 24/7 AI-powered Customer Success employee that handles routine support queries across multiple channels (Email, WhatsApp, Web Form). Built following the **Agent Maturity Model** — from incubation prototype to production-grade Custom Agent.

**Business Value:**
- **Cost:** <$1,000/year vs $75,000/year for human FTE
- **Availability:** 24/7 without breaks, sick days, or vacations
- **Consistency:** Handles 80%+ of routine queries without escalation
- **Multi-Channel:** Unified customer experience across Email, WhatsApp, and Web

---

## Quick Start

### Prerequisites
- Docker Desktop (running)
- Python 3.14+
- Groq API Key (free: https://console.groq.com/keys)

### 1. Clone and Setup
```bash
cd "D:\Desktop4\The CRM Digital FTE"
cp .env.example .env
# Edit .env with your actual credentials
```

### 2. Start Database
```bash
docker-compose up -d
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run Components

**Option A: Run Prototype (Phase 1)**
```bash
python src\agent\prototype_agent.py
```

**Option B: Run Custom Agent (Phase 2)**
```bash
python src\agent\crm_agent.py
```

**Option C: Run FastAPI Server (Phase 2)**
```bash
cd src\api
python -m uvicorn main:app --reload --port 8000
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CRM DIGITAL FTE ARCHITECTURE                              │
│                                                                              │
│  CHANNEL INTAKE LAYER                                                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                          │
│  │Gmail Webhook│  │Twilio Webhook│  │ Web Form    │                          │
│  │  Handler    │  │  Handler    │  │  Handler    │                          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                          │
│         │                │                │                                  │
│         └────────────────┼────────────────┘                                  │
│                          ▼                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    FASTAPI SERVICE LAYER                              │   │
│  │  POST /webhooks/gmail                                                 │   │
│  │  POST /webhooks/whatsapp                                              │   │
│  │  POST /support/submit                                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                          │                                                   │
│  ┌───────────────────────┼───────────────────────────────────────────────┐ │
│  │                    CUSTOM AGENT (OpenAI SDK + Groq)                    │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                  │ │
│  │  │ search_      │ │ create_      │ │ escalate_    │                  │ │
│  │  │ knowledge_   │ │ ticket       │ │ ticket       │                  │ │
│  │  │ base         │ │              │ │              │                  │ │
│  │  └──────────────┘ └──────────────┘ └──────────────┘                  │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                  │ │
│  │  │ get_customer │ │ send_        │ │ track_       │                  │ │
│  │  │ _context     │ │ response     │ │ sentiment    │                  │ │
│  │  └──────────────┘ └──────────────┘ └──────────────┘                  │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                          │                                                   │
│  ┌───────────────────────▼───────────────────────────────────────────────┐ │
│  │                    POSTGRESQL + pgvector                                │ │
│  │  - customers (unified across channels)                                 │ │
│  │  - tickets (with channel tracking)                                     │ │
│  │  - messages (conversation history)                                     │ │
│  │  - embeddings (vector search for KB)                                   │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
D:\Desktop4\The CRM Digital FTE\
├── context/                    # Context files for agent
│   ├── brand-voice.md          # Communication guidelines
│   ├── escalation-rules.md     # Escalation triggers
│   ├── product-docs.md         # Product documentation
│   └── sample-tickets.json     # 28 test tickets
│
├── database/                   # Database layer
│   └── schema.sql              # PostgreSQL schema
│
├── docs/                       # Documentation
│   ├── PHASE1_README.md        # Phase 1 guide
│   └── PHASE2_README.md        # Phase 2 guide
│
├── specs/                      # Specifications
│   ├── discovery-log.md        # Exercise 1.1
│   ├── customer-success-fte-spec.md
│   ├── agent-skills-manifest.* # Exercise 1.5
│   ├── transition-checklist.md # Transition doc
│   └── exercise-*.md           # Exercise reports
│
├── src/                        # Source code
│   ├── agent/
│   │   ├── prototype_agent.py  # Phase 1 prototype
│   │   └── crm_agent.py        # Phase 2 Custom Agent
│   ├── api/
│   │   └── main.py             # FastAPI service
│   ├── db/
│   │   └── database.py         # Database layer
│   ├── mcp_server/
│   │   └── mcp_server.py       # MCP server
│   ├── channels/               # Channel handlers (Phase 2)
│   ├── workers/                # Background workers (Phase 2)
│   └── web-form/               # React web form (Phase 2)
│
├── tests/                      # Test suite
├── k8s/                        # Kubernetes manifests
│
├── docker-compose.yml          # Docker setup
├── requirements.txt            # Python dependencies
├── .env.example                # Environment template
├── .gitignore                  # Git ignore rules
└── README.md                   # This file
```

---

## Documentation

| Phase | Document | Description |
|-------|----------|-------------|
| **Phase 1** | [docs/PHASE1_README.md](docs/PHASE1_README.md) | Incubation Phase guide |
| **Phase 2** | [docs/PHASE2_README.md](docs/PHASE2_README.md) | Specialization Phase guide |
| **Specs** | [specs/transition-checklist.md](specs/transition-checklist.md) | Transition checklist |
| **API** | `http://localhost:8000/docs` | FastAPI Swagger docs |

---

## Key Features

### Multi-Channel Support
| Channel | Integration | Response Method |
|---------|-------------|-----------------|
| **Email** | Gmail API + Pub/Sub | Gmail API |
| **WhatsApp** | Twilio WhatsApp API | Twilio API |
| **Web Form** | React component | API + Email |

### AI Capabilities
- **Knowledge Base Search:** Semantic search with pgvector
- **Sentiment Analysis:** Real-time sentiment tracking
- **Escalation Detection:** 7 trigger types (pricing, legal, refund, etc.)
- **Cross-Channel Memory:** Remembers customers across channels
- **Response Formatting:** Channel-appropriate tone and length

### Hard Constraints
- NEVER discusses pricing (escalates immediately)
- NEVER processes refunds (escalates to billing)
- NEVER promises undocumented features
- ALWAYS creates ticket before responding
- ALWAYS uses channel-appropriate formatting

---

## Performance Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| Response Time | < 3 seconds | 62-1600ms |
| Escalation Rate | < 20% | 11.7% |
| AI Resolution | > 80% | 88.3% |
| Cross-Channel ID | > 95% | 100% |

---

## Testing

### Run Prototype Tests
```bash
python src\agent\prototype_agent.py
```

### Run Custom Agent Tests
```bash
python src\agent\crm_agent.py
```

### Test API Endpoints
```bash
# Health check
curl http://localhost:8000/health

# Submit support form
curl -X POST http://localhost:8000/support/submit \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User","email":"test@example.com","subject":"Test","category":"how-to","message":"Test message"}'

# Get metrics
curl http://localhost:8000/metrics/channels
```

---

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=crm_db
DB_USER=postgres
DB_PASSWORD=your_password

# Groq API (for Custom Agent)
GROQ_API_KEY=your_groq_api_key_here
MODEL_NAME=llama-3.3-70b-versatile
```

---

## License

MIT License - See LICENSE file for details.

---

## Acknowledgments

- **Panaversity** - Agent Factory Paradigm
- **Groq** - Fast LLM inference
- **OpenAI** - Agents SDK
- **PostgreSQL** - pgvector extension

---

*Built for Hackathon 5: The CRM Digital FTE Factory*
