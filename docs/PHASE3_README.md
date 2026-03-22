# Phase 3: Integration Testing

[![Phase 3 Progress](https://img.shields.io/badge/Phase%203-0%25-red)]()
[![Target](https://img.shields.io/badge/Target-99.9%25%20uptime-blue)]()
[![P95 Latency](https://img.shields.io/badge/P95-%3C3s-green)]()

**Status:** ⚠️ PLANNED  
**Duration:** Hours 41-48  
**Goal:** Validate end-to-end system reliability

---

## Target Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Uptime** | > 99.9% | 24-hour continuous test |
| **P95 Latency** | < 3 seconds | End-to-end response time |
| **Escalation Rate** | < 20% | Percentage of tickets |
| **Cross-Channel ID** | > 95% | Customer recognition accuracy |
| **Message Loss** | 0% | No dropped messages |
| **Error Rate** | < 1% | Failed requests |

---

## Test Scenarios (10)

### Scenario 1: Multi-Channel Customer Journey
**Description:** Customer contacts via email, then WhatsApp, then web form.

**Expected:**
- Customer recognized across all channels
- Conversation history preserved
- Consistent responses

**Commands:**
```bash
# Run multi-channel test
python tests/test_agent.py::TestReturningCustomer::test_cross_channel_customer_tracking -v
```

---

### Scenario 2: High Volume Load Test
**Description:** 100+ submissions over 1 hour.

**Expected:**
- Response time < 3s P95
- No message loss
- Auto-scaling triggers

**Commands:**
```bash
# Install locust
pip install locust

# Run load test
locust -f tests/load_test.py --host=http://localhost:8000
```

---

### Scenario 3: Escalation Flow
**Description:** Trigger all 7 escalation types.

**Expected:**
- All triggers detected correctly
- Proper routing to human queue
- Customer notified appropriately

**Commands:**
```bash
python -m pytest tests/test_agent.py::TestEscalationTriggers -v
```

---

### Scenario 4: Database Failover
**Description:** Restart PostgreSQL during operation.

**Expected:**
- Connection retry works
- No data loss
- Automatic reconnection

**Commands:**
```bash
# Restart database
docker-compose restart postgres

# Monitor application logs
tail -f logs/app.log
```

---

### Scenario 5: Channel Webhook Integration
**Description:** Test Gmail, WhatsApp, and web form webhooks.

**Expected:**
- Webhooks received and processed
- Messages queued correctly
- Responses sent via correct channel

**Commands:**
```bash
# Test web form
curl -X POST http://localhost:8000/support/submit \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","email":"test@test.com","subject":"Test","category":"how-to","message":"Test message"}'

# Test Gmail webhook (mock)
curl -X POST http://localhost:8000/webhooks/gmail \
  -H "Content-Type: application/json" \
  -d '{"message":{"data":"test"}}'

# Test WhatsApp webhook (mock)
curl -X POST http://localhost:8000/webhooks/whatsapp \
  -d "From=whatsapp:+1234567890&Body=Hello"
```

---

### Scenario 6: Sentiment Trend Detection
**Description:** Customer sentiment declines over 5 interactions.

**Expected:**
- Trend detected as "declining"
- Frustration flag set after 3+ negative
- Escalation triggered

**Commands:**
```bash
# Run sentiment tests
python -m pytest tests/test_database.py::TestSentimentTracking -v
```

---

### Scenario 7: Knowledge Base Search
**Description:** Search across all product documentation.

**Expected:**
- Relevant results returned
- Vector similarity working
- Fallback to text search

**Commands:**
```bash
# Test via API
curl "http://localhost:8000/search?query=how%20to%20add%20team%20members"
```

---

### Scenario 8: Ticket Lifecycle
**Description:** Full ticket lifecycle from creation to resolution.

**Expected:**
- Ticket created with unique ID
- Status transitions correctly
- Resolution recorded

**Commands:**
```bash
# Create ticket
TICKET=$(curl -X POST http://localhost:8000/support/submit \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","email":"test@test.com","subject":"Test","category":"how-to","message":"Help"}' \
  | jq -r '.ticket_id')

# Check status
curl http://localhost:8000/support/ticket/$TICKET
```

---

### Scenario 9: Metrics Collection
**Description:** Verify all metrics are being collected.

**Expected:**
- Channel metrics available
- Sentiment averages calculated
- Escalation rates tracked

**Commands:**
```bash
# Get channel metrics
curl http://localhost:8000/metrics/channels

# Get summary metrics
curl http://localhost:8000/metrics/summary
```

---

### Scenario 10: 24-Hour Continuous Operation
**Description:** Run system for 24 hours with continuous traffic.

**Expected:**
- 99.9% uptime
- Memory stable (no leaks)
- Response times consistent

**Commands:**
```bash
# Start monitoring
docker stats crm-postgres

# Run continuous load
locust -f tests/load_test.py --host=http://localhost:8000 --run-time 24h
```

---

## How to Run Integration Tests

### Prerequisites
```bash
# Ensure Docker is running
docker-compose up -d

# Install test dependencies
pip install pytest pytest-cov locust
```

### Run All Integration Tests
```bash
cd "D:\Desktop4\The CRM Digital FTE"
python -m pytest tests/ -v --tb=short
```

### Run Specific Scenario
```bash
# Example: Scenario 3 (Escalation)
python -m pytest tests/test_agent.py::TestEscalationTriggers -v
```

### Run Load Test
```bash
locust -f tests/load_test.py --host=http://localhost:8000
```

### Generate Coverage Report
```bash
python -m pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

---

## Test Environment

### Infrastructure
| Component | Configuration |
|-----------|---------------|
| **Database** | PostgreSQL 16 + pgvector |
| **API** | FastAPI (uvicorn) |
| **Agent** | OpenAI SDK + Groq |
| **Cache** | Connection pool (2-10) |

### Test Data
| Dataset | Count |
|---------|-------|
| Sample Tickets | 28 |
| Knowledge Base | 12 sections |
| Test Customers | Generated per test |

---

## Pass/Fail Criteria

### Pass
- ✅ All 10 scenarios executed
- ✅ 99.9% uptime achieved
- ✅ P95 latency < 3s
- ✅ Zero message loss
- ✅ All escalation triggers working

### Fail
- ❌ Uptime < 99.9%
- ❌ P95 latency > 3s
- ❌ Any message loss
- ❌ Escalation triggers not detected

---

## Reporting

### Test Report Template
```markdown
## Phase 3 Integration Test Report

**Date:** YYYY-MM-DD
**Duration:** X hours
**Tester:** Name

### Results
| Scenario | Status | Notes |
|----------|--------|-------|
| 1. Multi-Channel | PASS/FAIL | |
| 2. Load Test | PASS/FAIL | |
| ... | ... | |

### Metrics
- Uptime: X.XX%
- P95 Latency: X.XXs
- Total Requests: XXXX
- Errors: XX

### Issues Found
1. Issue description
2. Fix applied
3. Re-test result

### Sign-off
- [ ] All scenarios passed
- [ ] Metrics meet targets
- [ ] Ready for production
```

---

## Next Steps After Phase 3

1. **Production Deployment** - Deploy to Kubernetes cluster
2. **Monitoring Setup** - Configure alerts and dashboards
3. **Documentation** - Update runbooks and user guides
4. **Handoff** - Transfer to operations team

---

*Phase 3: Integration Testing — Planned*
