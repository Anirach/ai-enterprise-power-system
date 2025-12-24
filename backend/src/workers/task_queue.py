"""
AI Power System - Redis Task Queue
Manages document processing tasks with parallel workers
"""
import json
import asyncio
import uuid
from typing import Optional, Dict, Any, Callable
from datetime import datetime
import logging
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class TaskQueue:
    """Redis-based task queue for document processing"""
    
    QUEUE_NAME = "document_processing_queue"
    PROCESSING_SET = "document_processing_active"
    RESULTS_PREFIX = "task_result:"
    
    def __init__(self, redis_url: str = "redis://redis:6379"):
        self.redis_url = redis_url
        self._redis: Optional[aioredis.Redis] = None
    
    async def connect(self):
        """Connect to Redis"""
        if self._redis is None:
            self._redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("✅ Task queue connected to Redis")
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self._redis:
            await self._redis.close()
            self._redis = None
    
    async def enqueue(self, task_data: Dict[str, Any]) -> str:
        """Add a task to the queue"""
        await self.connect()
        
        task_id = str(uuid.uuid4())
        task = {
            "id": task_id,
            "created_at": datetime.utcnow().isoformat(),
            "status": "pending",
            **task_data
        }
        
        await self._redis.rpush(self.QUEUE_NAME, json.dumps(task))
        logger.info(f"Task {task_id} enqueued")
        return task_id
    
    async def dequeue(self, timeout: int = 5) -> Optional[Dict[str, Any]]:
        """Get a task from the queue (blocking)"""
        await self.connect()
        
        result = await self._redis.blpop(self.QUEUE_NAME, timeout=timeout)
        if result:
            _, task_json = result
            task = json.loads(task_json)
            # Mark as processing
            await self._redis.sadd(self.PROCESSING_SET, task["id"])
            return task
        return None
    
    async def complete_task(self, task_id: str, result: Dict[str, Any]):
        """Mark a task as completed"""
        await self.connect()
        await self._redis.srem(self.PROCESSING_SET, task_id)
        await self._redis.setex(
            f"{self.RESULTS_PREFIX}{task_id}",
            3600,  # 1 hour TTL
            json.dumps(result)
        )
    
    async def fail_task(self, task_id: str, error: str):
        """Mark a task as failed"""
        await self.connect()
        await self._redis.srem(self.PROCESSING_SET, task_id)
        await self._redis.setex(
            f"{self.RESULTS_PREFIX}{task_id}",
            3600,
            json.dumps({"status": "failed", "error": error})
        )
    
    async def get_queue_length(self) -> int:
        """Get number of pending tasks"""
        await self.connect()
        return await self._redis.llen(self.QUEUE_NAME)
    
    async def get_processing_count(self) -> int:
        """Get number of tasks being processed"""
        await self.connect()
        return await self._redis.scard(self.PROCESSING_SET)


class DocumentWorker:
    """Worker for processing documents from the queue"""
    
    def __init__(
        self,
        worker_id: int,
        task_queue: TaskQueue,
        process_func: Callable
    ):
        self.worker_id = worker_id
        self.task_queue = task_queue
        self.process_func = process_func
        self._running = False
    
    async def start(self):
        """Start the worker"""
        self._running = True
        logger.info(f"Worker {self.worker_id} started")
        
        while self._running:
            try:
                task = await self.task_queue.dequeue(timeout=2)
                if task:
                    logger.info(f"Worker {self.worker_id} processing task {task['id']}")
                    try:
                        result = await self.process_func(task)
                        await self.task_queue.complete_task(task["id"], result)
                        logger.info(f"Worker {self.worker_id} completed task {task['id']}")
                    except Exception as e:
                        logger.error(f"Worker {self.worker_id} failed task {task['id']}: {e}")
                        await self.task_queue.fail_task(task["id"], str(e))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {self.worker_id} error: {e}")
                await asyncio.sleep(1)
        
        logger.info(f"Worker {self.worker_id} stopped")
    
    def stop(self):
        """Stop the worker"""
        self._running = False


class WorkerPool:
    """Pool of document processing workers"""
    
    def __init__(
        self,
        num_workers: int,
        redis_url: str,
        process_func: Callable
    ):
        self.num_workers = num_workers
        self.task_queue = TaskQueue(redis_url)
        self.process_func = process_func
        self.workers: list[DocumentWorker] = []
        self._tasks: list[asyncio.Task] = []
    
    async def start(self):
        """Start all workers"""
        await self.task_queue.connect()
        
        for i in range(self.num_workers):
            worker = DocumentWorker(i, self.task_queue, self.process_func)
            self.workers.append(worker)
            task = asyncio.create_task(worker.start())
            self._tasks.append(task)
        
        logger.info(f"Started {self.num_workers} document processing workers")
    
    async def stop(self):
        """Stop all workers"""
        for worker in self.workers:
            worker.stop()
        
        for task in self._tasks:
            task.cancel()
        
        await asyncio.gather(*self._tasks, return_exceptions=True)
        await self.task_queue.disconnect()
        
        self.workers.clear()
        self._tasks.clear()
        logger.info("All workers stopped")
    
    async def enqueue_document(self, doc_data: Dict[str, Any]) -> str:
        """Add a document to the processing queue"""
        return await self.task_queue.enqueue(doc_data)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get worker pool statistics"""
        return {
            "num_workers": self.num_workers,
            "queue_length": await self.task_queue.get_queue_length(),
            "processing": await self.task_queue.get_processing_count()
        }



