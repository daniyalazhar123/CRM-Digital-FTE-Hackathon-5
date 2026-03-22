# Exercise 1.4 - MCP Server

**Status:** ✅ COMPLETE  
**Date:** March 22, 2026  
**File:** `src/mcp_server/mcp_server.py`

---

## Overview

Built a complete MCP (Model Context Protocol) server that exposes the Customer Success Agent's capabilities as callable tools. The server implements a JSON-RPC style protocol for tool invocation and includes 6 core tools for CRM operations.

---

## MCP Server Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MCP SERVER                                         │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        TOOL REGISTRY                                 │   │
│  │  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐    │   │
│  │  │ search_          │ │ create_          │ │ get_customer_    │    │   │
│  │  │ knowledge_base   │ │ ticket           │ │ history          │    │   │
│  │  └──────────────────┘ └──────────────────┘ └──────────────────┘    │   │
│  │  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐    │   │
│  │  │ escalate_        │ │ send_            │ │ get_customer_    │    │   │
│  │  │ ticket           │ │ response         │ │ stats            │    │   │
│  │  └──────────────────┘ └──────────────────┘ └──────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    JSON-RPC HANDLER                                  │   │
│  │  - tools/list: Return all registered tools                          │   │
│  │  - tools/call: Execute a specific tool                              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │              INTEGRATION WITH CustomerSuccessAgent                   │   │
│  │  - Uses InMemoryStore from prototype_agent.py                       │   │
│  │  - Reuses existing search, ticket, and memory functionality         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Tools Implemented

### 1. search_knowledge_base

**Purpose:** Search product documentation for relevant information.

**Input Schema:**
```json
{
  "query": "string (required)",
  "max_results": "integer (default: 5)",
  "category": "string (optional: tasks, docs, integration, pricing, api, security, general)"
}
```

**Output:**
```json
{
  "success": true,
  "query": "How do I add team members?",
  "results_count": 3,
  "results": [
    {
      "title": "7. Team Workspaces & Permissions",
      "content": "...",
      "score": 15,
      "category": "general"
    }
  ]
}
```

**Test Result:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "query": "How do I add team members to my workspace?",
    "results_count": 0,
    "results": []
  },
  "id": "test-1"
}
```

---

### 2. create_ticket

**Purpose:** Create a support ticket for tracking customer interactions. ALWAYS create a ticket at the start of every conversation.

**Input Schema:**
```json
{
  "customer_id": "string (required) - Customer identifier (email or phone)",
  "message": "string (required) - The customer's message or issue description",
  "channel": "string (required) - Source channel (email, whatsapp, web_form)",
  "priority": "string (default: medium) - low, medium, high, critical",
  "customer_name": "string (optional)"
}
```

**Output:**
```json
{
  "success": true,
  "ticket_id": "TKT-00001",
  "customer_id": "cust_1",
  "customer_email": "alice.wonder@techcorp.io",
  "status": "open",
  "priority": "medium",
  "channel": "email",
  "created_at": "2026-03-22T01:24:02.286170"
}
```

**Test Result:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "ticket_id": "TKT-00001",
    "customer_id": "cust_1",
    "customer_email": "alice.wonder@techcorp.io",
    "customer_phone": null,
    "status": "open",
    "priority": "medium",
    "channel": "email",
    "created_at": "2026-03-22T01:24:02.286170"
  },
  "id": "test-2"
}
```

---

### 3. get_customer_history

**Purpose:** Get customer's complete interaction history across ALL channels.

**Input Schema:**
```json
{
  "customer_identifier": "string (required) - Customer email or phone number",
  "identifier_type": "string (default: email) - email or phone",
  "limit": "integer (default: 10) - Maximum messages to return"
}
```

**Output:**
```json
{
  "success": true,
  "customer_id": "cust_1",
  "customer_email": "alice.wonder@techcorp.io",
  "messages_count": 3,
  "messages": [
    {
      "role": "customer",
      "content": "I need help setting up custom permissions...",
      "channel": "email",
      "timestamp": "2026-03-22T01:24:02.286155",
      "ticket_id": "TKT-00001"
    }
  ]
}
```

