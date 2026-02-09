"""
Arize Phoenix Tracing Integration for Legislation RAG
Using Manual Instrumentation with Phoenix SDK
"""

import os
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

# Phoenix SDK imports
try:
    from phoenix.otel import register
    from openinference.instrumentation import using_attributes
    from openinference.semconv.trace import SpanAttributes, OpenInferenceSpanKindValues
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    PHOENIX_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Phoenix SDK not available: {e}")
    PHOENIX_AVAILABLE = False

from config import ARIZE_SPACE_ID, ARIZE_API_KEY, ARIZE_PROJECT_NAME


class ArizeLegislationTracer:
    """Manual instrumentation for Legislation RAG with Phoenix"""
    
    def __init__(self):
        self.tracer = None
        self.tracer_provider = None
        self.enabled = False
        
    def initialize(self) -> bool:
        """Initialize Phoenix tracing with manual instrumentation"""
        if not PHOENIX_AVAILABLE:
            print("❌ Phoenix SDK not installed. Run: pip install arize-phoenix openinference-instrumentation")
            return False
            
        if not ARIZE_API_KEY or not ARIZE_SPACE_ID:
            print("⚠️ Arize credentials not set. Tracing disabled.")
            return False
            
        try:
            # Register Phoenix with Arize backend
            self.tracer_provider = register(
                project_name=ARIZE_PROJECT_NAME,
                endpoint=f"https://app.arize.com/v1/traces",
                headers={
                    "space-id": ARIZE_SPACE_ID,
                    "api-key": ARIZE_API_KEY,
                }
            )
            
            # Get tracer instance
            self.tracer = trace.get_tracer(__name__)
            self.enabled = True
            
            print("✅ Phoenix tracing initialized successfully")
            print(f"   📊 Project: {ARIZE_PROJECT_NAME}")
            print(f"   🔑 Space ID: {ARIZE_SPACE_ID[:20]}...")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize Phoenix: {e}")
            self.enabled = False
            return False


    def trace_rag_query(
        self,
        question: str,
        answer: str,
        method: str,
        confidence: float,
        latency: float,
        sources: List[Dict],
        metadata: Optional[Dict] = None
    ) -> None:
        """Trace a complete RAG query interaction"""
        if not self.enabled or not self.tracer:
            return
            
        try:
            with self.tracer.start_as_current_span(
                "rag_query",
                attributes={
                    SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.CHAIN.value,
                    SpanAttributes.INPUT_VALUE: question,
                    SpanAttributes.OUTPUT_VALUE: answer,
                    "rag.method": method,
                    "rag.confidence": confidence,
                    "rag.latency_ms": latency * 1000,
                    "rag.num_sources": len(sources),
                    "rag.timestamp": datetime.utcnow().isoformat(),
                }
            ) as span:
                # Add metadata if provided
                if metadata:
                    for key, value in metadata.items():
                        span.set_attribute(f"metadata.{key}", str(value))
                
                # Add retrieved documents as attributes
                for idx, source in enumerate(sources[:5]):  # Limit to 5 to avoid overflow
                    span.set_attribute(f"retrieved_document.{idx}.content", source.get("content", "")[:500])
                    span.set_attribute(f"retrieved_document.{idx}.score", source.get("score", 0.0))
                    span.set_attribute(f"retrieved_document.{idx}.metadata", json.dumps(source.get("metadata", {})))
                    
        except Exception as e:
            print(f"⚠️ Error tracing RAG query: {e}")


def trace_retrieval(
    query: str,
    num_results: int = 0,
    top_scores: Optional[list] = None,
    latency_ms: float = 0.0,
):
    """
    Trace the retrieval step (vector search + reranking).
    """
    if not _tracing_enabled or not _tracer:
        return
    
    try:
        with _tracer.start_as_current_span("retrieval") as span:
            span.set_attribute("input.value", query)
            span.set_attribute("retrieval.num_results", num_results)
            span.set_attribute("retrieval.latency_ms", latency_ms)
            span.set_attribute("openinference.span.kind", "RETRIEVER")
            
            if top_scores:
                span.set_attribute("retrieval.top_score", max(top_scores))
                span.set_attribute("retrieval.avg_score", sum(top_scores) / len(top_scores))
                
    except Exception as e:
        logger.warning(f"Tracing error (retrieval): {e}")


def trace_llm_call(
    prompt: str,
    response: str = "",
    model: str = "",
    tokens_used: int = 0,
    latency_ms: float = 0.0,
):
    """
    Trace an LLM API call.
    """
    if not _tracing_enabled or not _tracer:
        return
    
    try:
        with _tracer.start_as_current_span("llm_call") as span:
            span.set_attribute("input.value", prompt[:3000])
            span.set_attribute("output.value", response[:2000])
            span.set_attribute("llm.model_name", model or os.environ.get("MODEL_NAME", ""))
            span.set_attribute("llm.token_count.total", tokens_used)
            span.set_attribute("llm.latency_ms", latency_ms)
            span.set_attribute("openinference.span.kind", "LLM")
            
    except Exception as e:
        logger.warning(f"Tracing error (llm_call): {e}")


def log_feedback_span(
    message_id: str,
    question: str,
    answer: str,
    feedback: str,  # "up" or "down"
):
    """
    Log user feedback as a separate span for Arize tracking.
    This enables feedback analysis in the Arize dashboard.
    
    Args:
        message_id: Unique message identifier
        question: The original user question
        answer: The bot's answer
        feedback: "up" (positive) or "down" (negative)
    """
    if not _tracing_enabled or not _tracer:
        return
    
    try:
        with _tracer.start_as_current_span("user_feedback") as span:
            span.set_attribute("input.value", question)
            span.set_attribute("output.value", answer[:2000] if answer else "")
            span.set_attribute("feedback.type", feedback)
            span.set_attribute("feedback.score", 1 if feedback == "up" else 0)
            span.set_attribute("feedback.message_id", message_id)
            span.set_attribute("openinference.span.kind", "EVALUATOR")
            
            label = "👍 POSITIVE" if feedback == "up" else "👎 NEGATIVE"
            logger.info(f"📊 Traced feedback: {label} for message {message_id}")
            
    except Exception as e:
        logger.warning(f"Tracing error (feedback): {e}")


def get_tracing_status() -> Dict[str, Any]:
    """
    Get current tracing status for health checks.
    """
    return {
        "enabled": _tracing_enabled,
        "project": os.environ.get("ARIZE_PROJECT_NAME", "legislation-rag"),
        "space_id_set": bool(os.environ.get("ARIZE_SPACE_ID")),
        "api_key_set": bool(os.environ.get("ARIZE_API_KEY")),
    }
