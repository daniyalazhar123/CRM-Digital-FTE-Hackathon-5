"""
CRM Digital FTE - Metrics Collector
Phase 2: Specialization

Background metrics collection worker.
Collects and aggregates performance metrics for monitoring.
"""

import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


# =============================================================================
# METRICS STORE
# =============================================================================

class MetricsStore:
    """
    In-memory metrics store with aggregation.
    
    Collects:
    - Response times
    - Escalation rates
    - Channel distribution
    - Error rates
    - Sentiment trends
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MetricsStore, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self._initialize()
    
    def _initialize(self):
        """Initialize metrics store."""
        self.response_times = []  # List of (timestamp, duration_ms, channel)
        self.escalations = []  # List of (timestamp, reason, channel)
        self.errors = []  # List of (timestamp, error_type, channel)
        self.messages_by_channel = defaultdict(int)  # channel -> count
        self.sentiment_scores = []  # List of (timestamp, score, customer_id)
        self.tickets_created = 0
        self.tickets_resolved = 0
        self.initialized = True
        logger.info("✓ Metrics store initialized")
    
    def record_response_time(self, duration_ms: float, channel: str):
        """Record API response time."""
        self.response_times.append((datetime.utcnow(), duration_ms, channel))
        self.messages_by_channel[channel] += 1
        
        # Keep only last 1000 entries
        if len(self.response_times) > 1000:
            self.response_times = self.response_times[-1000:]
    
    def record_escalation(self, reason: str, channel: str):
        """Record ticket escalation."""
        self.escalations.append((datetime.utcnow(), reason, channel))
        
        # Keep only last 500 entries
        if len(self.escalations) > 500:
            self.escalations = self.escalations[-500:]
    
    def record_error(self, error_type: str, channel: str):
        """Record error occurrence."""
        self.errors.append((datetime.utcnow(), error_type, channel))
        
        # Keep only last 500 entries
        if len(self.errors) > 500:
            self.errors = self.errors[-500:]
    
    def record_sentiment(self, score: float, customer_id: str):
        """Record customer sentiment score."""
        self.sentiment_scores.append((datetime.utcnow(), score, customer_id))
        
        # Keep only last 2000 entries
        if len(self.sentiment_scores) > 2000:
            self.sentiment_scores = self.sentiment_scores[-2000:]
    
    def increment_tickets_created(self):
        """Increment tickets created counter."""
        self.tickets_created += 1
    
    def increment_tickets_resolved(self):
        """Increment tickets resolved counter."""
        self.tickets_resolved += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        now = datetime.utcnow()
        last_hour = now - timedelta(hours=1)
        
        # Response time stats
        recent_responses = [rt for rt in self.response_times if rt[0] >= last_hour]
        avg_response_time = sum(rt[1] for rt in recent_responses) / len(recent_responses) if recent_responses else 0
        p95_response_time = sorted([rt[1] for rt in recent_responses])[int(len(recent_responses) * 0.95)] if recent_responses else 0
        
        # Escalation rate
        total_messages = sum(self.messages_by_channel.values())
        total_escalations = len([e for e in self.escalations if e[0] >= last_hour])
        escalation_rate = total_escalations / total_messages if total_messages > 0 else 0
        
        # Error rate
        total_errors = len([e for e in self.errors if e[0] >= last_hour])
        error_rate = total_errors / total_messages if total_messages > 0 else 0
        
        # Average sentiment
        recent_sentiment = [s for s in self.sentiment_scores if s[0] >= last_hour]
        avg_sentiment = sum(s[1] for s in recent_sentiment) / len(recent_sentiment) if recent_sentiment else 0
        
        return {
            "timestamp": now.isoformat(),
            "period": "last_hour",
            "total_messages": total_messages,
            "avg_response_time_ms": round(avg_response_time, 2),
            "p95_response_time_ms": round(p95_response_time, 2),
            "total_escalations": total_escalations,
            "escalation_rate": round(escalation_rate, 4),
            "total_errors": total_errors,
            "error_rate": round(error_rate, 4),
            "avg_sentiment": round(avg_sentiment, 4),
            "tickets_created": self.tickets_created,
            "tickets_resolved": self.tickets_resolved,
            "messages_by_channel": dict(self.messages_by_channel)
        }
    
    def get_channel_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics broken down by channel."""
        now = datetime.utcnow()
        last_hour = now - timedelta(hours=1)
        
        channel_metrics = {}
        
        for channel in ['email', 'whatsapp', 'web_form']:
            channel_messages = [rt for rt in self.response_times if rt[2] == channel and rt[0] >= last_hour]
            channel_escalations = [e for e in self.escalations if e[2] == channel and e[0] >= last_hour]
            channel_errors = [e for e in self.errors if e[2] == channel and e[0] >= last_hour]
            channel_sentiment = [s for s in self.sentiment_scores if s[0] >= last_hour]
            
            avg_response = sum(cm[1] for cm in channel_messages) / len(channel_messages) if channel_messages else 0
            
            channel_metrics[channel] = {
                "total_messages": len(channel_messages),
                "avg_response_time_ms": round(avg_response, 2),
                "escalations": len(channel_escalations),
                "errors": len(channel_errors),
                "avg_sentiment": round(sum(s[1] for s in channel_sentiment) / len(channel_sentiment), 4) if channel_sentiment else 0
            }
        
        return channel_metrics
    
    def reset(self):
        """Reset all metrics (for testing)."""
        self.response_times.clear()
        self.escalations.clear()
        self.errors.clear()
        self.messages_by_channel.clear()
        self.sentiment_scores.clear()
        self.tickets_created = 0
        self.tickets_resolved = 0