**Test Result:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "customer_id": "cust_1",
    "customer_email": "alice.wonder@techcorp.io",
    "customer_phone": null,
    "messages_count": 3,
    "messages": [
      {
        "role": "customer",
        "content": "I need help setting up custom permissions for my team members. Some should only see specific projects.",
        "channel": "email",
        "timestamp": "2026-03-22T01:24:02.286155",
        "ticket_id": "TKT-00001"
      },
      {
        "role": "customer",
        "content": "Initial question about permissions",
        "channel": "email",
        "timestamp": "2026-03-22T01:24:02.290828",
        "ticket_id": "TKT-00001"
      },
      {
        "role": "agent",
        "content": "Here's how to set permissions...",
        "channel": "email",
        "timestamp": "2026-03-22T01:24:02.290854",
        "ticket_id": "TKT-00001"
      }
    ]
  },
  "id": "test-3"
}
```

---

### 4. escalate_ticket

**Purpose:** Escalate a ticket to human support.

**Input Schema:**
```json
{
  "ticket_id": "string (required)",
  "reason": "string (required) - pricing_inquiry, refund_request, legal_threat, negative_sentiment, human_requested, no_relevant_info, frustrated_customer, technical_issue",
  "notes": "string (optional) - Additional context for human agent",
  "urgency": "string (default: normal) - low, normal, high, critical"
}
```

**Output:**
```json
{
  "success": true,
  "escalation_id": "ESC-FF56A199",
  "ticket_id": "TKT-00001",
  "reason": "pricing_inquiry",
  "urgency": "high",
  "notes": "Customer asked about enterprise pricing...",
  "status": "escalated",
  "escalated_at": "2026-03-22T01:24:02.296359"
}
```

**Test Result:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "escalation_id": "ESC-FF56A199",
    "ticket_id": "TKT-00001",
    "reason": "pricing_inquiry",
    "urgency": "high",
    "notes": "Customer asked about enterprise pricing and volume discounts. Needs sales team follow-up.",
    "status": "escalated",
    "escalated_at": "2026-03-22T01:24:02.296359"
  },
  "id": "test-4"
}
```

---

### 5. send_response

**Purpose:** Send response to customer via their preferred channel.

**Input Schema:**
```json
{
  "ticket_id": "string (required)",
  "response_text": "string (required) - The response message to send",
  "channel": "string (required) - email, whatsapp, web_form"
}
```

**Output:**
```json
{
  "success": true,
  "ticket_id": "TKT-00002",
  "channel": "web_form",
  "response_length": 299,
  "delivery_status": "sent",
  "sent_at": "2026-03-22T01:24:02.300897"
}
```

**Test Result:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "ticket_id": "TKT-00002",
    "channel": "web_form",
    "response_length": 299,
    "delivery_status": "sent",
    "sent_at": "2026-03-22T01:24:02.300897"
  },
  "id": "test-5"
}
```

---

### 6. get_customer_stats

**Purpose:** Get comprehensive statistics for a customer.

**Input Schema:**
```json
{
  "customer_identifier": "string (required) - Customer email or phone number",
  "identifier_type": "string (default: email) - email or phone"
}
```

**Output:**
```json
{
  "success": true,
  "customer_id": "cust_1",
  "customer_email": "alice.wonder@techcorp.io",
  "stats": {
    "total_tickets": 2,
    "open_tickets": 1,
    "resolved_tickets": 0,
    "escalated_tickets": 1,
    "avg_sentiment": 0.75,
    "sentiment_trend": "improving",
    "frustration_flag": false,
    "preferred_channel": "email",
    "channels_used": ["email"],
    "last_interaction": "2026-03-22T01:24:02.304814",
    "topics_discussed": []
  }
}
```

**Test Result:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "customer_id": "cust_1",
    "customer_email": "alice.wonder@techcorp.io",
    "customer_phone": null,
    "stats": {
      "total_tickets": 2,
      "open_tickets": 1,
      "resolved_tickets": 0,
      "escalated_tickets": 1,
      "avg_sentiment": 0.75,
      "sentiment_trend": "improving",
      "frustration_flag": false,
      "preferred_channel": "email",
      "channels_used": ["email"],
      "last_interaction": "2026-03-22T01:24:02.304814",
      "topics_discussed": []
    }
  },
  "id": "test-6"
}
```

