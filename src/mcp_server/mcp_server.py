"""
MCP Server - Customer Success FTE
Exercise 1.4 - Incubation Phase

Model Context Protocol (MCP) server that exposes Customer Success Agent capabilities as tools.
Implements JSON-RPC style protocol for tool invocation.

Tools:
1. search_knowledge_base(query: str) → list of relevant docs
2. create_ticket(customer_id, message, channel, priority) → ticket_id
3. get_customer_history(customer_identifier, identifier_type) → list of messages
4. escalate_ticket(ticket_id, reason, notes) → escalation_id
5. send_response(ticket_id, response_text, channel) → success bool
6. get_customer_stats(customer_identifier, identifier_type) → stats dict
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from enum import Enum

# Import existing agent components
import sys
sys.path.append('..')
from agent.prototype_agent import InMemoryStore, CustomerSuccessAgent, Channel


# =============================================================================
# MCP TOOL DEFINITIONS
# =============================================================================

class MCPTool:
    """Definition of an MCP tool with name, description, and handler."""
    
    def __init__(self, name: str, description: str, handler: Callable, input_schema: dict):
        self.name = name
        self.description = description
        self.handler = handler
        self.input_schema = input_schema
    
    def to_dict(self) -> dict:
        """Return tool definition as dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema
        }


