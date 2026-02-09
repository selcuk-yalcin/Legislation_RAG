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
        sources_count: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> None:
        """Trace a complete RAG query interaction"""
        if not self.enabled or not self.tracer:
            return
            
        try:
            # Use sources_count if provided, otherwise calculate from sources list
            num_sources = sources_count if sources_count is not None else len(sources)
            
            with self.tracer.start_as_current_span(
                "rag_query",
                attributes={
                    SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.CHAIN.value,
                    SpanAttributes.INPUT_VALUE: question,
                    SpanAttributes.OUTPUT_VALUE: answer,
                    "rag.method": method,
                    "rag.confidence": confidence,
                    "rag.latency_ms": latency * 1000,
                    "rag.num_sources": num_sources,
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
        self,
        query: str,
        method: str,
        num_results: int,
        latency: float,
        results: List[Dict]
    ) -> None:
        """Trace retrieval step (vector search + reranking)"""
        if not self.enabled or not self.tracer:
            return
            
        try:
            with self.tracer.start_as_current_span(
                "retrieval",
                attributes={
                    SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.RETRIEVER.value,
                    SpanAttributes.INPUT_VALUE: query,
                    "retrieval.method": method,
                    "retrieval.num_results": num_results,
                    "retrieval.latency_ms": latency * 1000,
                }
            ) as span:
                # Add top results
                for idx, result in enumerate(results[:3]):
                    span.set_attribute(f"result.{idx}.score", result.get("score", 0.0))
                    span.set_attribute(f"result.{idx}.content_preview", result.get("content", "")[:200])
                    
        except Exception as e:
            print(f"⚠️ Error tracing retrieval: {e}")
    
    def trace_llm_call(
        self,
        prompt: str,
        response: str,
        model: str,
        latency: float,
        tokens_used: Optional[int] = None
    ) -> None:
        """Trace LLM generation step"""
        if not self.enabled or not self.tracer:
            return
            
        try:
            with self.tracer.start_as_current_span(
                "llm_generation",
                attributes={
                    SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.LLM.value,
                    SpanAttributes.INPUT_VALUE: prompt[:1000],  # Limit prompt length
                    SpanAttributes.OUTPUT_VALUE: response[:1000],
                    SpanAttributes.LLM_MODEL_NAME: model,
                    "llm.latency_ms": latency * 1000,
                }
            ) as span:
                if tokens_used:
                    span.set_attribute(SpanAttributes.LLM_TOKEN_COUNT_TOTAL, tokens_used)
                    
        except Exception as e:
            print(f"⚠️ Error tracing LLM call: {e}")
    
    def log_feedback(
        self,
        query_id: str,
        feedback_type: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> None:
        """Log user feedback (thumbs up/down)"""
        if not self.enabled or not self.tracer:
            return
            
        try:
            with self.tracer.start_as_current_span(
                "user_feedback",
                attributes={
                    SpanAttributes.OPENINFERENCE_SPAN_KIND: "FEEDBACK",
                    "feedback.query_id": query_id,
                    "feedback.type": feedback_type,
                    "feedback.timestamp": datetime.utcnow().isoformat(),
                }
            ) as span:
                if user_id:
                    span.set_attribute("feedback.user_id", user_id)
                if metadata:
                    for key, value in metadata.items():
                        span.set_attribute(f"feedback.{key}", str(value))
                        
        except Exception as e:
            print(f"⚠️ Error logging feedback: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get tracing status for health check"""
        return {
            "enabled": self.enabled,
            "provider": "arize_phoenix" if self.enabled else None,
            "project": ARIZE_PROJECT_NAME if self.enabled else None,
            "sdk_available": PHOENIX_AVAILABLE
        }


# Global tracer instance
_tracer = ArizeLegislationTracer()


def initialize_tracing() -> bool:
    """Initialize Phoenix tracing - call at startup"""
    return _tracer.initialize()


def trace_rag_query(*args, **kwargs):
    """Trace a RAG query"""
    _tracer.trace_rag_query(*args, **kwargs)


def trace_retrieval(*args, **kwargs):
    """Trace retrieval step"""
    _tracer.trace_retrieval(*args, **kwargs)


def trace_llm_call(*args, **kwargs):
    """Trace LLM call"""
    _tracer.trace_llm_call(*args, **kwargs)


def log_feedback_span(*args, **kwargs):
    """Log user feedback"""
    _tracer.log_feedback(*args, **kwargs)


def get_tracing_status() -> Dict[str, Any]:
    """Get tracing status"""
    return _tracer.get_status()
