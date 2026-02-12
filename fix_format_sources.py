#!/usr/bin/env python3
"""Fix rag_pipeline.py _format_sources method"""

# Read file
with open('rag_pipeline.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the method
in_method = False
method_start = -1
method_end = -1
indent_count = 0

for i, line in enumerate(lines):
    if '    def _format_sources(self, documents):' in line:
        method_start = i
        in_method = True
        print(f"Found method start at line {i}")
    elif in_method and line.strip().startswith('def ') and '    def ' in line:
        method_end = i
        print(f"Found method end at line {i}")
        break

if method_start != -1 and method_end != -1:
    # New method implementation
    new_method = '''    def _format_sources(self, documents):
        """Format sources with clear separation between legislation and guides"""
        if not documents:
            return ""
        
        # Kaynak tipine gore ayir
        mevzuat_docs = [d for d in documents if d.metadata.get('collection_type') != 'guide']
        guide_docs = [d for d in documents if d.metadata.get('collection_type') == 'guide']
        
        sources = "\\n\\n" + "═" * 70 + "\\n"
        sources += "📚 CEVABINIZ ICIN KULLANILAN KAYNAKLAR\\n"
        sources += "═" * 70 + "\\n\\n"
        
        # Mevzuat kaynaklari
        if mevzuat_docs:
            sources += "🏛️ **MEVZUAT KAYNAKLARI (Yasal Dayanak)**\\n"
            sources += "─" * 70 + "\\n"
            for idx, doc in enumerate(mevzuat_docs, 1):
                # Basligi temizle
                raw_title = doc.metadata.get('document_title', doc.metadata.get('source_file', 'Bilinmeyen Belge'))
                clean_title = self._clean_title(raw_title)
                
                # Link varsa ekle
                source_url = doc.metadata.get('source_url', '')
                if source_url and source_url.startswith('http'):
                    sources += f"{idx}. {clean_title}\\n"
                    sources += f"   🔗 Link: {source_url}\\n"
                else:
                    sources += f"{idx}. {clean_title}\\n"
                
                # Icerik onizleme
                content_preview = doc.page_content.replace('\\n', ' ').strip()[:250]
                sources += f"   💬 Alinti: \\"{content_preview}...\\"\\n\\n"
        
        # Rehber kaynaklari
        if guide_docs:
            sources += "📚 **REHBER KAYNAKLARI (Uygulama Onerileri)**\\n"
            sources += "─" * 70 + "\\n"
            for idx, doc in enumerate(guide_docs, 1):
                # Basligi temizle
                raw_title = doc.metadata.get('guide_title', doc.metadata.get('source_file', 'Bilinmeyen Rehber'))
                clean_title = self._clean_title(raw_title)
                
                # Link varsa ekle
                source_url = doc.metadata.get('source_url', '')
                if source_url and source_url.startswith('http'):
                    sources += f"{idx}. {clean_title}\\n"
                    sources += f"   🔗 Link: {source_url}\\n"
                else:
                    sources += f"{idx}. {clean_title}\\n"
                
                # Icerik onizleme
                content_preview = doc.page_content.replace('\\n', ' ').strip()[:250]
                sources += f"   💡 Oneri: \\"{content_preview}...\\"\\n\\n"
        
        sources += "═" * 70 + "\\n"
        sources += "💡 Not: Mevzuat kaynaklari yasal hukumler, rehber kaynaklari uygulama onerileridir.\\n"
        return sources
    
'''
    
    # Replace the method
    new_lines = lines[:method_start] + [new_method] + lines[method_end:]
    
    # Write back
    with open('rag_pipeline.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print("✅ Method replaced successfully!")
else:
    print(f"❌ Could not find method boundaries")
    print(f"   Start: {method_start}, End: {method_end}")
