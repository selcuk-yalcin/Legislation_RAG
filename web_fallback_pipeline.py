"""
Web Fallback Pipeline
Orchestrates the full web-based fallback flow:
  1. Serper search on official Turkish gov sites
  2. Fetch content via TR IP (HTML or PDF)
  3. Parse with Azure Document Intelligence (PDF) or simple HTML parser
  4. Chunk using heading-based semantic splitting
  5. Vectorize and store in MongoDB for future reuse
  6. Generate answer from web context

This module is called by the HybridRAGOrchestrator when internal RAG
confidence is below threshold.
"""

import os
from typing import Dict, Optional, List


class WebFallbackPipeline:
    """
    End-to-end web fallback: Search → Fetch → Parse → Chunk → Store → Answer
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
            print("✅ Web Fallback Pipeline ready (Serper + Azure DI + MongoDB)")
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
    # Main pipeline
    # ──────────────────────────────────────────────

    def execute(
        self,
        query: str,
        regulation_hint: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Run the full web fallback pipeline.

        Args:
            query: User's original question.
            regulation_hint: Optional regulation name for better Serper results.

        Returns:
            Dict with answer, sources, method info — or None if pipeline fails.
        """
        if not self.enabled:
            return None

        print("\n" + "─" * 70)
        print("🌐 WEB FALLBACK PIPELINE")
        print("─" * 70)

        # ── Step 1: Search ──
        print("\n📌 Step 1: Serper Web Search...")
        search_results = self.searcher.search_legislation(query, regulation_hint)

        if not search_results:
            print("   ❌ No results from Serper")
            return None

        # ── Step 2 & 3: Fetch + Parse top results ──
        print(f"\n📌 Step 2-3: Fetching & parsing top {len(search_results)} results...")
        all_chunks: List[Dict] = []
        web_sources: List[Dict] = []

        for result in search_results[:3]:  # Process top 3 only
            url = result["link"]
            title = result["title"]

            # Check if already in our web store
            try:
                if self.web_store.url_already_stored(url):
                    print(f"   ♻️  Already stored: {url[:60]}...")
                    # Search existing chunks instead
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
                        })
                    continue
            except Exception:
                pass

            # Fetch content
            content, content_type = self.fetcher.fetch(url)
            if not content:
                print(f"   ⚠️  Could not fetch: {url[:60]}")
                continue

            # Parse
            parsed_text = None
            if content_type == "pdf":
                if self.parser and self.parser != "html_only":
                    parsed_text = self.parser.parse_pdf(content)
                    chunk_type = "markdown"
                else:
                    print(f"   ⚠️  Cannot parse PDF without Azure DI: {url[:60]}")
                    continue
            else:
                # HTML
                if self.parser and self.parser != "html_only":
                    parsed_text = self.parser.parse_url(url)
                    chunk_type = "markdown"
                else:
                    parsed_text = self._simple_html_parse(content)
                    chunk_type = "plain"

            if not parsed_text or len(parsed_text.strip()) < 50:
                print(f"   ⚠️  Parsed content too short for: {url[:60]}")
                continue

            # ── Step 4: Chunk ──
            chunks = self.chunker.chunk_document(
                text=parsed_text,
                source_url=url,
                source_title=title,
                content_type=chunk_type,
            )

            if chunks:
                all_chunks.extend(chunks)
                web_sources.append({
                    "title": title,
                    "url": url,
                    "status": "fetched",
                    "chunks": len(chunks),
                })

                # ── Step 5: Store in MongoDB ──
                try:
                    print(f"\n📌 Step 5: Vectorizing & storing {len(chunks)} chunks...")
                    stored = self.web_store.store_chunks(chunks)
                    print(f"   ✅ Stored {stored} chunks for future reuse")
                except Exception as e:
                    print(f"   ⚠️  Storage failed (answer still generated): {e}")

        if not all_chunks:
            print("\n   ❌ No usable content from any web source")
            return None

        # ── Step 6: Generate answer ──
        print(f"\n📌 Step 6: Generating answer from {len(all_chunks)} web chunks...")
        answer = self._generate_web_answer(query, all_chunks, web_sources)

        if not answer:
            return None

        return {
            "answer": answer,
            "method": "web_fallback",
            "confidence": 0.55,
            "web_sources": web_sources,
            "chunks_used": len(all_chunks),
        }

    # ──────────────────────────────────────────────
    # Answer generation
    # ──────────────────────────────────────────────

    def _generate_web_answer(
        self,
        query: str,
        chunks: List[Dict],
        web_sources: List[Dict],
    ) -> Optional[str]:
        """Generate an answer from web-sourced chunks using LLM."""
        if not self.openrouter_client:
            print("   ❌ No LLM client available for answer generation")
            return None

        # Build context from chunks
        context_parts = []
        for idx, chunk in enumerate(chunks[:10], 1):  # Max 10 chunks
            title = chunk["metadata"].get("source_title", "Bilinmeyen")
            context_parts.append(f"[Kaynak: {title}]\n{chunk['content']}")

        context = "\n\n---\n\n".join(context_parts)

        prompt = f"""Sen Türk İş Sağlığı ve Güvenliği (İSG) mevzuatı konusunda uzmanlaşmış bir danışmansın.

Aşağıda resmi internet kaynaklarından (Resmi Gazete, Mevzuat Bilgi Sistemi vb.) 
elde edilen güncel mevzuat bilgileri bulunmaktadır.

KURALLAR:
1. Yalnızca verilen kaynaklardaki bilgileri kullan
2. Kaynak referanslarını köşeli parantez içinde yönetmelik/kanun adı olarak yaz
3. Cevabın sonunda "Dosya adı" veya ".pdf" kullanma
4. Spekülatif bilgi verme — sadece kaynaklardaki bilgileri kullan
5. Eğer bilgi çelişiyorsa en güncel tarihli kaynağa öncelik ver

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
            # Clean title
            clean_title = title.replace(" - Mevzuat Bilgi Sistemi", "").strip()
            section += f"📄 Kaynak: {clean_title}, {url}\n\n"

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