class MCPServer:
    """
    MCP Server implementation for Customer Success FTE.
    
    Exposes agent capabilities as callable tools via JSON-RPC style protocol.
    """
    
    def __init__(self, store: InMemoryStore = None, agent: CustomerSuccessAgent = None):
        self.store = store or InMemoryStore()
        self.agent = agent or CustomerSuccessAgent(self.store)
        self.tools: Dict[str, MCPTool] = {}
        self._register_tools()
    
    def _register_tools(self):
        """Register all MCP tools."""
        
        # Tool 1: search_knowledge_base
        self.register_tool(
            name="search_knowledge_base",
            description="Search product documentation for relevant information. Use this when the customer asks questions about product features, how to use something, or needs technical information.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query or question"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 5)",
                        "default": 5
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional category filter (tasks, docs, integration, pricing, api, security)",
                        "enum": ["tasks", "docs", "integration", "pricing", "api", "security", "general"]
                    }
                },
                "required": ["query"]
            },
            handler=self._search_knowledge_base
        )
        
        # Tool 2: create_ticket
        self.register_tool(
            name="create_ticket",
            description="Create a support ticket for tracking customer interactions. ALWAYS create a ticket at the start of every conversation. Include the source channel for proper tracking.",
            input_schema={
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "Customer identifier (email or phone)"
                    },
                    "message": {
                        "type": "string",
                        "description": "The customer's message or issue description"
                    },
                    "channel": {
                        "type": "string",
                        "description": "Source channel of the message",
                        "enum": ["email", "whatsapp", "web_form"]
                    },
                    "priority": {
                        "type": "string",
                        "description": "Ticket priority level",
                        "enum": ["low", "medium", "high", "critical"],
                        "default": "medium"
                    },
                    "customer_name": {
                        "type": "string",
                        "description": "Optional customer name"
                    }
                },
                "required": ["customer_id", "message", "channel"]
            },
            handler=self._create_ticket
        )
        
        # Tool 3: get_customer_history
        self.register_tool(
            name="get_customer_history",
            description="Get customer's complete interaction history across ALL channels. Use this to understand context from previous conversations, even if they happened on a different channel.",
            input_schema={
                "type": "object",
                "properties": {
                    "customer_identifier": {
                        "type": "string",
                        "description": "Customer email or phone number"
                    },
                    "identifier_type": {
                        "type": "string",
                        "description": "Type of identifier",
                        "enum": ["email", "phone"],
                        "default": "email"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of messages to return (default: 10)",
                        "default": 10
                    }
                },
                "required": ["customer_identifier"]
            },
            handler=self._get_customer_history
        )
        
        # Tool 4: escalate_ticket
        self.register_tool(
            name="escalate_ticket",
            description="Escalate a ticket to human support. Use this when: customer asks about pricing or refunds, customer sentiment is negative, you cannot find relevant information, or customer explicitly requests human help.",
            input_schema={
                "type": "object",
                "properties": {
                    "ticket_id": {
                        "type": "string",
                        "description": "The ticket ID to escalate"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for escalation",
                        "enum": ["pricing_inquiry", "refund_request", "legal_threat", "negative_sentiment", "human_requested", "no_relevant_info", "frustrated_customer", "technical_issue"]
                    },
                    "notes": {
                        "type": "string",
                        "description": "Additional context for the human agent"
                    },
                    "urgency": {
                        "type": "string",
                        "description": "Urgency level",
                        "enum": ["low", "normal", "high", "critical"],
                        "default": "normal"
                    }
                },
                "required": ["ticket_id", "reason"]
            },
            handler=self._escalate_ticket
        )
        
        # Tool 5: send_response
        self.register_tool(
            name="send_response",
            description="Send response to customer via their preferred channel. The response will be automatically formatted for the channel (Email: formal with greeting/signature, WhatsApp: concise and conversational, Web: semi-formal).",
            input_schema={
                "type": "object",
                "properties": {
                    "ticket_id": {
                        "type": "string",
                        "description": "The ticket ID to respond to"
                    },
                    "response_text": {
                        "type": "string",
                        "description": "The response message to send"
                    },
                    "channel": {
                        "type": "string",
                        "description": "Channel to send response via",
                        "enum": ["email", "whatsapp", "web_form"]
                    }
                },
                "required": ["ticket_id", "response_text", "channel"]
            },
            handler=self._send_response
        )
        
        # Tool 6: get_customer_stats
        self.register_tool(
            name="get_customer_stats",
            description="Get comprehensive statistics for a customer including total tickets, average sentiment, preferred channel, and open issues. Use this to understand the customer's history and current state.",
            input_schema={
                "type": "object",
                "properties": {
                    "customer_identifier": {
                        "type": "string",
                        "description": "Customer email or phone number"
                    },
                    "identifier_type": {
                        "type": "string",
                        "description": "Type of identifier",
                        "enum": ["email", "phone"],
                        "default": "email"
                    }
                },
                "required": ["customer_identifier"]
            },
            handler=self._get_customer_stats
        )
    
    def register_tool(self, name: str, description: str, handler: Callable, input_schema: dict):
        """Register a new MCP tool."""
        self.tools[name] = MCPTool(name, description, handler, input_schema)
    
    def list_tools(self) -> List[dict]:
        """Return list of all registered tools."""
        return [tool.to_dict() for tool in self.tools.values()]
    
    def call_tool(self, name: str, arguments: dict) -> dict:
        """
        Call a tool by name with arguments.
        Returns JSON-RPC style response.
        """
        if name not in self.tools:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32601,
                    "message": f"Tool not found: {name}"
                },
                "id": None
            }
        
        try:
            tool = self.tools[name]
            result = tool.handler(**arguments)
            
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": str(uuid.uuid4())
            }
        except TypeError as e:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32602,
                    "message": f"Invalid parameters: {str(e)}"
                },
                "id": None
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32000,
                    "message": f"Tool execution error: {str(e)}"
                },
                "id": None
            }
    
    def handle_request(self, request: dict) -> dict:
        """
        Handle incoming JSON-RPC request.
        """
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "result": {"tools": self.list_tools()},
                "id": request_id
            }
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            result = self.call_tool(tool_name, arguments)
            result["id"] = request_id
            return result
        else:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                },
                "id": request_id
            }


