"""
Web Search Module - Serper.dev Integration (v2)
Searches official Turkish legislation sources when internal RAG confidence is low.
Only queries trusted government domains for reliability.

v2 improvements:
  A. Full content fetching (not just snippets)
  B. PDF table/figure handling via Azure DI
  C. Date/Mülga (obsolescence) sorting + flagging
  D. De-duplication of same-law results from different sources
  E. ISG synonym-based query expansion
"""

import os
import re
import httpx
from typing import List, Dict, Optional, Set, Tuple
from urllib.parse import urlparse, parse_qs


class ISGSynonymExpander:
    """
    Expands ISG queries with domain-specific Turkish occupational safety synonyms.
    E.g. "güvenlik başlığı" → also searches "baret", "baş koruyucu donanım"
    """

    # ISG term → list of synonyms/alternatives
    SYNONYM_MAP: Dict[str, List[str]] = {
        # KKD - Kişisel Koruyucu Donanım
        "güvenlik başlığı": ["baret", "baş koruyucu donanım", "koruyucu başlık"],
        "baret": ["güvenlik başlığı", "baş koruyucu donanım", "koruyucu başlık"],
        "baş koruyucu": ["baret", "güvenlik başlığı", "baş koruyucu donanım"],
        "koruyucu gözlük": ["göz koruyucu", "koruyucu gözlük donanımı", "göz ve yüz koruyucu"],
        "kulaklık": ["kulak koruyucu", "kulak tıkacı", "işitme koruyucu"],
        "kulak koruyucu": ["kulaklık", "kulak tıkacı", "işitme koruyucu"],
        "eldiven": ["el koruyucu", "koruyucu eldiven"],
        "güvenlik ayakkabısı": ["koruyucu ayakkabı", "çelik burunlu ayakkabı", "iş ayakkabısı"],
        "iş ayakkabısı": ["güvenlik ayakkabısı", "koruyucu ayakkabı", "çelik burunlu"],
        "emniyet kemeri": ["güvenlik kemeri", "paraşüt tipi emniyet kemeri", "düşme önleme"],
        "güvenlik kemeri": ["emniyet kemeri", "paraşüt tipi kemer", "düşme önleme"],
        "toz maskesi": ["solunum koruyucu", "yarım yüz maskesi", "FFP maskesi"],
        "maske": ["solunum koruyucu", "toz maskesi", "gaz maskesi"],

        # Tehlike sınıfları
        "az tehlikeli": ["düşük tehlike", "tehlike sınıfı I"],
        "tehlikeli": ["orta tehlike", "tehlike sınıfı II"],
        "çok tehlikeli": ["yüksek tehlike", "tehlike sınıfı III"],

        # İSG profesyonelleri
        "isg uzmanı": ["iş güvenliği uzmanı", "A sınıfı uzman", "B sınıfı uzman", "C sınıfı uzman"],
        "iş güvenliği uzmanı": ["isg uzmanı", "iş sağlığı güvenliği uzmanı"],
        "işyeri hekimi": ["iş hekimi", "işyeri sağlık personeli"],

        # İş kazası / meslek hastalığı
        "iş kazası": ["iş kazaları", "işkazası", "iş yerinde kaza"],
        "meslek hastalığı": ["meslek hastalıkları", "mesleki hastalık"],
        "ramak kala": ["ramak kala olay", "ucuz atlatma", "near miss"],

        # Risk değerlendirmesi
        "risk değerlendirmesi": ["risk analizi", "tehlike analizi", "risk değerlendirme"],
        "risk analizi": ["risk değerlendirmesi", "tehlike analizi"],

        # Genel terimler
        "KKD": ["kişisel koruyucu donanım", "koruyucu ekipman"],
        "kişisel koruyucu donanım": ["KKD", "koruyucu ekipman", "koruyucu malzeme"],
        "iş sağlığı": ["işçi sağlığı", "çalışan sağlığı"],
        "iş güvenliği": ["işçi güvenliği", "çalışan güvenliği", "iş emniyeti"],
        "ISG": ["İSG", "iş sağlığı ve güvenliği", "iş sağlığı güvenliği"],
        "İSG": ["ISG", "iş sağlığı ve güvenliği", "iş sağlığı güvenliği"],

        # Yapı/İnşaat
        "iskele": ["yapı iskelesi", "cephe iskelesi", "iç iskele"],
        "yapı iskelesi": ["iskele", "cephe iskelesi"],
        "kazı": ["hafriyat", "kazı çalışması"],
        "yüksekte çalışma": ["yüksekten düşme", "yüksekte iş", "yüksek çalışma"],
        "düşme": ["yüksekten düşme", "düşme tehlikesi", "düşme riski"],

        # Elektrik
        "elektrik çarpması": ["elektrik kazası", "elektrik tehlikesi"],
        "topraklama": ["koruyucu topraklama", "toprak hattı"],

        # Yangın
        "yangın": ["yangın güvenliği", "yangın önleme", "yangın riski"],
        "yangın söndürücü": ["yangın tüpü", "söndürme cihazı"],
        "acil durum": ["acil durum planı", "tahliye", "acil eylem planı"],
    }

    @classmethod
    def expand_query(cls, query: str) -> List[str]:
        """
        Given a query, return additional synonym-expanded queries.
        Returns the original query plus up to 2 synonym variants.
        """
        query_lower = query.lower()
        expanded_terms: Set[str] = set()

        for term, synonyms in cls.SYNONYM_MAP.items():
            if term.lower() in query_lower:
                # Add top 2 synonyms as alternative search terms
                for syn in synonyms[:2]:
                    alt_query = query_lower.replace(term.lower(), syn)
                    expanded_terms.add(alt_query)

        # Return unique alternatives (max 2 extra queries)
        return list(expanded_terms)[:2]