# =============================================================================
# METRICS COLLECTOR WORKER
# =============================================================================

class MetricsCollector:
    """
    Background metrics collector worker.
    
    Periodically aggregates metrics and publishes to Kafka/Prometheus.
    """
    
    def __init__(self):
        self.store = MetricsStore()
        self.running = False
        logger.info("✓ Metrics collector initialized")
    
    async def start(self, interval_seconds: int = 60):
        """Start background metrics collection."""
        import asyncio
        
        self.running = True
        logger.info(f"Starting metrics collector (interval: {interval_seconds}s)")
        
        while self.running:
            try:
                await self._collect_and_publish()
                await asyncio.sleep(interval_seconds)
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                await asyncio.sleep(10)
    
    async def stop(self):
        """Stop metrics collection."""
        self.running = False
        logger.info("Metrics collector stopped")
    
    async def _collect_and_publish(self):
        """Collect metrics and publish to Kafka."""
        summary = self.store.get_summary()
        channel_metrics = self.store.get_channel_metrics()
        
        logger.info(f"Metrics summary: {summary['total_messages']} messages, "
                    f"{summary['avg_response_time_ms']}ms avg, "
                    f"{summary['escalation_rate']*100:.1f}% escalation rate")
        
        # In production, publish to Kafka
        try:
            from workers.kafka_producer import get_producer
            producer = get_producer()
            
            await producer.publish_metric({
                "type": "summary",
                "data": summary
            })
            
            for channel, metrics in channel_metrics.items():
                await producer.publish_metric({
                    "type": "channel",
                    "channel": channel,
                    "data": metrics
                })
        except Exception as e:
            logger.warning(f"Failed to publish metrics to Kafka: {e}")


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_metrics_store() -> MetricsStore:
    """Get singleton metrics store instance."""
    return MetricsStore()


def record_response_time(duration_ms: float, channel: str):
    """Convenience function to record response time."""
    store = get_metrics_store()
    store.record_response_time(duration_ms, channel)


def record_escalation(reason: str, channel: str):
    """Convenience function to record escalation."""
    store = get_metrics_store()
    store.record_escalation(reason, channel)


def record_error(error_type: str, channel: str):
    """Convenience function to record error."""
    store = get_metrics_store()
    store.record_error(error_type, channel)


def record_sentiment(score: float, customer_id: str):
    """Convenience function to record sentiment."""
    store = get_metrics_store()
    store.record_sentiment(score, customer_id)
