"""
StateStoreProvider for PayMCP - ENG-114 Timeout Fix
Simple state storage with only 3 methods (put, get, delete)
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, TypedDict, Final
from dataclasses import dataclass
import json
import time
import logging

try:
    import redis
except ImportError:
    redis = None

logger = logging.getLogger(__name__)


class PaymentState(TypedDict, total=False):
    """Type definition for payment state"""
    session_id: Optional[str]
    payment_id: str
    payment_url: str
    tool_name: str
    tool_args: Dict[str, Any]
    status: str
    created_at: float
    _timestamp: float  # Internal timestamp for TTL


class StateStoreProvider(ABC):
    """Abstract base class for state storage providers with payment_id indexing"""

    @abstractmethod
    def put(self, key: str, value: PaymentState) -> None:
        """Store a value with a key"""
        pass

    @abstractmethod
    def get(self, key: str) -> Optional[PaymentState]:
        """Retrieve a value by key"""
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete a value by key"""
        pass

    @abstractmethod
    def get_by_payment_id(self, payment_id: str) -> Optional[PaymentState]:
        """Retrieve a value by payment_id (O(1) lookup)"""
        pass


class InMemoryStore(StateStoreProvider):
    """In-memory state storage with payment_id index for O(1) lookups"""

    def __init__(self, ttl_seconds: int = 3600):
        """
        Initialize in-memory store with dual indexing

        Args:
            ttl_seconds: Time-to-live for entries (default 1 hour)
        """
        self.store: Dict[str, PaymentState] = {}
        # Hash index: payment_id -> key for O(1) payment_id lookups
        self.payment_index: Dict[str, str] = {}
        self.ttl_seconds = ttl_seconds
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # Cleanup every 5 minutes
        logger.info(f"Initialized InMemoryStore with TTL={ttl_seconds}s and payment_id index")
    
    def put(self, key: str, value: PaymentState) -> None:
        """Store a value with a key and update payment_id index"""
        self._cleanup_if_needed()
        value['_timestamp'] = time.time()

        # Update primary storage
        self.store[key] = value

        # Update payment_id index for O(1) lookups
        payment_id = value.get('payment_id')
        if payment_id:
            # Remove old index entry if key is being updated
            if key in self.store:
                old_payment_id = self.store[key].get('payment_id')
                if old_payment_id and old_payment_id in self.payment_index:
                    del self.payment_index[old_payment_id]

            # Add new index entry
            self.payment_index[payment_id] = key
            logger.debug(f"Indexed payment_id={payment_id} -> key={key}")

        logger.debug(f"Stored state for key={key}")
    
    def get(self, key: str) -> Optional[PaymentState]:
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
            self._delete_with_index(key)
            return None

        logger.debug(f"Retrieved state for key={key}")
        return value

    def get_by_payment_id(self, payment_id: str) -> Optional[PaymentState]:
        """Retrieve a value by payment_id using O(1) hash lookup"""
        # Use payment_id index for direct lookup
        if payment_id not in self.payment_index:
            logger.debug(f"Payment ID not found in index: {payment_id}")
            return None

        key = self.payment_index[payment_id]
        logger.debug(f"Found key={key} for payment_id={payment_id} via index")
        return self.get(key)
    
    def delete(self, key: str) -> None:
        """Delete a value by key and update index"""
        self._delete_with_index(key)

    def _delete_with_index(self, key: str) -> None:
        """Internal delete that also updates payment_id index"""
        if key in self.store:
            # Remove from payment_id index
            payment_id = self.store[key].get('payment_id')
            if payment_id and payment_id in self.payment_index:
                del self.payment_index[payment_id]
                logger.debug(f"Removed payment_id={payment_id} from index")

            # Remove from primary storage
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
            self._delete_with_index(key)

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
    
    def put(self, key: str, value: PaymentState) -> None:
        """Store a value with a key and TTL, update payment_id index"""
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

        # Update payment_id index for O(1) lookups
        payment_id = value.get('payment_id')
        if payment_id:
            # Create index entry: payment_id -> key
            index_key = f"paymcp:idx:payment:{payment_id}"
            self.client.setex(index_key, self.ttl_seconds, key)
            logger.debug(f"Indexed payment_id={payment_id} -> key={key} in Redis")

        logger.debug(f"Stored state in Redis for key={key}")
    
    def get(self, key: str) -> Optional[PaymentState]:
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

    def get_by_payment_id(self, payment_id: str) -> Optional[PaymentState]:
        """Retrieve a value by payment_id using O(1) Redis lookup"""
        # Look up key from payment_id index
        index_key = f"paymcp:idx:payment:{payment_id}"
        key = self.client.get(index_key)

        if key is None:
            logger.debug(f"Payment ID not found in Redis index: {payment_id}")
            return None

        logger.debug(f"Found key={key} for payment_id={payment_id} via Redis index")
        return self.get(key)
    
    def delete(self, key: str) -> None:
        """Delete a value by key and remove from payment_id index"""
        redis_key = f"paymcp:{key}"

        # Get value first to find payment_id for index cleanup
        data = self.client.get(redis_key)
        if data:
            try:
                value = json.loads(data)
                payment_id = value.get('payment_id')
                if payment_id:
                    # Delete from payment_id index
                    index_key = f"paymcp:idx:payment:{payment_id}"
                    self.client.delete(index_key)
                    logger.debug(f"Removed payment_id={payment_id} from Redis index")
            except json.JSONDecodeError:
                pass

        # Delete primary key
        result = self.client.delete(redis_key)
        if result:
            logger.debug(f"Deleted state from Redis for key={key}")
        else:
            logger.debug(f"Key not found in Redis for deletion: {key}")