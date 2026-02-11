"""
Web Content Fetcher - Downloads pages via Turkey-based IP
Bypasses geo-blocking by routing requests through a local Turkish server.
Supports both HTML and PDF content retrieval.
"""

import os
import httpx
import tempfile
from typing import Optional, Tuple


class WebContentFetcher:
    """
    Fetches web content (HTML / PDF) through a Turkey-located proxy server
    to bypass geo-restrictions on official Turkish government sites.
    """

    # Default proxy — Turkey IP server (can be overridden via env)
    DEFAULT_PROXY = os.getenv("TR_PROXY_URL", "")  # e.g. socks5://185.169.64.46:1080

    # Direct fetch user-agent (pretend to be a normal browser)
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    # Max download size: 50 MB
    MAX_SIZE = 50 * 1024 * 1024

    def __init__(self):
        self.timeout = float(os.getenv("FETCH_TIMEOUT", "30"))
        self.proxy = self.DEFAULT_PROXY or None
        mode = "via TR proxy" if self.proxy else "direct (no proxy configured)"
        print(f"✅ Web Content Fetcher initialized ({mode})")

    def _get_client_kwargs(self) -> dict:
        """Build httpx client kwargs, optionally with proxy."""
        kwargs = {
            "timeout": self.timeout,
            "follow_redirects": True,
            "headers": {"User-Agent": self.USER_AGENT},
        }
        if self.proxy:
            kwargs["proxy"] = self.proxy
        return kwargs

    def fetch_html(self, url: str) -> Optional[str]:
        """
        Download an HTML page and return its text content.

        Args:
            url: Full URL to fetch.

        Returns:
            Raw HTML string or None on failure.
        """
        print(f"   📥 Fetching HTML: {url[:80]}...")
        try:
            with httpx.Client(**self._get_client_kwargs()) as client:
                resp = client.get(url)
                resp.raise_for_status()

                content_type = resp.headers.get("content-type", "")
                if "text/html" not in content_type and "text/plain" not in content_type:
                    print(f"   ⚠️  Unexpected content-type: {content_type}")

                text = resp.text
                if len(text) > self.MAX_SIZE:
                    print(f"   ⚠️  Content truncated to {self.MAX_SIZE} bytes")
                    text = text[: self.MAX_SIZE]

                print(f"   ✅ HTML fetched ({len(text):,} chars)")
                return text

        except httpx.TimeoutException:
            print(f"   ❌ Timeout fetching {url}")
            return None
        except httpx.HTTPStatusError as e:
            print(f"   ❌ HTTP {e.response.status_code} for {url}")
            return None
        except Exception as e:
            print(f"   ❌ Fetch failed: {e}")
            return None

    def fetch_pdf(self, url: str) -> Optional[str]:
        """
        Download a PDF file and save to a temporary path.

        Args:
            url: Full URL to the PDF.

        Returns:
            Path to the downloaded temporary file, or None on failure.
        """
        print(f"   📥 Fetching PDF: {url[:80]}...")
        try:
            with httpx.Client(**self._get_client_kwargs()) as client:
                resp = client.get(url)
                resp.raise_for_status()

                content = resp.content
                if len(content) > self.MAX_SIZE:
                    print(f"   ❌ PDF too large ({len(content):,} bytes)")
                    return None

                # Write to temp file
                tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
                tmp.write(content)
                tmp.close()

                print(f"   ✅ PDF downloaded ({len(content):,} bytes) → {tmp.name}")
                return tmp.name

        except httpx.TimeoutException:
            print(f"   ❌ Timeout downloading PDF {url}")
            return None
        except httpx.HTTPStatusError as e:
            print(f"   ❌ HTTP {e.response.status_code} for {url}")
            return None
        except Exception as e:
            print(f"   ❌ PDF download failed: {e}")
            return None

    def fetch(self, url: str) -> Tuple[Optional[str], str]:
        """
        Smart fetch: detects content type and returns (content, type).

        Args:
            url: URL to fetch.

        Returns:
            Tuple of (content_string_or_path, content_type).
            content_type is 'html' or 'pdf'.
        """
        url_lower = url.lower()
        if url_lower.endswith(".pdf") or "/pdf/" in url_lower:
            path = self.fetch_pdf(url)
            return (path, "pdf") if path else (None, "pdf")
        else:
            html = self.fetch_html(url)
            return (html, "html") if html else (None, "html")