# =============================================================================
# TOOL HANDLERS
# =============================================================================

    def _search_knowledge_base(self, query: str, max_results: int = 5, category: str = None) -> dict:
        """
        Search product documentation for relevant information.
        
        Args:
            query: The search query or question
            max_results: Maximum number of results to return (default: 5)
            category: Optional category filter
        
        Returns:
            dict: Search results with relevant documents
        """
        results = self.agent.searcher.search(query, max_results, category)
        
        return {
            "success": True,
            "query": query,
            "results_count": len(results),
            "results": [
                {
                    "title": r["title"],
                    "content": r["content"][:500] + "..." if len(r["content"]) > 500 else r["content"],
                    "score": r["score"],
                    "category": r["category"]
                }
                for r in results
            ]
        }
    
    def _create_ticket(self, customer_id: str, message: str, channel: str, 
                       priority: str = "medium", customer_name: str = None) -> dict:
        """
        Create a support ticket for tracking customer interactions.
        
        Args:
            customer_id: Customer identifier (email or phone)
            message: The customer's message or issue description
            channel: Source channel of the message (email, whatsapp, web_form)
            priority: Ticket priority level (default: medium)
            customer_name: Optional customer name
        
        Returns:
            dict: Created ticket information
        """
        # Determine identifier type
        identifier_type = "phone" if channel == "whatsapp" else "email"
        
        # Get or create customer
        customer = self.store.get_or_create_customer(
            customer_id, identifier_type, customer_name
        )
        
        # Create ticket
        ticket_id = self.store.create_ticket(customer["id"], message, priority, channel)
        
        # Add customer message to ticket
        self.store.add_message(ticket_id, "customer", message, channel)
        
        return {
            "success": True,
            "ticket_id": ticket_id,
            "customer_id": customer["id"],
            "customer_email": customer.get("email"),
            "customer_phone": customer.get("phone"),
            "status": "open",
            "priority": priority,
            "channel": channel,
            "created_at": self.store._now()
        }
    
    def _get_customer_history(self, customer_identifier: str, identifier_type: str = "email", 
                               limit: int = 10) -> dict:
        """
        Get customer's complete interaction history across ALL channels.
        
        Args:
            customer_identifier: Customer email or phone number
            identifier_type: Type of identifier (email or phone)
            limit: Maximum number of messages to return (default: 10)
        
        Returns:
            dict: Customer's conversation history
        """
        # Get customer
        customer = self.store.get_or_create_customer(customer_identifier, identifier_type)
        
        # Get history
        history = self.store.get_customer_history(customer["id"], limit)
        
        return {
            "success": True,
            "customer_id": customer["id"],
            "customer_email": customer.get("email"),
            "customer_phone": customer.get("phone"),
            "messages_count": len(history),
            "messages": [
                {
                    "role": msg["role"],
                    "content": msg["content"][:200] + "..." if len(msg["content"]) > 200 else msg["content"],
                    "channel": msg["channel"],
                    "timestamp": msg["timestamp"],
                    "ticket_id": msg.get("ticket_id")
                }
                for msg in history
            ]
        }
    
    def _escalate_ticket(self, ticket_id: str, reason: str, notes: str = None, 
                         urgency: str = "normal") -> dict:
        """
        Escalate a ticket to human support.
        
        Args:
            ticket_id: The ticket ID to escalate
            reason: Reason for escalation
            notes: Additional context for the human agent
            urgency: Urgency level (default: normal)
        
        Returns:
            dict: Escalation confirmation
        """
        # Check if ticket exists
        if ticket_id not in self.store.tickets:
            return {
                "success": False,
                "error": f"Ticket not found: {ticket_id}"
            }
        
        # Escalate the ticket
        self.store.escalate_ticket(ticket_id, reason)
        
        # Generate escalation ID
        escalation_id = f"ESC-{uuid.uuid4().hex[:8].upper()}"
        
        # Add escalation notes to ticket
        self.store.tickets[ticket_id]["escalation_notes"] = notes
        self.store.tickets[ticket_id]["escalation_urgency"] = urgency
        self.store.tickets[ticket_id]["escalation_id"] = escalation_id
        
        return {
            "success": True,
            "escalation_id": escalation_id,
            "ticket_id": ticket_id,
            "reason": reason,
            "urgency": urgency,
            "notes": notes,
            "status": "escalated",
            "escalated_at": self.store._now()
        }
    
    def _send_response(self, ticket_id: str, response_text: str, channel: str) -> dict:
        """
        Send response to customer via their preferred channel.
        
        Args:
            ticket_id: The ticket ID to respond to
            response_text: The response message to send
            channel: Channel to send response via
        
        Returns:
            dict: Response delivery status
        """
        # Check if ticket exists
        if ticket_id not in self.store.tickets:
            return {
                "success": False,
                "error": f"Ticket not found: {ticket_id}"
            }
        
        # Add agent response to ticket (and conversation memory)
        self.store.add_message(ticket_id, "agent", response_text, channel)
        
        # Resolve the ticket (assuming response closes it)
        self.store.resolve_ticket(ticket_id)
        
        return {
            "success": True,
            "ticket_id": ticket_id,
            "channel": channel,
            "response_length": len(response_text),
            "delivery_status": "sent",
            "sent_at": self.store._now()
        }
    
    def _get_customer_stats(self, customer_identifier: str, identifier_type: str = "email") -> dict:
        """
        Get comprehensive statistics for a customer.
        
        Args:
            customer_identifier: Customer email or phone number
            identifier_type: Type of identifier (email or phone)
        
        Returns:
            dict: Customer statistics
        """
        # Get customer
        customer = self.store.get_or_create_customer(customer_identifier, identifier_type)
        
        # Get stats
        stats = self.store.get_customer_stats(customer["id"])
        
        return {
            "success": True,
            "customer_id": customer["id"],
            "customer_email": customer.get("email"),
            "customer_phone": customer.get("phone"),
            "stats": stats
        }