class SearchResultDeduplicator:
    """
    Merges search results pointing to the same legislation/mevzuat.
    E.g. same MevzuatNo=6331 from resmigazete and mevzuat.gov.tr → single entry.
    """

    @staticmethod
    def extract_mevzuat_id(url: str, title: str) -> Optional[str]:
        """Extract a canonical ID from URL/title to identify same legislation."""
        # Pattern 1: mevzuat.gov.tr URLs with MevzuatNo
        parsed = urlparse(url)
        if "mevzuat.gov.tr" in parsed.netloc:
            params = parse_qs(parsed.query)
            mevzuat_no = params.get("MevzuatNo", [None])[0]
            if mevzuat_no:
                return f"mevzuat_{mevzuat_no}"

            # Pattern: /mevzuatmetin/X.X.NNNN.pdf
            path_match = re.search(r"/mevzuatmetin/[\d.]+\.(\d+)\.pdf", parsed.path)
            if path_match:
                return f"mevzuat_{path_match.group(1)}"

        # Pattern 2: resmigazete.gov.tr with kanun/yonetmelik number in title
        kanun_match = re.search(r"(\d{4,5})\s*(?:sayılı|Sayılı)", title)
        if kanun_match:
            return f"sayi_{kanun_match.group(1)}"

        # Pattern 3: Yönetmelik name matching
        yonetmelik_match = re.search(
            r"([\w\s]+(?:Yönetmeliği|Kanunu|Tebliği))", title
        )
        if yonetmelik_match:
            name = yonetmelik_match.group(1).strip().lower()
            # Normalize whitespace
            name = re.sub(r"\s+", " ", name)
            return f"name_{name}"

        return None

    @classmethod
    def deduplicate(cls, results: List[Dict]) -> List[Dict]:
        """
        Merge results that reference the same legislation.
        Keeps the best result (highest position / most info) for each law.
        """
        seen_ids: Dict[str, int] = {}  # mevzuat_id → index in deduped
        deduped: List[Dict] = []

        for result in results:
            mev_id = cls.extract_mevzuat_id(result["link"], result["title"])

            if mev_id and mev_id in seen_ids:
                # Merge: keep existing, add alternative link
                idx = seen_ids[mev_id]
                existing = deduped[idx]
                if "alt_links" not in existing:
                    existing["alt_links"] = []
                existing["alt_links"].append(result["link"])

                # Keep longer snippet
                if len(result.get("snippet", "")) > len(existing.get("snippet", "")):
                    existing["snippet"] = result["snippet"]
                # Keep more recent date
                if result.get("date") and (
                    not existing.get("date") or result["date"] > existing["date"]
                ):
                    existing["date"] = result["date"]
            else:
                # New unique result
                if mev_id:
                    seen_ids[mev_id] = len(deduped)
                deduped.append(result.copy())

        removed = len(results) - len(deduped)
        if removed > 0:
            print(f"   🔄 De-duplication: {len(results)} → {len(deduped)} ({removed} merged)")

        return deduped


