"""
AI Power System - High-Performance Embedding Service
Optimized for fast embedding generation using:
- LOCAL sentence-transformers (FASTEST - batch processing)
- Fallback to Ollama API
- Caching for duplicate texts
"""
import httpx
import asyncio
import hashlib
from typing import List, Dict, Optional
import logging
import os

logger = logging.getLogger(__name__)

# ============================================================
# FAST LOCAL EMBEDDING SERVICE (sentence-transformers)
# ============================================================

class LocalEmbeddingService:
    """
    Ultra-fast embedding service using sentence-transformers.
    Can process 1000+ embeddings in seconds using batch processing.
    """
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",  # Fast and good quality
        device: str = "cpu",  # or "cuda" if GPU available
        cache_size: int = 5000
    ):
        self.model_name = model_name
        self.device = device
        self._model = None
        self._cache: Dict[str, List[float]] = {}
        self._cache_size = cache_size
        self.dimension = 384  # MiniLM dimension (or 768 for larger models)
        
    def _load_model(self):
        """Lazy load the model"""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading embedding model: {self.model_name}")
                self._model = SentenceTransformer(self.model_name, device=self.device)
                self.dimension = self._model.get_sentence_embedding_dimension()
                logger.info(f"✅ Model loaded: {self.model_name} (dim={self.dimension})")
            except ImportError:
                logger.error("sentence-transformers not installed!")
                raise
        return self._model
    
    def _get_cache_key(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()
    
    def _get_cached(self, text: str) -> Optional[List[float]]:
        return self._cache.get(self._get_cache_key(text))
    
    def _set_cache(self, text: str, embedding: List[float]):
        if len(self._cache) >= self._cache_size:
            keys_to_remove = list(self._cache.keys())[:500]
            for key in keys_to_remove:
                self._cache.pop(key, None)
        self._cache[self._get_cache_key(text)] = embedding
    
    async def embed_text(self, text: str) -> List[float]:
        """Embed single text"""
        cached = self._get_cached(text)
        if cached:
            return cached
        
        model = self._load_model()
        # Run in thread pool to not block async
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None, 
            lambda: model.encode(text, convert_to_numpy=True).tolist()
        )
        self._set_cache(text, embedding)
        return embedding
    
    async def embed_texts(
        self,
        texts: List[str],
        batch_size: int = 128,  # Process 128 at once!
        progress_callback=None,
        show_progress: bool = True
    ) -> List[List[float]]:
        """
        BATCH embed all texts at once - EXTREMELY FAST!
        Can process 1000+ texts in <10 seconds.
        """
        if not texts:
            return []
        
        total = len(texts)
        logger.info(f"🚀 Fast batch embedding: {total} texts")
        
        # Check cache first
        results = [None] * total
        uncached_indices = []
        uncached_texts = []
        
        for i, text in enumerate(texts):
            cached = self._get_cached(text)
            if cached:
                results[i] = cached
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)
        
        cache_hits = total - len(uncached_texts)
        if cache_hits > 0:
            logger.info(f"Cache hits: {cache_hits}/{total}")
        
        if uncached_texts:
            model = self._load_model()
            
            # Process in batches
            for batch_start in range(0, len(uncached_texts), batch_size):
                batch_end = min(batch_start + batch_size, len(uncached_texts))
                batch = uncached_texts[batch_start:batch_end]
                
                # Run embedding in thread pool
                loop = asyncio.get_event_loop()
                batch_embeddings = await loop.run_in_executor(
                    None,
                    lambda b=batch: model.encode(b, convert_to_numpy=True, show_progress_bar=show_progress).tolist()
                )
                
                # Store results
                for i, embedding in enumerate(batch_embeddings):
                    idx = uncached_indices[batch_start + i]
                    results[idx] = embedding
                    self._set_cache(uncached_texts[batch_start + i], embedding)
                
                if progress_callback:
                    processed = min(batch_end + cache_hits, total)
                    try:
                        await progress_callback(processed, total)
                    except:
                        pass
        
        logger.info(f"✅ Embedded {total} texts successfully")
        return results
    
    async def is_available(self) -> bool:
        """Check if model can be loaded"""
        try:
            self._load_model()
            return True
        except:
            return False
    
    async def close(self):
        """Cleanup"""
        self._model = None
        self._cache.clear()
    
    def clear_cache(self):
        self._cache.clear()
    
    def get_cache_stats(self) -> Dict:
        return {"size": len(self._cache), "max_size": self._cache_size}


