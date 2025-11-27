"""
AI Power System - Web Crawler
Crawls websites and extracts text content
"""
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional, Set
from urllib.parse import urljoin, urlparse
import logging
import asyncio
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


class WebCrawler:
    """Web crawler for extracting content from websites"""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        max_pages: int = 50,
        timeout: float = 30.0
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_pages = max_pages
        self.timeout = timeout
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
    
    async def crawl_url(
        self,
        url: str,
        follow_links: bool = False,
        max_depth: int = 1
    ) -> Dict[str, Any]:
        """Crawl a URL and extract content"""
        visited: Set[str] = set()
        results: List[Dict[str, Any]] = []
        
        await self._crawl_recursive(
            url=url,
            base_domain=urlparse(url).netloc,
            visited=visited,
            results=results,
            current_depth=0,
            max_depth=max_depth if follow_links else 0
        )
        
        # Combine all text and chunk it
        all_text = "\n\n".join([r["text"] for r in results if r.get("text")])
        chunks = self.text_splitter.split_text(all_text) if all_text else []
        
        return {
            "url": url,
            "pages_crawled": len(results),
            "chunks": chunks,
            "total_chunks": len(chunks),
            "total_characters": len(all_text),
            "pages": [
                {"url": r["url"], "title": r.get("title", "")}
                for r in results
            ]
        }
    
    async def _crawl_recursive(
        self,
        url: str,
        base_domain: str,
        visited: Set[str],
        results: List[Dict[str, Any]],
        current_depth: int,
        max_depth: int
    ):
        """Recursively crawl pages"""
        if url in visited or len(visited) >= self.max_pages:
            return
        
        if current_depth > max_depth:
            return
        
        visited.add(url)
        
        try:
            page_data = await self._fetch_page(url)
            if page_data:
                results.append(page_data)
                
                # Follow links if not at max depth
                if current_depth < max_depth and page_data.get("links"):
                    for link in page_data["links"][:10]:  # Limit links per page
                        if urlparse(link).netloc == base_domain:
                            await self._crawl_recursive(
                                url=link,
                                base_domain=base_domain,
                                visited=visited,
                                results=results,
                                current_depth=current_depth + 1,
                                max_depth=max_depth
                            )
        except Exception as e:
            logger.error(f"Failed to crawl {url}: {e}")
    
    async def _fetch_page(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch and parse a single page"""
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True
            ) as client:
                response = await client.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (compatible; AIPowerBot/1.0)"
                    }
                )
                response.raise_for_status()
                
                content_type = response.headers.get("content-type", "")
                if "text/html" not in content_type:
                    return None
                
                soup = BeautifulSoup(response.text, "lxml")
                
                # Remove unwanted elements
                for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                    tag.decompose()
                
                # Extract title
                title = soup.title.string if soup.title else ""
                
                # Extract main content
                main_content = soup.find("main") or soup.find("article") or soup.find("body")
                text = main_content.get_text(separator="\n", strip=True) if main_content else ""
                
                # Extract links
                links = []
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    full_url = urljoin(url, href)
                    if full_url.startswith("http"):
                        links.append(full_url)
                
                return {
                    "url": url,
                    "title": title,
                    "text": text,
                    "links": list(set(links))
                }
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None
    
    async def crawl_multiple(
        self,
        urls: List[str]
    ) -> List[Dict[str, Any]]:
        """Crawl multiple URLs concurrently"""
        tasks = [self.crawl_url(url, follow_links=False) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return [
            r for r in results
            if isinstance(r, dict) and not isinstance(r, Exception)
        ]


