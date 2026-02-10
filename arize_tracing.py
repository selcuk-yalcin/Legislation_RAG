"""
Arize Tracing for Legislation RAG
Uses OpenAI auto-instrumentation (works with OpenRouter)
Docs: https://arize.com/docs/ax/integrations/llm-providers/openrouter/openrouter-tracing
"""

import os
from typing import Dict, Any, Optional
from datetime import datetime

# Set OTEL env vars BEFORE any imports to prevent gRPC/mutex issues
os.environ.setdefault("OTEL_EXPORTER_OTLP_TIMEOUT", "30000")
os.environ.setdefault("OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf")
os.environ.setdefault("OTEL_BSP_SCHEDULE_DELAY", "5000")
os.environ.setdefault("OTEL_BSP_MAX_EXPORT_BATCH_SIZE", "32")

# Arize + OpenAI auto-instrumentation
try:
    from arize.otel import register
    from openinference.instrumentation.openai import OpenAIInstrumentor
    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode
    ARIZE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Arize SDK not available: {e}")
    ARIZE_AVAILABLE = False

from config import ARIZE_SPACE_ID, ARIZE_API_KEY, ARIZE_PROJECT_NAME


class ArizeTracer:
    """Arize tracing with OpenAI auto-instrumentation for OpenRouter"""
    
    def __init__(self):
        self.tracer = None
        self.tracer_provider = None
        self.enabled = False
        
    def initialize(self) -> bool:
        """Initialize Arize tracing with OpenAI auto-instrumentation"""
        if not ARIZE_AVAILABLE:
            print("❌ arize-otel or openinference-instrumentation-openai not installed")
            return False
            
        if not ARIZE_API_KEY or not ARIZE_SPACE_ID:
            print("⚠️ ARIZE_API_KEY or ARIZE_SPACE_ID not set. Tracing disabled.")
            return False
            
        try:
            print("🔭 Initializing Arize tracing (OpenRouter auto-instrumentation)...")
            
            # Step 1: Register with Arize using HTTP/protobuf (avoids gRPC mutex issues)
            self.tracer_provider = register(
                space_id=ARIZE_SPACE_ID,
                api_key=ARIZE_API_KEY,
                project_name=ARIZE_PROJECT_NAME,
            )
            
            # Step 2: Auto-instrument OpenAI SDK (catches all OpenRouter calls)
            OpenAIInstrumentor().instrument(tracer_provider=self.tracer_provider)
            
            # Step 3: Get tracer for manual spans (feedback, etc.)
            self.tracer = trace.get_tracer(__name__)
            self.enabled = True
            
            print("✅ Arize tracing initialized!")
            print(f"   📊 Project: {ARIZE_PROJECT_NAME}")
            print(f"   🔗 Dashboard: https://app.arize.com")
            print(f"   🤖 OpenRouter calls will be auto-traced")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize Arize tracing: {e}")
            import traceback
            traceback.print_exc()
            self.enabled = False
            return False
    
    def log_feedback(
        self,
        query_id: str,
        feedback_type: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> None:
        """Log user feedback (like/unlike) as a span"""
        if not self.enabled or not self.tracer:
            return
            
        try:
            # Use descriptive span name based on feedback type and comment presence
            has_comment = metadata and metadata.get("comment")
            span_name = f"user_feedback_{feedback_type}" + ("_with_comment" if has_comment else "")
            
            with self.tracer.start_as_current_span(span_name) as span:
                # Build detailed input/output for better visibility in Arize UI
                question = metadata.get("question", "") if metadata else ""
                answer = metadata.get("answer", "") if metadata else ""
                comment = metadata.get("comment", "") if metadata else ""
                
                # Input: Show question + comment (if exists)
                input_text = question
                if comment:
                    input_text += f"\n\n💬 User Comment:\n{comment}"
                span.set_attribute("input.value", input_text)
                
                # Output: Show answer
                span.set_attribute("output.value", answer)
                
                # Feedback attributes
                span.set_attribute("feedback.query_id", query_id)
                span.set_attribute("feedback.type", feedback_type)
                span.set_attribute("feedback.score", 1.0 if feedback_type == "up" else 0.0)
                span.set_attribute("feedback.label", "positive" if feedback_type == "up" else "negative")
                span.set_attribute("feedback.timestamp", datetime.utcnow().isoformat())
                
                # Add user comment as separate attribute (for filtering/search)
                if comment:
                    span.set_attribute("feedback.user_comment", str(comment))
                    span.set_attribute("feedback.comment_length", len(str(comment)))
                
                if user_id:
                    span.set_attribute("feedback.user_id", user_id)
                
                # Don't add metadata items again (already in input/output)
                # This prevents duplication
                
                span.set_status(Status(StatusCode.OK))
                        
        except Exception as e:
            print(f"⚠️ Feedback tracing error: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get tracing status"""
        return {
            "enabled": self.enabled,
            "provider": "arize",
            "project": ARIZE_PROJECT_NAME if self.enabled else None,
            "auto_instrumentation": "openai (openrouter)" if self.enabled else None,
            "sdk_available": ARIZE_AVAILABLE
        }


# ===== Global instance =====
_tracer = ArizeTracer()


def initialize_tracing() -> bool:
    """Initialize Arize tracing - call at startup"""
    return _tracer.initialize()


def log_feedback_span(*args, **kwargs):
    """Log user feedback"""
    _tracer.log_feedback(*args, **kwargs)


def get_tracing_status() -> Dict[str, Any]:
    """Get tracing status"""
    return _tracer.get_status()