class DateMulgaChecker:
    """
    Sorts results by date (newest first) and flags potentially obsolete documents.
    Pre-2012 documents may be mülga (repealed) after 6331 sayılı İSG Kanunu.
    """

    # İSG Kanunu (6331) yürürlük tarihi
    ISG_KANUNU_DATE = "2012-06-30"

    # Keywords indicating a document may be repealed
    MULGA_KEYWORDS = ["mülga", "yürürlükten kaldırıl", "ilga edil"]

    @classmethod
    def sort_and_flag(cls, results: List[Dict]) -> List[Dict]:
        """
        Sort by date (newest first), flag pre-2012 or mülga documents.
        """
        for result in results:
            result["is_potentially_obsolete"] = False
            result["obsolescence_reason"] = ""

            date_str = result.get("date", "")
            snippet = result.get("snippet", "").lower()
            title = result.get("title", "").lower()

            # Check for mülga keywords
            combined_text = f"{snippet} {title}"
            for keyword in cls.MULGA_KEYWORDS:
                if keyword in combined_text:
                    result["is_potentially_obsolete"] = True
                    result["obsolescence_reason"] = f"Mülga ifadesi tespit edildi"
                    break

            # Check date — pre-2012 documents need verification
            if date_str:
                try:
                    # Serper dates can be: "2 days ago", "Jan 15, 2020", etc.
                    year_match = re.search(r"20\d{2}", date_str)
                    if year_match:
                        year = int(year_match.group())
                        if year < 2012:
                            result["is_potentially_obsolete"] = True
                            result["obsolescence_reason"] = (
                                f"Tarih: {year} — 6331 sayılı İSG Kanunu öncesi, "
                                f"güncelliği kontrol edilmeli"
                            )
                except (ValueError, AttributeError):
                    pass

        # Sort: non-obsolete first, then by date (newest first)
        def sort_key(r):
            obsolete_penalty = 1 if r["is_potentially_obsolete"] else 0
            # Try to extract year for sorting
            year = 9999  # Default: treat no-date as "recent"
            date_str = r.get("date", "")
            year_match = re.search(r"20\d{2}", date_str)
            if year_match:
                year = -int(year_match.group())  # Negative for descending
            return (obsolete_penalty, year)

        results.sort(key=sort_key)
        return results


class SerperWebSearch:
    """
    Serper.dev search client focused on official Turkish legislation sources.
    Restricts search to: resmigazete.gov.tr, mevzuat.gov.tr, csgb.gov.tr

    v2: Includes synonym expansion, deduplication, date sorting, mülga flagging.
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
        self.expander = ISGSynonymExpander()
        self.deduplicator = SearchResultDeduplicator()
        self.date_checker = DateMulgaChecker()
        print("✅ Serper Web Search v2 initialized (synonyms + dedup + date check)")

    def _build_site_query(self, query: str) -> str:
        """
        Expand user query to target only trusted official sites.
        """
        site_filter = " OR ".join(f"site:{d}" for d in self.TRUSTED_DOMAINS)
        return f"{query} ({site_filter})"

    def _raw_search(
        self,
        query: str,
        max_results: int = 5,
    ) -> List[Dict]:
        """
        Execute a single Serper search (no expansion/dedup).
        """
        full_query = self._build_site_query(query)

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
            return results

        except httpx.TimeoutException:
            print("   ⚠️  Serper request timed out")
            return []
        except httpx.HTTPStatusError as e:
            print(f"   ⚠️  Serper HTTP error: {e.response.status_code}")
            return []
        except Exception as e:
            print(f"   ⚠️  Serper search failed: {e}")
            return []

    def search(
        self,
        query: str,
        max_results: int = 5,
        expand_synonyms: bool = True,
    ) -> List[Dict]:
        """
        Full search pipeline: expand → search → deduplicate → date-sort.

        Args:
            query: The search query.
            max_results: Maximum results per search.
            expand_synonyms: Whether to add ISG synonym queries.

        Returns:
            Deduplicated, date-sorted list of results with obsolescence flags.
        """
        print(f"   🌐 Serper query: {query[:100]}...")

        # Step 1: Main search
        all_results = self._raw_search(query, max_results)

        # Step 2: Synonym-expanded searches (E: Query Expansion)
        if expand_synonyms:
            alt_queries = self.expander.expand_query(query)
            for alt_q in alt_queries:
                print(f"   🔄 Synonym search: {alt_q[:80]}...")
                alt_results = self._raw_search(alt_q, max_results=3)
                all_results.extend(alt_results)

        if not all_results:
            print("   ❌ No results from Serper")
            return []

        # Step 3: De-duplicate (D: same mevzuat from different sources)
        deduped = self.deduplicator.deduplicate(all_results)

        # Step 4: Date sort + mülga flag (C: Date/Mülga control)
        sorted_results = self.date_checker.sort_and_flag(deduped)

        # Log obsolete warnings
        for r in sorted_results:
            if r.get("is_potentially_obsolete"):
                print(f"   ⚠️  Potentially obsolete: {r['title'][:60]} — {r['obsolescence_reason']}")

        print(f"   ✅ Serper pipeline: {len(all_results)} raw → {len(sorted_results)} final results")
        return sorted_results

    def search_legislation(
        self,
        query: str,
        regulation_hint: Optional[str] = None,
    ) -> List[Dict]:
        """
        High-level search for Turkish legislation with full v2 pipeline.
        """
        expanded = query
        if regulation_hint:
            expanded = f"{regulation_hint} {query} güncel hali"
        else:
            expanded = f"{query} İSG yönetmelik güncel hali"

        return self.search(expanded, max_results=5, expand_synonyms=True)
