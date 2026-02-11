"""
Azure Document Intelligence Parser
Parses PDF and HTML documents using Azure DI Layout model.
Returns structured Markdown with tables and section headings.
"""

import os
import re
from typing import Optional, List, Dict


class AzureDocParser:
    """
    Uses Azure Document Intelligence (Layout model) to extract
    structured Markdown content from PDFs and HTML pages.
    """

    def __init__(self):
        self.endpoint = os.getenv("AZURE_DI_ENDPOINT")
        self.key = os.getenv("AZURE_DI_KEY")
        self.model = os.getenv("AZURE_DI_MODEL", "prebuilt-layout")

        if not self.endpoint or not self.key:
            raise ValueError(
                "AZURE_DI_ENDPOINT and AZURE_DI_KEY must be set in environment"
            )

        try:
            from azure.ai.documentintelligence import DocumentIntelligenceClient
            from azure.core.credentials import AzureKeyCredential

            self.client = DocumentIntelligenceClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.key),
            )
            print(f"✅ Azure Document Intelligence initialized (model: {self.model})")
        except ImportError:
            raise ImportError(
                "azure-ai-documentintelligence package required. "
                "Install with: pip install azure-ai-documentintelligence"
            )

    def parse_pdf(self, pdf_path: str) -> Optional[str]:
        """
        Parse a local PDF file with Azure DI Layout model.

        Args:
            pdf_path: Absolute path to the PDF file.

        Returns:
            Markdown-formatted text extracted from the PDF.
        """
        print(f"   📄 Azure DI parsing PDF: {pdf_path}")
        try:
            with open(pdf_path, "rb") as f:
                poller = self.client.begin_analyze_document(
                    model_id=self.model,
                    analyze_request=f,
                    content_type="application/octet-stream",
                    output_content_format="markdown",
                )
            result = poller.result()
            markdown = result.content or ""
            print(f"   ✅ Azure DI extracted {len(markdown):,} chars from PDF")
            return markdown

        except Exception as e:
            print(f"   ❌ Azure DI PDF parsing failed: {e}")
            return None

    def parse_pdf_bytes(self, pdf_bytes: bytes) -> Optional[str]:
        """
        Parse PDF from raw bytes (downloaded via proxy) with Azure DI Layout model.
        Tables, figures, and structured content are extracted as Markdown.

        Args:
            pdf_bytes: Raw PDF file content as bytes.

        Returns:
            Markdown-formatted text with tables preserved.
        """
        print(f"   📄 Azure DI parsing PDF bytes ({len(pdf_bytes):,} bytes)...")
        try:
            poller = self.client.begin_analyze_document(
                model_id=self.model,
                analyze_request=pdf_bytes,
                content_type="application/pdf",
                output_content_format="markdown",
            )
            result = poller.result()
            markdown = result.content or ""

            # Log table/figure extraction stats
            tables_count = len(result.tables) if hasattr(result, 'tables') and result.tables else 0
            figures_count = markdown.count("![") if markdown else 0
            print(f"   ✅ Azure DI: {len(markdown):,} chars, {tables_count} tables, {figures_count} figures")
            return markdown

        except Exception as e:
            print(f"   ❌ Azure DI PDF bytes parsing failed: {e}")
            return None

    def parse_html_bytes(self, html_bytes: bytes) -> Optional[str]:
        """
        Parse HTML content from raw bytes with Azure DI Layout model.
        Useful for structured government pages with tables.

        Args:
            html_bytes: Raw HTML content as bytes.

        Returns:
            Markdown-formatted text with tables preserved.
        """
        print(f"   🌐 Azure DI parsing HTML bytes ({len(html_bytes):,} bytes)...")
        try:
            import base64
            from azure.ai.documentintelligence.models import AnalyzeDocumentRequest

            b64_content = base64.b64encode(html_bytes).decode('utf-8')
            poller = self.client.begin_analyze_document(
                model_id=self.model,
                analyze_request=AnalyzeDocumentRequest(bytes_source=b64_content),
                output_content_format="markdown",
            )
            result = poller.result()
            markdown = result.content or ""
            print(f"   ✅ Azure DI HTML: {len(markdown):,} chars extracted")
            return markdown

        except Exception as e:
            print(f"   ❌ Azure DI HTML bytes parsing failed: {e}")
            return None

    def parse_url(self, url: str) -> Optional[str]:
        """
        Parse a web page URL directly with Azure DI.

        Args:
            url: Public URL of the document.

        Returns:
            Markdown-formatted text.
        """
        print(f"   🌐 Azure DI parsing URL: {url[:80]}...")
        try:
            from azure.ai.documentintelligence.models import AnalyzeDocumentRequest

            poller = self.client.begin_analyze_document(
                model_id=self.model,
                analyze_request=AnalyzeDocumentRequest(url_source=url),
                output_content_format="markdown",
            )
            result = poller.result()
            markdown = result.content or ""
            print(f"   ✅ Azure DI extracted {len(markdown):,} chars from URL")
            return markdown

        except Exception as e:
            print(f"   ❌ Azure DI URL parsing failed: {e}")
            return None

    def parse_html_text(self, html: str) -> str:
        """
        Simple HTML-to-text fallback when Azure DI is not needed
        (e.g. for already-structured mevzuat.gov.tr pages).

        Args:
            html: Raw HTML string.

        Returns:
            Cleaned text with basic structure preserved.
        """
        import re

        # Strip tags but keep structure
        text = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", html)
        text = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", text)
        text = re.sub(r"<br\s*/?>", "\n", text)
        text = re.sub(r"</?p[^>]*>", "\n", text)
        text = re.sub(r"</?div[^>]*>", "\n", text)
        text = re.sub(r"<h[1-6][^>]*>", "\n### ", text)
        text = re.sub(r"</h[1-6]>", "\n", text)
        text = re.sub(r"</?li[^>]*>", "\n• ", text)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"&nbsp;", " ", text)
        text = re.sub(r"&amp;", "&", text)
        text = re.sub(r"&lt;", "<", text)
        text = re.sub(r"&gt;", ">", text)
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()
