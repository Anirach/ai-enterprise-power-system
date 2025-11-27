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
    """
    Process various file types using Docling and extract text content.
    
    Optimized for:
    - Larger chunk sizes to reduce embedding calls
    - Semantic-aware chunking
    - Efficient memory usage
    """
    
    SUPPORTED_EXTENSIONS = {
        ".pdf", ".docx", ".doc", ".pptx", ".ppt", 
        ".xlsx", ".xls", ".html", ".htm",
        ".png", ".jpg", ".jpeg", ".tiff", ".bmp",
        ".txt", ".md", ".csv"
    }
    
    def __init__(
        self,
        chunk_size: int = 8000,  # HUGE chunks = minimum embedding calls = FASTEST
        chunk_overlap: int = 200,  # Small overlap
        min_chunk_size: int = 500  # Filter out small chunks
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        
        # Optimized text splitter with semantic separators
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=[
                "\n\n\n",  # Section breaks
                "\n\n",    # Paragraph breaks
                "\n",      # Line breaks
                ". ",      # Sentences
                "? ",      # Questions
                "! ",      # Exclamations
                "; ",      # Semi-colons
                ", ",      # Clauses
                " ",       # Words
                ""         # Characters
            ]
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
        """
        Process a file and return chunks with metadata.
        
        Optimized for:
        - Efficient chunking with larger chunk sizes
        - Filtering out small/useless chunks
        - Better content extraction
        """
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
        elif ext == ".pdf":
            # Use pdfplumber for PDFs (best Thai support)
            text = await self._extract_pdf_with_pdfplumber(path)
        else:
            # Use Docling for other complex documents (docx, pptx, etc.)
            text = await self._extract_with_docling(path)
        
        # Clean and normalize text
        text = self._clean_text(text) if text else ""
        
        # Split into chunks
        raw_chunks = self.text_splitter.split_text(text) if text else []
        
        # Filter out chunks that are too small or contain only whitespace/special chars
        chunks = [
            chunk.strip() for chunk in raw_chunks 
            if len(chunk.strip()) >= self.min_chunk_size
            and self._is_meaningful_chunk(chunk)
        ]
        
        # Detect language (simple heuristic)
        language = self._detect_language(text[:1000] if text else "")
        
        # Count pages (rough estimate for PDFs)
        page_count = text.count('\f') + 1 if '\f' in text else (len(text) // 3000) + 1
        
        # Build metadata
        base_metadata = {
            "source": str(path),
            "filename": path.name,
            "file_type": ext,
            "file_size": path.stat().st_size,
            "parser": "docling" if ext not in {".txt", ".md", ".csv"} else "native",
            "page_count": page_count,
            "language": language
        }
        if metadata:
            base_metadata.update(metadata)
        
        logger.info(f"Processed {path.name}: {len(chunks)} chunks from {len(text)} chars")
        
        return {
            "filename": path.name,
            "content": text,  # Return full content for storage
            "chunks": chunks,
            "metadata": base_metadata,
            "total_chunks": len(chunks),
            "total_characters": len(text) if text else 0
        }
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        import re
        
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        text = re.sub(r'\t+', ' ', text)
        
        # Remove null bytes and other control characters (except newlines)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        return text.strip()
    
    def _is_meaningful_chunk(self, chunk: str) -> bool:
        """Check if a chunk contains meaningful content"""
        import re
        
        # Remove all whitespace and special characters for counting
        alphanumeric = re.sub(r'[^a-zA-Z0-9\u0E00-\u0E7F]', '', chunk)  # Include Thai chars
        
        # At least 20% of the chunk should be alphanumeric
        if len(chunk) > 0 and len(alphanumeric) / len(chunk) < 0.2:
            return False
        
        # Should have at least some words
        words = chunk.split()
        if len(words) < 3:
            return False
        
        return True
    
    def _detect_language(self, text: str) -> str:
        """Simple language detection"""
        import re
        
        # Check for Thai characters
        thai_chars = len(re.findall(r'[\u0E00-\u0E7F]', text))
        
        # Check for Chinese characters
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        
        # Check for Japanese characters
        japanese_chars = len(re.findall(r'[\u3040-\u309f\u30a0-\u30ff]', text))
        
        # Check for Korean characters
        korean_chars = len(re.findall(r'[\uac00-\ud7af]', text))
        
        total_chars = len(text)
        
        if total_chars == 0:
            return "unknown"
        
        if thai_chars / total_chars > 0.1:
            return "th"
        elif chinese_chars / total_chars > 0.1:
            return "zh"
        elif japanese_chars / total_chars > 0.1:
            return "ja"
        elif korean_chars / total_chars > 0.1:
            return "ko"
        else:
            return "en"
    
    async def _extract_pdf_with_pdfplumber(self, path: Path) -> str:
        """Extract text from PDF using pdfplumber, with OCR fallback for scanned PDFs"""
        text_parts = []
        
        # First try regular text extraction
        try:
            import pdfplumber
            with pdfplumber.open(str(path)) as pdf:
                total_pages = len(pdf.pages)
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if text and text.strip():
                        text_parts.append(text)
                    if (i + 1) % 10 == 0:
                        logger.info(f"Extracted page {i+1}/{total_pages}")
            
            if text_parts:
                result = "\n\n".join(text_parts)
                logger.info(f"✅ pdfplumber extracted {len(result)} chars from {len(text_parts)} pages")
                return result
                
        except ImportError:
            logger.warning("pdfplumber not installed")
        except Exception as e:
            logger.warning(f"pdfplumber failed: {e}")
        
        # If no text extracted, PDF is likely scanned - try OCR
        logger.info("📸 No text found - trying OCR for scanned PDF...")
        return await self._extract_pdf_with_ocr(path)
    
    async def _extract_pdf_with_pypdf(self, path: Path) -> str:
        """Extract text from PDF using pypdf as fallback"""
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            text_parts = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            if text_parts:
                result = "\n\n".join(text_parts)
                logger.info(f"✅ pypdf extracted {len(result)} chars")
                return result
            return ""
        except ImportError:
            logger.error("pypdf not installed!")
            return ""
        except Exception as e:
            logger.error(f"pypdf failed for {path}: {e}")
            return ""
    
    async def _extract_pdf_with_ocr(self, path: Path) -> str:
        """Extract text from scanned PDF using OCR (tesseract)"""
        try:
            import subprocess
            import tempfile
            from PIL import Image
            import pdf2image
            
            logger.info(f"🔍 Starting OCR extraction for {path.name}...")
            
            # Convert PDF to images
            images = pdf2image.convert_from_path(str(path), dpi=200)
            logger.info(f"Converted {len(images)} pages to images")
            
            text_parts = []
            for i, image in enumerate(images):
                # Save image temporarily
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    image.save(tmp.name, 'PNG')
                    
                    # Run tesseract OCR with Thai + English
                    try:
                        result = subprocess.run(
                            ['tesseract', tmp.name, 'stdout', '-l', 'tha+eng'],
                            capture_output=True,
                            text=True,
                            timeout=60
                        )
                        text = result.stdout.strip()
                        if text:
                            text_parts.append(text)
                            if (i + 1) % 5 == 0:
                                logger.info(f"OCR processed page {i+1}/{len(images)}")
                    except subprocess.TimeoutExpired:
                        logger.warning(f"OCR timeout on page {i+1}")
                    finally:
                        os.remove(tmp.name)
            
            if text_parts:
                result = "\n\n".join(text_parts)
                logger.info(f"✅ OCR extracted {len(result)} chars from {len(text_parts)} pages")
                return result
            
            return ""
            
        except ImportError as e:
            logger.error(f"OCR dependencies missing: {e}")
            logger.info("Install with: pip install pdf2image pillow")
            return ""
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return ""
    
    async def _extract_with_docling(self, path: Path) -> str:
        """Extract text using Docling (for non-PDF documents)"""
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
        """Fallback extraction when Docling fails - optimized for Thai/non-English"""
        ext = path.suffix.lower()
        
        try:
            if ext == ".pdf":
                # Try pdfplumber first (best for Thai text)
                try:
                    import pdfplumber
                    text_parts = []
                    with pdfplumber.open(str(path)) as pdf:
                        for page in pdf.pages:
                            text = page.extract_text()
                            if text:
                                text_parts.append(text)
                    if text_parts:
                        result = "\n\n".join(text_parts)
                        logger.info(f"✅ pdfplumber extracted {len(result)} chars")
                        return result
                except ImportError:
                    logger.warning("pdfplumber not installed")
                except Exception as e:
                    logger.warning(f"pdfplumber failed: {e}")
                
                # Try pypdf as second fallback
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(str(path))
                    text_parts = []
                    for page in reader.pages:
                        text = page.extract_text()
                        if text:
                            text_parts.append(text)
                    if text_parts:
                        result = "\n\n".join(text_parts)
                        logger.info(f"✅ pypdf extracted {len(result)} chars")
                        return result
                except ImportError:
                    logger.warning("pypdf not installed")
                except Exception as e:
                    logger.warning(f"pypdf failed: {e}")
                
                # Don't fall through to text extraction for PDFs!
                logger.error(f"All PDF parsers failed for {path}")
                return ""
            
            # Only read as text for actual text files
            if ext in {".txt", ".md", ".csv", ".html", ".htm"}:
                return await self._extract_text_file(path)
            
            return ""
            
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
