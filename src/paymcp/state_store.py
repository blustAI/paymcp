"""
StateStoreProvider for PayMCP - ENG-114 Timeout Fix
Simple state storage with only 3 methods (put, get, delete)
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import json
import time
import logging

try:
    import redis
except ImportError:
    redis = None

logger = logging.getLogger(__name__)


class StateStoreProvider(ABC):
    """Abstract base class for state storage providers"""
    
    @abstractmethod
    def put(self, key: str, value: Dict[Any, Any]) -> None:
        """Store a value with a key"""
        pass
    
    @abstractmethod
    def get(self, key: str) -> Optional[Dict[Any, Any]]:
        """Retrieve a value by key"""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete a value by key"""
        pass


class InMemoryStore(StateStoreProvider):
    """In-memory state storage (default for development)"""
    
    def __init__(self, ttl_seconds: int = 3600):
        """
        Initialize in-memory store
        
        Args:
            ttl_seconds: Time-to-live for entries (default 1 hour)
        """
        self.store: Dict[str, Dict[Any, Any]] = {}
        self.ttl_seconds = ttl_seconds
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # Cleanup every 5 minutes
        logger.info(f"Initialized InMemoryStore with TTL={ttl_seconds}s")
    
    def put(self, key: str, value: Dict[Any, Any]) -> None:
        """Store a value with a key and timestamp"""
        self._cleanup_if_needed()
        value['_timestamp'] = time.time()
        self.store[key] = value
        logger.debug(f"Stored state for key={key}")
    
    def get(self, key: str) -> Optional[Dict[Any, Any]]:
        """Retrieve a value by key if not expired"""
        self._cleanup_if_needed()
        
        if key not in self.store:
            logger.debug(f"Key not found: {key}")
            return None
        
        value = self.store[key]
        timestamp = value.get('_timestamp', 0)
        
        # Check if expired
        if time.time() - timestamp > self.ttl_seconds:
            logger.debug(f"Key expired: {key}")
            del self.store[key]
            return None
        
        logger.debug(f"Retrieved state for key={key}")
        return value
    
    def delete(self, key: str) -> None:
        """Delete a value by key"""
        if key in self.store:
            del self.store[key]
            logger.debug(f"Deleted state for key={key}")
    
    def _cleanup_if_needed(self) -> None:
        """Remove expired entries periodically"""
        current_time = time.time()
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        self._last_cleanup = current_time
        expired_keys = []
        
        for key, value in self.store.items():
            timestamp = value.get('_timestamp', 0)
            if current_time - timestamp > self.ttl_seconds:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.store[key]
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired entries")


class RedisStore(StateStoreProvider):
    """Redis state storage (for production)"""
    
    def __init__(self, host='localhost', port=6379, db=0, ttl_seconds=3600, **kwargs):
        """
        Initialize Redis store
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            ttl_seconds: Time-to-live for entries (default 1 hour)
            **kwargs: Additional Redis connection parameters
        """
        if redis is None:
            raise ImportError("Redis is not installed. Install with: pip install redis")
        
        self.client = redis.Redis(
            host=host, 
            port=port, 
            db=db, 
            decode_responses=True,
            **kwargs
        )
        self.ttl_seconds = ttl_seconds
        
        # Test connection
        try:
            self.client.ping()
            logger.info(f"Connected to Redis at {host}:{port}/{db}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    def put(self, key: str, value: Dict[Any, Any]) -> None:
        """Store a value with a key and TTL"""
        # Add timestamp for consistency with in-memory store
        value['_timestamp'] = time.time()
        
        # Prefix key to avoid collisions
        redis_key = f"paymcp:{key}"
        
        # Store as JSON with TTL
        self.client.setex(
            redis_key, 
            self.ttl_seconds, 
            json.dumps(value)
        )
        logger.debug(f"Stored state in Redis for key={key}")
    
    def get(self, key: str) -> Optional[Dict[Any, Any]]:
        """Retrieve a value by key"""
        redis_key = f"paymcp:{key}"
        data = self.client.get(redis_key)
        
        if data is None:
            logger.debug(f"Key not found in Redis: {key}")
            return None
        
        try:
            value = json.loads(data)
            logger.debug(f"Retrieved state from Redis for key={key}")
            return value
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode Redis value for key={key}: {e}")
            return None
    
    def delete(self, key: str) -> None:
        """Delete a value by key"""
        redis_key = f"paymcp:{key}"
        result = self.client.delete(redis_key)
        if result:
            logger.debug(f"Deleted state from Redis for key={key}")
        else:
            logger.debug(f"Key not found in Redis for deletion: {key}")