class EmbeddingService:
    """High-performance service for generating text embeddings via Ollama"""
    
    def __init__(
        self, 
        base_url: str, 
        model: str = "nomic-embed-text",
        max_concurrent: int = 10,  # Max parallel requests
        timeout: float = 120.0,
        cache_size: int = 1000  # Cache size for embeddings
    ):
        self.base_url = base_url
        self.model = model
        self.dimension = 768  # nomic-embed-text dimension
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        
        # Semaphore for controlling concurrent requests
        self._semaphore = asyncio.Semaphore(max_concurrent)
        
        # Shared HTTP client with connection pooling
        self._client: Optional[httpx.AsyncClient] = None
        
        # Simple in-memory cache for embeddings
        self._cache: Dict[str, List[float]] = {}
        self._cache_size = cache_size
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the shared HTTP client with connection pooling"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                limits=httpx.Limits(
                    max_connections=self.max_concurrent + 5,
                    max_keepalive_connections=self.max_concurrent
                )
            )
        return self._client
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        return hashlib.md5(text.encode()).hexdigest()
    
    def _get_cached(self, text: str) -> Optional[List[float]]:
        """Get cached embedding if exists"""
        key = self._get_cache_key(text)
        return self._cache.get(key)
    
    def _set_cache(self, text: str, embedding: List[float]):
        """Cache an embedding"""
        if len(self._cache) >= self._cache_size:
            # Remove oldest entries (simple FIFO eviction)
            keys_to_remove = list(self._cache.keys())[:100]
            for key in keys_to_remove:
                self._cache.pop(key, None)
        
        key = self._get_cache_key(text)
        self._cache[key] = embedding
    
    async def embed_text(self, text: str, use_cache: bool = True) -> List[float]:
        """Generate embedding for a single text with caching"""
        # Check cache first
        if use_cache:
            cached = self._get_cached(text)
            if cached is not None:
                return cached
        
        async with self._semaphore:
            try:
                client = await self._get_client()
                response = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={
                        "model": self.model,
                        "prompt": text
                    }
                )
                response.raise_for_status()
                data = response.json()
                embedding = data.get("embedding", [])
                
                # Cache the result
                if use_cache and embedding:
                    self._set_cache(text, embedding)
                
                return embedding
                
            except Exception as e:
                logger.error(f"Failed to generate embedding: {e}")
                raise
    
    async def embed_texts(
        self, 
        texts: List[str],
        batch_size: int = 20,
        progress_callback=None
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts using parallel processing.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process in each parallel batch
            progress_callback: Optional async callback for progress updates
            
        Returns:
            List of embeddings in the same order as input texts
        """
        if not texts:
            return []
        
        total = len(texts)
        embeddings = [None] * total
        processed = 0
        
        # Process in batches for better memory management
        for batch_start in range(0, total, batch_size):
            batch_end = min(batch_start + batch_size, total)
            batch_texts = texts[batch_start:batch_end]
            batch_indices = list(range(batch_start, batch_end))
            
            # Create tasks for parallel processing
            tasks = []
            for i, text in zip(batch_indices, batch_texts):
                # Check cache first to avoid unnecessary API calls
                cached = self._get_cached(text)
                if cached is not None:
                    embeddings[i] = cached
                else:
                    tasks.append((i, text))
            
            # Process uncached texts in parallel
            if tasks:
                async def embed_with_index(idx: int, txt: str):
                    embedding = await self.embed_text(txt, use_cache=True)
                    return idx, embedding
                
                # Execute all embedding requests in parallel
                results = await asyncio.gather(
                    *[embed_with_index(idx, txt) for idx, txt in tasks],
                    return_exceptions=True
                )
                
                # Process results
                for result in results:
                    if isinstance(result, Exception):
                        logger.error(f"Embedding failed: {result}")
                        # Use zero vector as fallback
                        continue
                    idx, embedding = result
                    embeddings[idx] = embedding
            
            processed = batch_end
            
            # Report progress
            if progress_callback:
                try:
                    await progress_callback(processed, total)
                except Exception as e:
                    logger.debug(f"Progress callback failed: {e}")
        
        # Fill any missing embeddings with zero vectors
        for i, emb in enumerate(embeddings):
            if emb is None:
                embeddings[i] = [0.0] * self.dimension
        
        logger.info(f"Generated {total} embeddings (cache hits: {total - len(tasks) if 'tasks' in dir() else 0})")
        return embeddings
    
    async def embed_texts_streaming(
        self,
        texts: List[str],
        chunk_callback=None
    ):
        """
        Generate embeddings with streaming progress updates.
        Yields (index, embedding) tuples as they complete.
        """
        total = len(texts)
        
        async def process_one(idx: int, text: str):
            embedding = await self.embed_text(text)
            if chunk_callback:
                await chunk_callback(idx, total)
            return idx, embedding
        
        # Process all in parallel with semaphore limiting
        tasks = [process_one(i, text) for i, text in enumerate(texts)]
        
        for coro in asyncio.as_completed(tasks):
            result = await coro
            yield result
    
    async def is_available(self) -> bool:
        """Check if the embedding model is available"""
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                return any(m.get("name", "").startswith(self.model.split(":")[0]) for m in models)
            return False
        except Exception:
            return False
    
    async def close(self):
        """Close the HTTP client"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    def clear_cache(self):
        """Clear the embedding cache"""
        self._cache.clear()
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        return {
            "size": len(self._cache),
            "max_size": self._cache_size
        }


class FastEmbeddingService(EmbeddingService):
    """
    Extended embedding service with additional optimizations:
    - Pre-warming model
    - Adaptive batch sizing
    - Request queuing
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._model_warmed = False
    
    async def warm_up(self):
        """Pre-warm the embedding model to reduce first-request latency"""
        if not self._model_warmed:
            try:
                # Send a dummy request to load the model into memory
                await self.embed_text("warmup", use_cache=False)
                self._model_warmed = True
                logger.info("✅ Embedding model warmed up")
            except Exception as e:
                logger.warning(f"Failed to warm up model: {e}")
    
    async def embed_texts_adaptive(
        self,
        texts: List[str],
        min_batch_size: int = 5,
        max_batch_size: int = 50,
        target_latency: float = 2.0
    ) -> List[List[float]]:
        """
        Embed texts with adaptive batch sizing based on measured latency.
        Automatically adjusts batch size to optimize throughput.
        """
        import time
        
        total = len(texts)
        embeddings = [None] * total
        current_batch_size = min_batch_size
        idx = 0
        
        while idx < total:
            batch_end = min(idx + current_batch_size, total)
            batch_texts = texts[idx:batch_end]
            
            start_time = time.time()
            
            # Process batch
            batch_embeddings = await self.embed_texts(batch_texts, batch_size=len(batch_texts))
            
            elapsed = time.time() - start_time
            
            # Store results
            for i, emb in enumerate(batch_embeddings):
                embeddings[idx + i] = emb
            
            # Adjust batch size based on latency
            if elapsed < target_latency * 0.8 and current_batch_size < max_batch_size:
                current_batch_size = min(current_batch_size + 5, max_batch_size)
            elif elapsed > target_latency * 1.2 and current_batch_size > min_batch_size:
                current_batch_size = max(current_batch_size - 5, min_batch_size)
            
            idx = batch_end
            
            logger.debug(f"Batch of {len(batch_texts)} took {elapsed:.2f}s, next batch size: {current_batch_size}")
        
        return embeddings
