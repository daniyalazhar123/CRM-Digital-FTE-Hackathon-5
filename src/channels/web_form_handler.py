"""
CRM Digital FTE - Web Form Handler
Phase 2: Specialization — Step 7

Handles web form submissions via FastAPI endpoints.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/support", tags=["support-form"])


class SupportFormSubmission(BaseModel):
    """Support form submission model with validation."""
    name: str
    email: EmailStr
    subject: str
    category: str
    message: str
    priority: Optional[str] = 'medium'
    
    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Name must be at least 2 characters')
        return v.strip()
    
    @validator('message')
    def message_must_have_content(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError('Message must be at least 10 characters')
        return v.strip()
    
    @validator('category')
    def category_must_be_valid(cls, v):
        valid_categories = ['how-to', 'technical', 'billing', 'bug-report', 'other']
        if v not in valid_categories:
            raise ValueError(f'Category must be one of: {valid_categories}')
        return v


class SupportFormResponse(BaseModel):
    """Response model for form submission."""
    ticket_id: str
    message: str
    estimated_response_time: str


@router.post("/submit", response_model=SupportFormResponse)
async def submit_support_form(submission: SupportFormSubmission):
    """
    Handle support form submission.
    
    This endpoint:
    1. Validates the submission
    2. Creates a ticket in the system
    3. Processes with CRM agent
    4. Returns confirmation to user
    """
    try:
        logger.info(f"Processing support form from {submission.email}")
        
        # Import agent processing
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agent'))
        from crm_agent import process_message
        
        # Process with CRM agent
        result = process_message(
            customer_email=submission.email,
            message=f"Subject: {submission.subject}\nCategory: {submission.category}\n\n{submission.message}",
            channel="web_form",
            customer_name=submission.name
        )
        
        logger.info(f"Ticket created: {result['ticket_id']}")
        
        return SupportFormResponse(
            ticket_id=result['ticket_id'],
            message="Thank you for contacting us! Our AI assistant will respond shortly.",
            estimated_response_time="Usually within 5 minutes"
        )
        
    except Exception as e:
        logger.error(f"Form submission error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ticket/{ticket_id}")
async def get_ticket_status(ticket_id: str):
    """
    Get status and conversation history for a ticket.
    """
    try:
        # Import database
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'db'))
        from database import CRMDatabase
        
        db = CRMDatabase()
        ticket = db.get_ticket(ticket_id)
        
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        # Get messages
        messages = db.get_customer_history(ticket['customer_id'], limit=20)
        
        return {
            'ticket_id': ticket_id,
            'status': ticket['status'],
            'messages': messages,
            'created_at': str(ticket['created_at']),
            'last_updated': str(ticket.get('resolved_at') or ticket['created_at'])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get ticket error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories")
async def get_categories():
    """Get available support categories."""
    return {
        'categories': [
            {'value': 'how-to', 'label': 'How-To Question'},
            {'value': 'technical', 'label': 'Technical Support'},
            {'value': 'billing', 'label': 'Billing Inquiry'},
            {'value': 'bug-report', 'label': 'Bug Report'},
            {'value': 'other', 'label': 'Other'}
        ]
    }
