"""
AI Power System - File Processor
Uses Docling (IBM) for advanced document parsing
Supports: PDF, DOCX, PPTX, XLSX, HTML, images, and more
https://github.com/docling-project/docling
"""
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


class FileProcessor:
    """Process various file types using Docling and extract text content"""
    
    SUPPORTED_EXTENSIONS = {
        ".pdf", ".docx", ".doc", ".pptx", ".ppt", 
        ".xlsx", ".xls", ".html", ".htm",
        ".png", ".jpg", ".jpeg", ".tiff", ".bmp",
        ".txt", ".md", ".csv"
    }
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        self._converter = None
    
    def _get_converter(self):
        """Lazy load DocumentConverter to avoid slow startup"""
        if self._converter is None:
            try:
                from docling.document_converter import DocumentConverter
                self._converter = DocumentConverter()
                logger.info("✅ Docling DocumentConverter initialized")
            except ImportError as e:
                logger.error(f"Failed to import Docling: {e}")
                raise
        return self._converter
    
    async def process_file(
        self,
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a file and return chunks with metadata"""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        ext = path.suffix.lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {ext}")
        
        # Extract text based on file type
        if ext in {".txt", ".md", ".csv"}:
            # Plain text files - read directly
            text = await self._extract_text_file(path)
        else:
            # Use Docling for complex documents
            text = await self._extract_with_docling(path)
        
        # Split into chunks
        chunks = self.text_splitter.split_text(text) if text else []
        
        # Build metadata
        base_metadata = {
            "source": str(path),
            "filename": path.name,
            "file_type": ext,
            "file_size": path.stat().st_size,
            "parser": "docling" if ext not in {".txt", ".md", ".csv"} else "native"
        }
        if metadata:
            base_metadata.update(metadata)
        
        return {
            "filename": path.name,
            "chunks": chunks,
            "metadata": base_metadata,
            "total_chunks": len(chunks),
            "total_characters": len(text) if text else 0
        }
    
    async def _extract_with_docling(self, path: Path) -> str:
        """Extract text using Docling"""
        try:
            converter = self._get_converter()
            result = converter.convert(str(path))
            
            # Export to markdown for best text representation
            text = result.document.export_to_markdown()
            
            logger.info(f"✅ Docling processed: {path.name}")
            return text
            
        except Exception as e:
            logger.error(f"Docling extraction failed for {path}: {e}")
            # Fallback to basic text extraction if Docling fails
            return await self._fallback_extract(path)
    
    async def _fallback_extract(self, path: Path) -> str:
        """Fallback extraction when Docling fails"""
        ext = path.suffix.lower()
        
        try:
            if ext == ".pdf":
                # Try pypdf as fallback
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(str(path))
                    text_parts = []
                    for page in reader.pages:
                        text = page.extract_text()
                        if text:
                            text_parts.append(text)
                    return "\n\n".join(text_parts)
                except ImportError:
                    pass
            
            # Try reading as text
            return await self._extract_text_file(path)
            
        except Exception as e:
            logger.error(f"Fallback extraction failed: {e}")
            return ""
    
    async def _extract_text_file(self, path: Path) -> str:
        """Extract text from plain text files"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(path, 'r', encoding='latin-1') as f:
                    return f.read()
            except Exception:
                return ""
    
    def get_supported_extensions(self) -> List[str]:
        """Return list of supported file extensions"""
        return list(self.SUPPORTED_EXTENSIONS)
    
    async def process_image(
        self,
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process an image file with OCR using Docling"""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        ext = path.suffix.lower()
        if ext not in {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}:
            raise ValueError(f"Unsupported image type: {ext}")
        
        # Docling handles OCR automatically for images
        text = await self._extract_with_docling(path)
        
        chunks = self.text_splitter.split_text(text) if text else []
        
        base_metadata = {
            "source": str(path),
            "filename": path.name,
            "file_type": ext,
            "file_size": path.stat().st_size,
            "parser": "docling-ocr"
        }
        if metadata:
            base_metadata.update(metadata)
        
        return {
            "filename": path.name,
            "chunks": chunks,
            "metadata": base_metadata,
            "total_chunks": len(chunks),
            "total_characters": len(text) if text else 0
        }