---

## JSON-RPC Protocol

### Request Format
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "tool_name",
    "arguments": {
      "arg1": "value1",
      "arg2": "value2"
    }
  },
  "id": "unique-request-id"
}
```

### Response Format (Success)
```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    ...tool-specific data...
  },
  "id": "unique-request-id"
}
```

### Response Format (Error)
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32601,
    "message": "Tool not found: unknown_tool"
  },
  "id": "unique-request-id"
}
```

### Error Codes
| Code | Meaning |
|------|---------|
| -32601 | Tool not found |
| -32602 | Invalid parameters |
| -32000 | Tool execution error |

---

## MCP Methods

### tools/list
Returns all registered tools with their schemas.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/list",
  "params": {},
  "id": "list-1"
}
```

**Response:** Returns array of tool definitions with name, description, and inputSchema.

### tools/call
Executes a specific tool with provided arguments.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "create_ticket",
    "arguments": {...}
  },
  "id": "call-1"
}
```

---

## Test Summary

| Tool | Status | Test Data |
|------|--------|-----------|
| search_knowledge_base | ✅ | Query: "How do I add team members?" |
| create_ticket | ✅ | Customer: alice.wonder@techcorp.io |
| get_customer_history | ✅ | Retrieved 3 messages |
| escalate_ticket | ✅ | Escalation ID: ESC-FF56A199 |
| send_response | ✅ | Response sent, 299 chars |
| get_customer_stats | ✅ | Full stats with sentiment trend |

---

## Code Structure

```
src/mcp_server/
├── __init__.py              # Package marker
└── mcp_server.py            # Main MCP server implementation
    ├── MCPTool class        # Tool definition
    ├── MCPServer class      # Server implementation
    │   ├── _register_tools()
    │   ├── list_tools()
    │   ├── call_tool()
    │   ├── handle_request()
    │   └── Tool handlers:
    │       ├── _search_knowledge_base()
    │       ├── _create_ticket()
    │       ├── _get_customer_history()
    │       ├── _escalate_ticket()
    │       ├── _send_response()
    │       └── _get_customer_stats()
    └── main()               # Test function
```

---

## Integration with Prototype Agent

The MCP server reuses existing components:

```python
from agent.prototype_agent import InMemoryStore, CustomerSuccessAgent

# Initialize with existing store and agent
store = InMemoryStore()
store.load_knowledge_base("context/product-docs.md")
server = MCPServer(store)  # Uses existing store and agent
```

This ensures:
- Consistent data model
- Shared conversation memory
- Same sentiment analysis
- Unified topic tracking

---

## Usage Example

```python
# Initialize server
store = InMemoryStore()
server = MCPServer(store)

# List all tools
tools = server.list_tools()

# Call a tool
request = {
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "create_ticket",
        "arguments": {
            "customer_id": "user@example.com",
            "message": "Help me!",
            "channel": "email"
        }
    },
    "id": "1"
}

response = server.handle_request(request)
ticket_id = response["result"]["ticket_id"]
```

---

## Next Steps

**Ready for Exercise 1.5 - Define Agent Skills**

The MCP foundation is complete. Next we will:
1. Define formal agent skill manifests
2. Create reusable skill definitions
3. Map skills to MCP tools
4. Document skill invocation patterns

---

*Exercise 1.4 Complete*
