"""
Web Fallback Pipeline v2
Orchestrates the full web-based fallback flow:
  1. Serper search with synonym expansion + dedup + date sorting
  2. Fetch FULL CONTENT from links (not just snippets) via TR proxy
  3. Parse with Azure Document Intelligence (PDF tables/figures + HTML)
  4. Chunk using heading-based semantic splitting
  5. Vectorize and store in MongoDB for future reuse
  6. Generate answer from full web context with obsolescence warnings

v2 improvements:
  A. Full content fetching (never stops at snippet)
  B. PDF table/figure handling via Azure DI
  C. Date/Mülga (obsolescence) sorting + LLM instructions
  D. De-duplication of same-law results
  E. ISG synonym-based query expansion
"""

import os
from typing import Dict, Optional, List


class WebFallbackPipeline:
    """
    End-to-end web fallback v2: Search → Fetch Full → Parse → Chunk → Store → Answer
    """

    def __init__(self, openrouter_client=None):
        """
        Initialize all web pipeline components.
        Components are lazy-loaded — only initialized when first needed.
        """
        self.openrouter_client = openrouter_client
        self._searcher = None
        self._fetcher = None
        self._parser = None
        self._chunker = None
        self._web_store = None
        self.enabled = self._check_requirements()

        if self.enabled:
            print("✅ Web Fallback Pipeline v2 ready (Serper + Azure DI + MongoDB)")
        else:
            print("⚠️  Web Fallback Pipeline disabled (missing env vars)")

    def _check_requirements(self) -> bool:
        """Check if minimum required env vars are set."""
        serper_key = os.getenv("SERPER_API_KEY")
        if not serper_key:
            print("   ⚠️  SERPER_API_KEY not set — web fallback disabled")
            return False
        return True

    # ──────────────────────────────────────────────
    # Lazy component initialization
    # ──────────────────────────────────────────────

    @property
    def searcher(self):
        if self._searcher is None:
            from web_search import SerperWebSearch
            self._searcher = SerperWebSearch()
        return self._searcher

    @property
    def fetcher(self):
        if self._fetcher is None:
            from web_content_fetcher import WebContentFetcher
            self._fetcher = WebContentFetcher()
        return self._fetcher

    @property
    def parser(self):
        if self._parser is None:
            try:
                from azure_doc_parser import AzureDocParser
                self._parser = AzureDocParser()
            except (ValueError, ImportError) as e:
                print(f"   ⚠️  Azure DI not available, using HTML fallback: {e}")
                self._parser = "html_only"
        return self._parser

    @property
    def chunker(self):
        if self._chunker is None:
            from web_doc_chunker import WebDocumentChunker
            self._chunker = WebDocumentChunker()
        return self._chunker

    @property
    def web_store(self):
        if self._web_store is None:
            from web_vector_store import WebVectorStore
            self._web_store = WebVectorStore()
        return self._web_store

    # ──────────────────────────────────────────────
    # Main pipeline (v2)
    # ──────────────────────────────────────────────

    def execute(
        self,
        query: str,
        regulation_hint: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Run the full web fallback pipeline v2.

        Pipeline: Search (with synonyms + dedup + date sort)
                  → Fetch FULL content (not snippets)
                  → Parse with Azure DI (tables/figures)
                  → Chunk → Store → Answer

        Args:
            query: User's original question.
            regulation_hint: Optional regulation name for better Serper results.

        Returns:
            Dict with answer, sources, method info — or None if pipeline fails.
        """
        if not self.enabled:
            return None

        print("\n" + "─" * 70)
        print("🌐 WEB FALLBACK PIPELINE v2")
        print("─" * 70)

        # ── Step 1: Search (E: synonym expansion, D: dedup, C: date sort) ──
        print("\n📌 Step 1: Serper Web Search (v2: synonyms + dedup + date check)...")
        search_results = self.searcher.search_legislation(query, regulation_hint)

        if not search_results:
            print("   ❌ No results from Serper")
            return None

        # ── Step 2-4: Fetch FULL CONTENT + Parse + Chunk ──
        print(f"\n📌 Step 2-4: Fetching FULL content & parsing top {min(3, len(search_results))} results...")
        all_chunks: List[Dict] = []
        web_sources: List[Dict] = []
        obsolete_warnings: List[str] = []

        for result in search_results[:3]:  # Process top 3
            url = result["link"]
            title = result["title"]
            is_obsolete = result.get("is_potentially_obsolete", False)
            obsolete_reason = result.get("obsolescence_reason", "")

            if is_obsolete:
                obsolete_warnings.append(f"{title}: {obsolete_reason}")

            # Check if already in our web store
            try:
                if self.web_store.url_already_stored(url):
                    print(f"   ♻️  Already stored: {url[:60]}...")
                    existing = self.web_store.search(query, k=3)
                    if existing:
                        for doc in existing:
                            all_chunks.append({
                                "content": doc["content"],
                                "metadata": doc["metadata"],
                            })
                        web_sources.append({
                            "title": title,
                            "url": url,
                            "status": "cached",
                            "is_obsolete": is_obsolete,
                        })
                    continue
            except Exception:
                pass

            # ── A: Fetch FULL content (not just snippet) ──
            parsed_text = None
            chunk_type = "plain"

            # Try Azure DI first for best quality (B: PDF table/figure handling)
            if self.parser and self.parser != "html_only":
                parsed_text = self._fetch_and_parse_with_azure_di(url)
                if parsed_text:
                    chunk_type = "markdown"

            # Fallback: regular fetch + simple parse
            if not parsed_text:
                parsed_text = self._fetch_and_parse_fallback(url)
                if parsed_text:
                    chunk_type = "plain"

            if not parsed_text or len(parsed_text.strip()) < 50:
                # Last resort: use snippet (but mark it)
                snippet = result.get("snippet", "")
                if len(snippet) > 30:
                    print(f"   ⚠️  Using snippet only for: {url[:60]}")
                    parsed_text = f"### {title}\n\n{snippet}"
                    chunk_type = "snippet"
                else:
                    print(f"   ⚠️  No content obtained for: {url[:60]}")
                    continue

            # ── Step 3: Chunk ──
            chunks = self.chunker.chunk_document(
                text=parsed_text,
                source_url=url,
                source_title=title,
                content_type=chunk_type,
            )

            if chunks:
                # Add obsolescence flag to chunk metadata
                if is_obsolete:
                    for c in chunks:
                        c["metadata"]["is_potentially_obsolete"] = True
                        c["metadata"]["obsolescence_reason"] = obsolete_reason

                all_chunks.extend(chunks)
                web_sources.append({
                    "title": title,
                    "url": url,
                    "status": "fetched" if chunk_type != "snippet" else "snippet_only",
                    "chunks": len(chunks),
                    "content_type": chunk_type,
                    "is_obsolete": is_obsolete,
                })

                # ── Step 4: Store in MongoDB (if full content, not snippet) ──
                if chunk_type != "snippet":
                    try:
                        stored = self.web_store.store_chunks(chunks)
                        print(f"   ✅ Stored {stored} chunks for future reuse")
                    except Exception as e:
                        print(f"   ⚠️  Storage failed (answer still generated): {e}")

        if not all_chunks:
            print("\n   ❌ No usable content from any web source")
            return None

        # ── Step 5: Generate answer (C: with date/mülga warnings) ──
        print(f"\n📌 Step 5: Generating answer from {len(all_chunks)} web chunks...")
        answer = self._generate_web_answer(query, all_chunks, web_sources, obsolete_warnings)

        if not answer:
            return None

        return {
            "answer": answer,
            "method": "web_fallback",
            "confidence": 0.55,
            "web_sources": web_sources,
            "chunks_used": len(all_chunks),
            "obsolete_warnings": obsolete_warnings,
        }

    # ──────────────────────────────────────────────
    # Content fetching strategies (A: Full content)
    # ──────────────────────────────────────────────

    def _fetch_and_parse_with_azure_di(self, url: str) -> Optional[str]:
        """
        Fetch raw bytes from URL and parse with Azure DI.
        Best for: PDFs with tables/figures, structured HTML.
        """
        try:
            from azure_doc_parser import AzureDocParser

            parser = self.parser
            if not isinstance(parser, AzureDocParser):
                return None

            raw_bytes, content_type = self.fetcher.fetch_raw_bytes(url)
            if not raw_bytes or len(raw_bytes) < 100:
                return None

            if content_type == "pdf":
                return parser.parse_pdf_bytes(raw_bytes)
            else:
                return parser.parse_html_bytes(raw_bytes)

        except Exception as e:
            print(f"   ⚠️  Azure DI fetch+parse failed for {url[:50]}: {e}")
            return None

    def _fetch_and_parse_fallback(self, url: str) -> Optional[str]:
        """
        Fetch HTML and use simple parser. Fallback when Azure DI unavailable.
        """
        try:
            content, content_type = self.fetcher.fetch(url)
            if not content:
                return None

            if content_type == "pdf":
                # Can't parse PDF without Azure DI
                print(f"   ⚠️  PDF requires Azure DI: {url[:50]}")
                return None
            else:
                return self._simple_html_parse(content)

        except Exception as e:
            print(f"   ⚠️  Fallback fetch failed for {url[:50]}: {e}")
            return None

    # ──────────────────────────────────────────────
    # Answer generation (C: with date/mülga warnings)
    # ──────────────────────────────────────────────

    def _generate_web_answer(
        self,
        query: str,
        chunks: List[Dict],
        web_sources: List[Dict],
        obsolete_warnings: List[str],
    ) -> Optional[str]:
        """Generate an answer from web-sourced chunks using LLM.
        Includes instructions about date verification and obsolescence."""
        if not self.openrouter_client:
            print("   ❌ No LLM client available for answer generation")
            return None

        # Build context from chunks
        context_parts = []
        for idx, chunk in enumerate(chunks[:10], 1):  # Max 10 chunks
            title = chunk["metadata"].get("source_title", "Bilinmeyen")
            is_obsolete = chunk["metadata"].get("is_potentially_obsolete", False)
            obsolete_note = " [⚠️ GÜNCELLIK KONTROL EDİLMELİ]" if is_obsolete else ""
            context_parts.append(f"[Kaynak {idx}: {title}{obsolete_note}]\n{chunk['content']}")

        context = "\n\n---\n\n".join(context_parts)

        # Build obsolescence warning for LLM
        obsolete_section = ""
        if obsolete_warnings:
            obsolete_section = "\n\nÖNEMLI - GÜNCELLİK UYARISI:\n"
            for w in obsolete_warnings:
                obsolete_section += f"⚠️ {w}\n"
            obsolete_section += (
                "Bu kaynaklar 2012 öncesi veya mülga olabilir. "
                "Güncelliğini doğrula ve kullanıcıyı bilgilendir.\n"
            )

        prompt = f"""Sen Türk İş Sağlığı ve Güvenliği (İSG) mevzuatı konusunda uzmanlaşmış bir danışmansın.

Aşağıda resmi internet kaynaklarından (Resmi Gazete, Mevzuat Bilgi Sistemi vb.) 
elde edilen güncel mevzuat bilgileri bulunmaktadır.

KURALLAR:
1. Yalnızca verilen kaynaklardaki bilgileri kullan
2. Kaynak referanslarını köşeli parantez içinde yönetmelik/kanun adı olarak yaz
3. Cevabın sonunda "Dosya adı" veya ".pdf" kullanma
4. Spekülatif bilgi verme — sadece kaynaklardaki bilgileri kullan
5. Eğer bilgi çelişiyorsa EN GÜNCEL tarihli kaynağa öncelik ver
6. Kaynakta tablo varsa, tablo bilgilerini doğru aktar
7. "⚠️ GÜNCELLIK KONTROL EDİLMELİ" işaretli kaynakları kullanırken, 
   kullanıcıyı bu bilginin eski olabileceği konusunda uyar
{obsolete_section}

İNTERNET KAYNAKLARI:
━━━━━━━━━━━━━━━━━━━━━━
{context}
━━━━━━━━━━━━━━━━━━━━━━

Kullanıcı Sorusu: {query}

Yanıt:"""

        messages = [
            {
                "role": "system",
                "content": (
                    "Sen İSG mevzuatı danışmanısın. Resmi internet kaynaklarından "
                    "elde edilen güncel bilgilerle cevap veriyorsun. "
                    "Tablo ve şekil bilgilerini doğru aktar. "
                    "Eski/mülga mevzuat konusunda kullanıcıyı uyar. "
                    "Cevabını Türkçe ver."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        try:
            from config import MODEL_NAME, TEMPERATURE, MAX_TOKENS

            response = self.openrouter_client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
            )

            answer_text = response.choices[0].message.content

            # Append web source links
            answer_text += self._format_web_sources(web_sources)

            return answer_text

        except Exception as e:
            print(f"   ❌ LLM answer generation failed: {e}")
            return None

    def _format_web_sources(self, sources: List[Dict]) -> str:
        """Format web sources as clickable links at the end of the answer."""
        if not sources:
            return ""

        section = "\n\n" + "═" * 70 + "\n"
        section += "İNTERNET KAYNAKLARI\n"
        section += "═" * 70 + "\n\n"

        for src in sources:
            title = src.get("title", "Kaynak")
            url = src.get("url", "")
            status = src.get("status", "")
            content_type = src.get("content_type", "")
            is_obsolete = src.get("is_obsolete", False)

            # Clean title
            clean_title = title.replace(" - Mevzuat Bilgi Sistemi", "").strip()

            # Status indicator
            if status == "cached":
                status_mark = "[onbellek]"
            elif status == "snippet_only":
                status_mark = "[yalnizca ozet]"
            elif content_type == "markdown":
                status_mark = "[tam icerik]"
            else:
                status_mark = ""

            obsolete_mark = " [eski olabilir]" if is_obsolete else ""

            section += f"Kaynak: {clean_title} {status_mark}{obsolete_mark}\n{url}\n\n"

        section += "═" * 70 + "\n"
        return section

    def _simple_html_parse(self, html: str) -> str:
        """Minimal HTML to text conversion when Azure DI is not available."""
        import re

        text = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", html)
        text = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", text)
        text = re.sub(r"<br\s*/?>", "\n", text)
        text = re.sub(r"</?p[^>]*>", "\n", text)
        text = re.sub(r"<h[1-6][^>]*>", "\n### ", text)
        text = re.sub(r"</h[1-6]>", "\n", text)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"&nbsp;", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def get_stats(self) -> Dict:
        """Return web pipeline statistics."""
        try:
            store_stats = self.web_store.get_stats()
        except Exception:
            store_stats = {"total_chunks": 0, "unique_urls": 0}

        return {
            "enabled": self.enabled,
            "store": store_stats,
        }
