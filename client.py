"""
OpenRouter API client setup
"""

from openai import OpenAI
import httpx
from config import OPENROUTER_API_KEY, HTTP_TIMEOUT


def create_openrouter_client():
    """
    Creates and returns an OpenAI-compatible client for OpenRouter.
    
    Returns:
        OpenAI: Configured OpenAI client
    """
    print("🔧 Setting up OpenRouter client...")
    
    # Create httpx client with timeout
    http_client = httpx.Client(
        timeout=HTTP_TIMEOUT,
        follow_redirects=True,
    )
    
    # Create OpenAI-compatible client for OpenRouter
    try:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
            http_client=http_client,
        )
        print("✅ OpenRouter client created successfully!")
        return client
    except Exception as e:
        print(f"❌ Error creating client: {e}")
        raise
