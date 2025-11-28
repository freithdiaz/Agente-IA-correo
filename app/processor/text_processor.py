"""
Text Processor Module
Extracts text content from various file formats (DOCX, PDF, TXT)
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class TextProcessor:
    """Handles text extraction from documents"""
    
    def process_file(self, file_path: str) -> str:
        """
        Determines file type and extracts text
        Returns a summary string of the content
        """
        try:
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == '.docx':
                return self._process_docx(file_path)
            elif ext == '.pdf':
                return self._process_pdf(file_path)
            elif ext == '.txt':
                return self._process_txt(file_path)
            else:
                return f"Formato no soportado para extracción de texto: {ext}"
                
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            return f"Error al leer archivo: {str(e)}"

    def _process_docx(self, file_path: str) -> str:
        """Extracts text from DOCX"""
        try:
            import docx
            doc = docx.Document(file_path)
            full_text = []
            for para in doc.paragraphs:
                if para.text.strip():
                    full_text.append(para.text)
            
            content = "\n".join(full_text)
            # Limit content length for AI
            return f"--- CONTENIDO DOCX ({os.path.basename(file_path)}) ---\n{content[:5000]}"
        except Exception as e:
            raise Exception(f"Error reading DOCX: {e}")

    def _process_pdf(self, file_path: str) -> str:
        """Extracts text from PDF"""
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            full_text = []
            
            # Read first 5 pages max to avoid huge payloads
            for i, page in enumerate(reader.pages):
                if i >= 5: break
                text = page.extract_text()
                if text:
                    full_text.append(text)
            
            content = "\n".join(full_text)
            return f"--- CONTENIDO PDF ({os.path.basename(file_path)}) ---\n{content[:5000]}"
        except Exception as e:
            raise Exception(f"Error reading PDF: {e}")

    def _process_txt(self, file_path: str) -> str:
        """Extracts text from TXT"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            return f"--- CONTENIDO TXT ({os.path.basename(file_path)}) ---\n{content[:5000]}"
        except Exception as e:
            raise Exception(f"Error reading TXT: {e}")
