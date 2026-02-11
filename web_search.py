"""
Web Search Module - Serper.dev Integration
Searches official Turkish legislation sources when internal RAG confidence is low.
Only queries trusted government domains for reliability.
"""

import os
import httpx
from typing import List, Dict, Optional


class SerperWebSearch:
    """
    Serper.dev search client focused on official Turkish legislation sources.
    Restricts search to: resmigazete.gov.tr, mevzuat.gov.tr, csgb.gov.tr
    """

    TRUSTED_DOMAINS = [
        "resmigazete.gov.tr",
        "mevzuat.gov.tr",
        "csgb.gov.tr",
        "mevzuat.gov.tr/mevzuatmetin",
    ]

    SERPER_API_URL = "https://google.serper.dev/search"

    def __init__(self):
        self.api_key = os.getenv("SERPER_API_KEY")
        if not self.api_key:
            raise ValueError("SERPER_API_KEY not found in environment variables")
        self.timeout = float(os.getenv("SERPER_TIMEOUT", "15"))
        print("✅ Serper Web Search initialized (trusted Turkish gov domains only)")

    def _build_site_query(self, query: str) -> str:
        """
        Expand user query to target only trusted official sites.
        Example: 'Madde 5' -> 'Yapı İşlerinde İSG Yönetmeliği Madde 5 güncel hali
                  site:resmigazete.gov.tr OR site:mevzuat.gov.tr OR site:csgb.gov.tr'
        """
        site_filter = " OR ".join(f"site:{d}" for d in self.TRUSTED_DOMAINS)
        return f"{query} ({site_filter})"

    def search(
        self,
        query: str,
        max_results: int = 5,
    ) -> List[Dict]:
        """
        Execute a web search via Serper.dev restricted to official sources.

        Args:
            query: The search query (will be expanded with site filters).
            max_results: Maximum number of results to return (default 5).

        Returns:
            List of dicts with keys: title, link, snippet, date (if available).
        """
        full_query = self._build_site_query(query)
        print(f"   🌐 Serper query: {full_query[:120]}...")

        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "q": full_query,
            "gl": "tr",
            "hl": "tr",
            "num": max_results,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(self.SERPER_API_URL, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            organic = data.get("organic", [])
            results = []
            for item in organic[:max_results]:
                results.append({
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "date": item.get("date", ""),
                    "position": item.get("position", 0),
                })

            print(f"   ✅ Serper returned {len(results)} results from official sources")
            return results

        except httpx.TimeoutException:
            print("   ❌ Serper request timed out")
            return []
        except httpx.HTTPStatusError as e:
            print(f"   ❌ Serper HTTP error: {e.response.status_code}")
            return []
        except Exception as e:
            print(f"   ❌ Serper search failed: {e}")
            return []

    def search_legislation(
        self,
        query: str,
        regulation_hint: Optional[str] = None,
    ) -> List[Dict]:
        """
        High-level search specifically for Turkish legislation updates.
        Expands query with regulation context before searching.

        Args:
            query: User's original question.
            regulation_hint: Optional regulation name for better results.

        Returns:
            List of search result dicts.
        """
        expanded = query
        if regulation_hint:
            expanded = f"{regulation_hint} {query} güncel hali"
        else:
            expanded = f"{query} İSG yönetmelik güncel hali"

        return self.search(expanded, max_results=5)