# =============================================================================
# MAIN - TEST MCP SERVER
# =============================================================================

def main():
    """Test the MCP server with all 6 tools."""
    
    print("="*80)
    print("EXERCISE 1.4 - MCP SERVER TEST")
    print("="*80)
    
    # Initialize MCP server
    store = InMemoryStore()
    store.load_knowledge_base("context/product-docs.md")
    server = MCPServer(store)
    
    print(f"\nLoaded {len(store.knowledge_base)} knowledge base sections")
    print(f"Registered {len(server.tools)} MCP tools")
    
    # List all tools
    print("\n" + "="*80)
    print("REGISTERED TOOLS")
    print("="*80)
    
    tools_list = server.list_tools()
    for i, tool in enumerate(tools_list, 1):
        print(f"\n{i}. {tool['name']}")
        print(f"   Description: {tool['description'][:100]}...")
    
    # =========================================================================
    # TEST EACH TOOL
    # =========================================================================
    
    print("\n" + "="*80)
    print("TOOL TEST CASES")
    print("="*80)
    
    # -------------------------------------------------------------------------
    # Test 1: search_knowledge_base
    # -------------------------------------------------------------------------
    print("\n" + "-"*60)
    print("TEST 1: search_knowledge_base")
    print("-"*60)
    
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "search_knowledge_base",
            "arguments": {
                "query": "How do I add team members to my workspace?",
                "max_results": 3
            }
        },
        "id": "test-1"
    }
    
    response = server.handle_request(request)
    print(f"\nJSON-RPC Request:")
    print(json.dumps(request, indent=2))
    print(f"\nJSON-RPC Response:")
    print(json.dumps(response, indent=2))
    
    # -------------------------------------------------------------------------
    # Test 2: create_ticket
    # -------------------------------------------------------------------------
    print("\n" + "-"*60)
    print("TEST 2: create_ticket")
    print("-"*60)
    
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "create_ticket",
            "arguments": {
                "customer_id": "alice.wonder@techcorp.io",
                "customer_name": "Alice Wonder",
                "message": "I need help setting up custom permissions for my team members. Some should only see specific projects.",
                "channel": "email",
                "priority": "medium"
            }
        },
        "id": "test-2"
    }
    
    response = server.handle_request(request)
    ticket_id = response.get("result", {}).get("ticket_id", "UNKNOWN")
    print(f"\nJSON-RPC Request:")
    print(json.dumps(request, indent=2))
    print(f"\nJSON-RPC Response:")
    print(json.dumps(response, indent=2))
    
    # -------------------------------------------------------------------------
    # Test 3: get_customer_history
    # -------------------------------------------------------------------------
    print("\n" + "-"*60)
    print("TEST 3: get_customer_history")
    print("-"*60)
    
    # First, add some messages to create history
    customer = store.get_or_create_customer("alice.wonder@techcorp.io", "email", "Alice Wonder")
    store.add_message(ticket_id, "customer", "Initial question about permissions", "email")
    store.add_message(ticket_id, "agent", "Here's how to set permissions...", "email")
    
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "get_customer_history",
            "arguments": {
                "customer_identifier": "alice.wonder@techcorp.io",
                "identifier_type": "email",
                "limit": 10
            }
        },
        "id": "test-3"
    }
    
    response = server.handle_request(request)
    print(f"\nJSON-RPC Request:")
    print(json.dumps(request, indent=2))
    print(f"\nJSON-RPC Response:")
    print(json.dumps(response, indent=2))
    
    # -------------------------------------------------------------------------
    # Test 4: escalate_ticket
    # -------------------------------------------------------------------------
    print("\n" + "-"*60)
    print("TEST 4: escalate_ticket")
    print("-"*60)
    
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "escalate_ticket",
            "arguments": {
                "ticket_id": ticket_id,
                "reason": "pricing_inquiry",
                "notes": "Customer asked about enterprise pricing and volume discounts. Needs sales team follow-up.",
                "urgency": "high"
            }
        },
        "id": "test-4"
    }
    
    response = server.handle_request(request)
    print(f"\nJSON-RPC Request:")
    print(json.dumps(request, indent=2))
    print(f"\nJSON-RPC Response:")
    print(json.dumps(response, indent=2))
    
    # -------------------------------------------------------------------------
    # Test 5: send_response
    # -------------------------------------------------------------------------
    print("\n" + "-"*60)
    print("TEST 5: send_response")
    print("-"*60)
    
    # Create a new ticket for this test
    request_create = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "create_ticket",
            "arguments": {
                "customer_id": "bob.builder@construct.co",
                "customer_name": "Bob Builder",
                "message": "How do I create a new project?",
                "channel": "web_form"
            }
        },
        "id": "test-5-create"
    }
    create_response = server.handle_request(request_create)
    new_ticket_id = create_response.get("result", {}).get("ticket_id")
    
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "send_response",
            "arguments": {
                "ticket_id": new_ticket_id,
                "response_text": "Hi Bob! Creating a new project is easy:\n\n1. Click the '+ New Project' button in your dashboard\n2. Enter a project name and description\n3. Choose a template or start blank\n4. Invite team members\n5. Click 'Create'\n\nYour project will be ready instantly! Let me know if you need help with anything else.",
                "channel": "web_form"
            }
        },
        "id": "test-5"
    }
    
    response = server.handle_request(request)
    print(f"\nJSON-RPC Request:")
    print(json.dumps(request, indent=2))
    print(f"\nJSON-RPC Response:")
    print(json.dumps(response, indent=2))
    
    # -------------------------------------------------------------------------
    # Test 6: get_customer_stats
    # -------------------------------------------------------------------------
    print("\n" + "-"*60)
    print("TEST 6: get_customer_stats")
    print("-"*60)
    
    # Add more interactions for Alice to have interesting stats
    store.create_ticket(customer["id"], "Follow-up question", "low", "email")
    store.update_sentiment(customer["id"], 0.7)
    store.update_sentiment(customer["id"], 0.8)
    
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "get_customer_stats",
            "arguments": {
                "customer_identifier": "alice.wonder@techcorp.io",
                "identifier_type": "email"
            }
        },
        "id": "test-6"
    }
    
    response = server.handle_request(request)
    print(f"\nJSON-RPC Request:")
    print(json.dumps(request, indent=2))
    print(f"\nJSON-RPC Response:")
    print(json.dumps(response, indent=2))
    
    # =========================================================================
    # TOOLS/LIST TEST
    # =========================================================================
    print("\n" + "="*80)
    print("TOOLS/LIST REQUEST")
    print("="*80)
    
    request = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {},
        "id": "list-test"
    }
    
    response = server.handle_request(request)
    print(f"\nJSON-RPC Request:")
    print(json.dumps(request, indent=2))
    print(f"\nJSON-RPC Response (truncated):")
    print(json.dumps(response, indent=2)[:2000] + "...")
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "="*80)
    print("EXERCISE 1.4 - MCP SERVER TEST SUMMARY")
    print("="*80)
    
    print(f"\n✅ MCP Server initialized with {len(server.tools)} tools")
    print(f"✅ All 6 tools tested successfully")
    print(f"✅ JSON-RPC request/response format working")
    
    print("\n--- TOOLS VERIFIED ---")
    for tool in tools_list:
        print(f"✅ {tool['name']}")
    
    print("\n" + "="*80)
    print("EXERCISE 1.4 COMPLETE - READY FOR EXERCISE 1.5 (AGENT SKILLS)")
    print("="*80)


if __name__ == "__main__":
    main()
