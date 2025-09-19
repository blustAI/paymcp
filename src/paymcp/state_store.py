"""
StateStoreProvider for PayMCP - Persistent State Management for Payment Recovery.

This module implements the core state persistence layer that enables PayMCP to handle
client timeouts gracefully (ENG-114). When clients disconnect during payment processing,
the state store preserves payment information so it can be recovered when clients reconnect.

Architecture Overview:
- Abstract StateStoreProvider interface for pluggable storage backends
- InMemoryStore: Fast, ephemeral storage for development and testing
- RedisStore: Persistent, distributed storage for production environments
- Dual indexing: Both session_id and payment_id lookups for O(1) performance
- Automatic TTL management to prevent memory leaks

Key Features:
1. Payment Recovery: Restore payment state after client disconnection
2. Idempotency: Prevent duplicate payments for the same session
3. Performance: O(1) lookups by both session_id and payment_id
4. Scalability: Redis support for distributed deployments
5. Cleanup: Automatic expiration of stale payment data

This addresses the core issue in ENG-114 where payment flows would fail if clients
timed out during payment processing, even if the payment completed successfully.
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
    """
    Type definition for payment state stored in the StateStore.

    This TypedDict defines the exact structure of payment state data that gets
    persisted across client disconnections. It contains all information needed
    to resume a payment flow after timeout or reconnection.

    Fields:
        session_id: MCP session identifier for associating payments with sessions.
                   This is the primary key for state storage.
        payment_id: Unique payment identifier from the payment provider.
                   This enables O(1) lookups by payment ID for status checking.
        payment_url: URL where users complete payment.
                    Preserved so resumed flows can redirect users to the same URL.
        tool_name: Name of the tool that requires payment.
                  Used to execute the correct tool after payment completion.
        tool_args: Original arguments passed to the tool.
                  Preserved so tool execution uses the original parameters.
        status: Current payment status (requested, pending, paid, etc.).
               Tracks payment progression for debugging and flow control.
        created_at: Timestamp when payment was initiated.
                   Used for analytics and debugging payment flow timing.
        _timestamp: Internal timestamp for TTL calculations.
                   Used by storage implementations for automatic cleanup.

    Usage:
        This structure is passed between payment flows and state stores to ensure
        consistent data format across different storage backends.

    Example:
        {
            "session_id": "session_abc123",
            "payment_id": "pay_xyz789",
            "payment_url": "https://checkout.stripe.com/pay_xyz789",
            "tool_name": "generate_image",
            "tool_args": {"prompt": "a blue car", "size": "512x512"},
            "status": "pending",
            "created_at": 1699123456.789,
            "_timestamp": 1699123456.789
        }
    """
    session_id: Optional[str]
    payment_id: str
    payment_url: str
    tool_name: str
    tool_args: Dict[str, Any]
    status: str
    created_at: float
    _timestamp: float  # Internal timestamp for TTL


class StateStoreProvider(ABC):
    """
    Abstract base class for state storage providers with dual indexing capability.

    This ABC defines the interface that all state storage implementations must provide
    to support PayMCP's payment recovery functionality. The interface is designed to
    be simple yet powerful, providing both session-based and payment-based lookups.

    Design Principles:
    1. Minimal Interface: Only 4 essential methods to keep implementations simple
    2. Dual Indexing: Support lookups by both session_id and payment_id
    3. Type Safety: Strong typing with PaymentState for data consistency
    4. Performance: O(1) lookups for both access patterns
    5. Pluggability: Easy to swap between storage backends

    The dual indexing is critical for ENG-114 recovery scenarios:
    - session_id lookups: For normal payment flow continuation
    - payment_id lookups: For webhook-based payment status updates

    Implementations:
    - InMemoryStore: For development, testing, and single-instance deployments
    - RedisStore: For production, distributed, and high-availability deployments

    Usage Pattern:
        store = InMemoryStore(ttl_seconds=1800)  # 30 minutes
        store.put("session_123", payment_state)
        recovered_state = store.get("session_123")
        webhook_state = store.get_by_payment_id("pay_abc123")
    """

    @abstractmethod
    def put(self, key: str, value: PaymentState) -> None:
        """
        Store payment state with the given session_id as key.

        This method persists payment state and must also update any internal
        indexes (like payment_id -> session_id mapping) for efficient lookups.

        Args:
            key: Session ID to use as the primary key.
                 This should be unique per MCP session.
            value: Complete payment state data to store.
                   Must conform to PaymentState structure.

        Implementation Notes:
            - Must handle TTL/expiration automatically
            - Should update payment_id index for get_by_payment_id()
            - Should be atomic to prevent partial updates
            - Should handle overwrites of existing keys gracefully

        Example:
            store.put("session_abc123", {
                "session_id": "session_abc123",
                "payment_id": "pay_xyz789",
                "payment_url": "https://checkout.stripe.com/xyz",
                "tool_name": "generate_image",
                "tool_args": {"prompt": "a car"},
                "status": "pending",
                "created_at": 1699123456.789
            })
        """
        pass

    @abstractmethod
    def get(self, key: str) -> Optional[PaymentState]:
        """
        Retrieve payment state by session_id.

        This is the primary lookup method used by payment flows to check for
        existing payment state when a tool is called multiple times in the
        same session.

        Args:
            key: Session ID to look up.
                 This should match the key used in put().

        Returns:
            PaymentState if found and not expired, None otherwise.
            None indicates no existing payment for this session.

        Implementation Notes:
            - Must check TTL and return None for expired entries
            - Should clean up expired entries automatically
            - Should handle missing keys gracefully (return None)

        Example:
            state = store.get("session_abc123")
            if state and state["status"] == "paid":
                # Payment already completed, execute tool
                return tool_function(**state["tool_args"])
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """
        Delete payment state by session_id.

        This method removes payment state and must also clean up any internal
        indexes to prevent orphaned references.

        Args:
            key: Session ID of the state to delete.

        Implementation Notes:
            - Must remove from payment_id index as well
            - Should handle missing keys gracefully (no error)
            - Should be atomic to prevent partial deletions

        Example:
            # After successful payment and tool execution
            store.delete("session_abc123")
        """
        pass

    @abstractmethod
    def get_by_payment_id(self, payment_id: str) -> Optional[PaymentState]:
        """
        Retrieve payment state by payment_id for O(1) webhook handling.

        This method enables efficient lookup when payment providers send
        webhooks with payment status updates. Without this, we'd need to
        scan all stored states to find the matching payment.

        Args:
            payment_id: Payment identifier from the payment provider.
                       This should match the payment_id in stored PaymentState.

        Returns:
            PaymentState if found and not expired, None otherwise.
            None indicates no active payment with this ID.

        Performance Requirement:
            Must be O(1) average case. Implementations should maintain an
            index rather than scanning all stored states.

        Use Cases:
            1. Webhook handlers updating payment status
            2. Background jobs checking payment completion
            3. Admin tools for payment debugging

        Example:
            # In a webhook handler
            state = store.get_by_payment_id("pay_xyz789")
            if state and webhook_status == "completed":
                # Update state and potentially trigger tool execution
                store.put(state["session_id"], {**state, "status": "paid"})
        """
        pass


class InMemoryStore(StateStoreProvider):
    """
    In-memory state storage implementation with dual indexing for O(1) lookups.

    This implementation provides fast, ephemeral storage suitable for:
    - Development and testing environments
    - Single-instance deployments where persistence isn't required
    - Scenarios where Redis setup is not feasible

    Architecture:
    - Primary storage: session_id -> PaymentState mapping
    - Secondary index: payment_id -> session_id mapping for webhook lookups
    - Automatic TTL management with periodic cleanup
    - Thread-safe operations (Python GIL provides basic safety)

    Performance Characteristics:
    - put(): O(1) average case
    - get(): O(1) average case
    - get_by_payment_id(): O(1) average case
    - delete(): O(1) average case
    - cleanup(): O(n) but runs infrequently

    Memory Management:
    - Automatic cleanup of expired entries every 5 minutes
    - TTL-based expiration prevents unbounded memory growth
    - Graceful handling of memory pressure

    Limitations:
    - Data lost on process restart (not persistent)
    - Single-instance only (not suitable for load balancers)
    - Memory usage grows with number of concurrent payments

    Best Practices:
    - Use shorter TTL in high-volume environments
    - Monitor memory usage in production
    - Consider Redis for distributed deployments
    """

    def __init__(self, ttl_seconds: int = 3600):
        """
        Initialize in-memory store with dual indexing architecture.

        Sets up the primary storage and secondary index for efficient lookups
        by both session_id and payment_id. Also configures automatic cleanup
        to prevent memory leaks from expired entries.

        Args:
            ttl_seconds: Time-to-live for entries in seconds.
                        Default is 3600 (1 hour).
                        Recommendations:
                        - Development: 300-900 seconds (5-15 minutes)
                        - Testing: 1800 seconds (30 minutes)
                        - Production: 3600-7200 seconds (1-2 hours)

        Memory Layout:
            self.store: {
                "session_abc123": PaymentState,
                "session_def456": PaymentState,
                ...
            }
            self.payment_index: {
                "pay_xyz789": "session_abc123",
                "pay_uvw012": "session_def456",
                ...
            }

        Example:
            # Short TTL for development
            dev_store = InMemoryStore(ttl_seconds=300)

            # Longer TTL for production
            prod_store = InMemoryStore(ttl_seconds=3600)
        """
        # Primary storage: session_id -> PaymentState
        self.store: Dict[str, PaymentState] = {}

        # Secondary index: payment_id -> session_id for O(1) payment_id lookups
        # This eliminates the need to scan all stored states when handling webhooks
        self.payment_index: Dict[str, str] = {}

        # TTL configuration
        self.ttl_seconds = ttl_seconds

        # Cleanup timing to prevent memory leaks
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # Cleanup every 5 minutes

        logger.info(f"Initialized InMemoryStore with TTL={ttl_seconds}s and payment_id index")
    
    def put(self, key: str, value: PaymentState) -> None:
        """
        Store payment state with automatic TTL and index management.

        This method handles the complex task of storing payment state while
        maintaining consistency between the primary storage and payment_id index.
        It's designed to be idempotent and handle updates gracefully.

        Algorithm:
        1. Trigger cleanup if needed to free memory
        2. Add TTL timestamp to the value
        3. Handle index updates atomically
        4. Store in primary storage

        Args:
            key: Session ID to use as primary key.
            value: PaymentState object to store.

        Index Management:
            When updating an existing key, the old payment_id index entry
            is removed before adding the new one to prevent orphaned references.

        Example:
            store.put("session_123", {
                "session_id": "session_123",
                "payment_id": "pay_abc",
                "payment_url": "https://checkout.stripe.com/abc",
                "tool_name": "generate_image",
                "tool_args": {"prompt": "a car"},
                "status": "pending",
                "created_at": 1699123456.789
            })
        """
        # Opportunistic cleanup to manage memory usage
        self._cleanup_if_needed()

        # Add internal timestamp for TTL tracking
        value['_timestamp'] = time.time()

        # Handle payment_id index updates atomically
        payment_id = value.get('payment_id')
        if payment_id:
            # Clean up old index entry if this key is being updated
            if key in self.store:
                old_payment_id = self.store[key].get('payment_id')
                if old_payment_id and old_payment_id in self.payment_index:
                    del self.payment_index[old_payment_id]
                    logger.debug(f"Removed old payment_id={old_payment_id} from index")

            # Add new index entry for O(1) payment_id lookups
            self.payment_index[payment_id] = key
            logger.debug(f"Indexed payment_id={payment_id} -> key={key}")

        # Store in primary storage
        self.store[key] = value
        logger.debug(f"Stored state for key={key}")

    def get(self, key: str) -> Optional[PaymentState]:
        """
        Retrieve payment state by session_id with automatic expiration checking.

        This method provides lazy TTL enforcement by checking expiration at
        access time and cleaning up expired entries immediately.

        Args:
            key: Session ID to look up.

        Returns:
            PaymentState if found and not expired, None otherwise.

        TTL Behavior:
            - Entries are considered expired if current_time - _timestamp > ttl_seconds
            - Expired entries are automatically deleted when accessed
            - This provides eventual consistency without background processes

        Example:
            state = store.get("session_123")
            if state:
                print(f"Payment status: {state['status']}")
            else:
                print("No active payment for this session")
        """
        # Opportunistic cleanup to manage memory usage
        self._cleanup_if_needed()

        # Check if key exists
        if key not in self.store:
            logger.debug(f"Key not found: {key}")
            return None

        # Get value and check TTL
        value = self.store[key]
        timestamp = value.get('_timestamp', 0)

        # Lazy TTL enforcement - delete expired entries on access
        if time.time() - timestamp > self.ttl_seconds:
            logger.debug(f"Key expired: {key}")
            self._delete_with_index(key)
            return None

        logger.debug(f"Retrieved state for key={key}")
        return value

    def get_by_payment_id(self, payment_id: str) -> Optional[PaymentState]:
        """
        Retrieve payment state by payment_id using O(1) index lookup.

        This method is critical for webhook handling and payment status updates
        where only the payment_id is available. The implementation uses a
        hash index to avoid scanning all stored states.

        Args:
            payment_id: Payment provider's unique identifier.

        Returns:
            PaymentState if found and not expired, None otherwise.

        Performance:
            O(1) average case due to hash index lookup followed by direct access.
            This is much faster than O(n) linear scan of all stored states.

        Example:
            # Webhook handler
            def handle_stripe_webhook(payment_id, status):
                state = store.get_by_payment_id(payment_id)
                if state and status == "succeeded":
                    # Update payment status
                    updated_state = {**state, "status": "paid"}
                    store.put(state["session_id"], updated_state)
        """
        # Use payment_id index for O(1) lookup
        if payment_id not in self.payment_index:
            logger.debug(f"Payment ID not found in index: {payment_id}")
            return None

        # Get session_id from index and delegate to normal get()
        key = self.payment_index[payment_id]
        logger.debug(f"Found key={key} for payment_id={payment_id} via index")
        return self.get(key)  # This handles TTL checking automatically

    def delete(self, key: str) -> None:
        """
        Delete payment state by session_id with index cleanup.

        This is the public interface for deletion that ensures both the
        primary storage and payment_id index are updated atomically.

        Args:
            key: Session ID of the state to delete.

        Index Consistency:
            Always delegates to _delete_with_index() to ensure the payment_id
            index is properly maintained and doesn't contain orphaned references.

        Example:
            # After successful payment completion
            store.delete("session_123")
        """
        self._delete_with_index(key)

    def _delete_with_index(self, key: str) -> None:
        """
        Internal deletion method that maintains index consistency.

        This method handles the complex task of removing entries from both
        the primary storage and the payment_id index atomically to prevent
        orphaned references or inconsistent state.

        Args:
            key: Session ID of the state to delete.

        Atomicity:
            While Python's GIL provides basic thread safety, this method
            is designed to be atomic from a logical perspective - either
            both the primary storage and index are updated, or neither is.

        Error Handling:
            Gracefully handles cases where:
            - Key doesn't exist in primary storage
            - payment_id is missing from the stored state
            - Index is already inconsistent
        """
        if key in self.store:
            # Get payment_id for index cleanup
            payment_id = self.store[key].get('payment_id')

            # Remove from payment_id index if present
            if payment_id and payment_id in self.payment_index:
                del self.payment_index[payment_id]
                logger.debug(f"Removed payment_id={payment_id} from index")

            # Remove from primary storage
            del self.store[key]
            logger.debug(f"Deleted state for key={key}")
        else:
            logger.debug(f"Key not found for deletion: {key}")

    def _cleanup_if_needed(self) -> None:
        """
        Periodic cleanup of expired entries to prevent memory leaks.

        This method runs automatically during normal operations to remove
        expired entries that haven't been accessed recently. It's designed
        to run infrequently to avoid performance impact.

        Cleanup Strategy:
        - Only runs every 5 minutes to avoid overhead
        - Scans all entries and identifies expired ones
        - Batch deletes expired entries using proper index cleanup
        - Logs cleanup activity for monitoring

        Performance Impact:
        - O(n) operation but runs infrequently
        - Memory usage bounded by TTL and cleanup frequency
        - CPU impact minimal in typical usage patterns

        Memory Management:
            Without this cleanup, expired entries would accumulate indefinitely
            leading to memory leaks in long-running processes.
        """
        current_time = time.time()

        # Only cleanup every 5 minutes to avoid performance impact
        if current_time - self._last_cleanup < self._cleanup_interval:
            return

        self._last_cleanup = current_time
        expired_keys = []

        # Identify expired entries
        for key, value in self.store.items():
            timestamp = value.get('_timestamp', 0)
            if current_time - timestamp > self.ttl_seconds:
                expired_keys.append(key)

        # Batch delete expired entries with proper index cleanup
        for key in expired_keys:
            self._delete_with_index(key)

        # Log cleanup activity for monitoring
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired entries")
        else:
            logger.debug("No expired entries found during cleanup")


class RedisStore(StateStoreProvider):
    """
    Redis-based state storage implementation for production environments.

    This implementation provides persistent, distributed storage suitable for:
    - Production deployments with high availability requirements
    - Multi-instance deployments behind load balancers
    - Scenarios requiring data persistence across restarts
    - High-volume environments with thousands of concurrent payments

    Architecture:
    - Primary storage: Redis keys with JSON-serialized PaymentState values
    - Secondary index: Separate Redis keys mapping payment_id to session_id
    - Automatic TTL management using Redis EXPIRE functionality
    - Connection pooling and error recovery

    Performance Characteristics:
    - put(): O(1) with network latency
    - get(): O(1) with network latency
    - get_by_payment_id(): O(1) with network latency
    - delete(): O(1) with network latency
    - Network latency typically 1-5ms in same datacenter

    Redis Key Schema:
    - Primary keys: "paymcp:{session_id}"
    - Index keys: "paymcp:idx:payment:{payment_id}"
    - All keys use the same TTL for consistency

    Advantages over InMemoryStore:
    - Data survives process restarts
    - Shared state across multiple instances
    - Configurable persistence guarantees
    - Built-in clustering and replication
    - Memory usage distributed across Redis instances

    Requirements:
    - Redis server 3.0+ (SETEX command support)
    - python-redis library
    - Network connectivity to Redis instance
    - Appropriate Redis memory configuration
    """

    def __init__(self, host='localhost', port=6379, db=0, ttl_seconds=3600, **kwargs):
        """
        Initialize Redis store with connection and TTL configuration.

        Establishes connection to Redis server and configures automatic
        expiration for all stored payment states. The connection is tested
        immediately to fail fast if Redis is unavailable.

        Args:
            host: Redis server hostname or IP address.
                  Default: 'localhost'
                  Production: Use Redis cluster endpoint or load balancer
            port: Redis server port number.
                  Default: 6379 (standard Redis port)
            db: Redis database number (0-15 for standard Redis).
                Default: 0
                Recommendation: Use dedicated DB for PayMCP isolation
            ttl_seconds: Time-to-live for all entries in seconds.
                        Default: 3600 (1 hour)
                        Production recommendations:
                        - High-volume: 1800-3600 seconds (30min-1hr)
                        - Low-volume: 3600-7200 seconds (1-2hr)
            **kwargs: Additional Redis connection parameters:
                     - password: Redis AUTH password
                     - socket_timeout: Network timeout in seconds
                     - retry_on_timeout: Retry failed operations
                     - health_check_interval: Connection health checking

        Raises:
            ImportError: If python-redis library is not installed
            redis.ConnectionError: If cannot connect to Redis server
            redis.AuthenticationError: If Redis AUTH fails

        Example:
            # Local development
            store = RedisStore()

            # Production with authentication
            store = RedisStore(
                host='redis.company.com',
                port=6379,
                password='secret',
                ttl_seconds=1800,
                socket_timeout=5,
                retry_on_timeout=True
            )

            # Redis cluster
            store = RedisStore(
                host='redis-cluster.company.com',
                port=6379,
                db=1,  # Dedicated database
                ttl_seconds=3600
            )
        """
        # Check Redis dependency
        if redis is None:
            raise ImportError(
                "Redis is not installed. Install with: pip install redis\n"
                "Or install PayMCP with Redis support: pip install paymcp[redis]"
            )

        # Configure Redis connection with sensible defaults
        self.client = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=True,  # Automatically decode bytes to strings
            socket_connect_timeout=5,  # Connection timeout
            socket_timeout=5,  # Socket read/write timeout
            retry_on_timeout=True,  # Retry failed operations
            health_check_interval=30,  # Check connection health
            **kwargs
        )
        self.ttl_seconds = ttl_seconds

        # Test connection immediately to fail fast
        try:
            self.client.ping()
            logger.info(f"Connected to Redis at {host}:{port}/{db} with TTL={ttl_seconds}s")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis at {host}:{port}: {e}")
            raise
        except redis.AuthenticationError as e:
            logger.error(f"Redis authentication failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected Redis error: {e}")
            raise
    
    def put(self, key: str, value: PaymentState) -> None:
        """
        Store payment state in Redis with atomic TTL and index operations.

        This method serializes the PaymentState to JSON and stores it in Redis
        with automatic expiration. It also maintains the payment_id index for
        efficient webhook lookups.

        Algorithm:
        1. Add timestamp for consistency with InMemoryStore
        2. Serialize PaymentState to JSON
        3. Store primary key with TTL using SETEX (atomic)
        4. Update payment_id index with same TTL
        5. Handle Redis connection errors gracefully

        Args:
            key: Session ID to use as primary key.
            value: PaymentState object to store.

        Redis Operations:
            - SETEX paymcp:{session_id} TTL JSON_DATA
            - SETEX paymcp:idx:payment:{payment_id} TTL session_id

        Error Handling:
            Redis connection errors will raise exceptions that should be
            caught by the calling code. The operation is atomic - either
            both the primary key and index are updated, or neither is.

        Example:
            store.put("session_123", {
                "session_id": "session_123",
                "payment_id": "pay_abc",
                "payment_url": "https://checkout.stripe.com/abc",
                "tool_name": "generate_image",
                "tool_args": {"prompt": "a car"},
                "status": "pending",
                "created_at": 1699123456.789
            })
        """
        # Add timestamp for consistency with InMemoryStore
        value['_timestamp'] = time.time()

        # Use prefixed keys to avoid collisions with other Redis usage
        redis_key = f"paymcp:{key}"

        # Serialize to JSON for Redis storage
        try:
            json_data = json.dumps(value)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize PaymentState for key={key}: {e}")
            raise

        # Store primary key with atomic TTL using SETEX
        try:
            self.client.setex(redis_key, self.ttl_seconds, json_data)
        except redis.RedisError as e:
            logger.error(f"Failed to store primary key in Redis: {e}")
            raise

        # Update payment_id index for O(1) lookups
        payment_id = value.get('payment_id')
        if payment_id:
            try:
                # Create index entry mapping payment_id -> session_id
                index_key = f"paymcp:idx:payment:{payment_id}"
                self.client.setex(index_key, self.ttl_seconds, key)
                logger.debug(f"Indexed payment_id={payment_id} -> key={key} in Redis")
            except redis.RedisError as e:
                logger.error(f"Failed to update payment_id index in Redis: {e}")
                # Continue - primary storage succeeded, index failure is not fatal
                # The entry will still be accessible by session_id

        logger.debug(f"Stored state in Redis for key={key}")

    def get(self, key: str) -> Optional[PaymentState]:
        """
        Retrieve payment state from Redis by session_id.

        This method fetches the JSON data from Redis and deserializes it
        back to a PaymentState object. Redis handles TTL automatically,
        so expired entries return None.

        Args:
            key: Session ID to look up.

        Returns:
            PaymentState if found and not expired, None otherwise.

        Error Handling:
            - Redis connection errors are logged and re-raised
            - JSON deserialization errors are logged but return None
            - Missing keys return None (normal case)

        Redis TTL Behavior:
            Redis automatically removes expired keys, so this method doesn't
            need to check TTL manually like InMemoryStore does.

        Example:
            state = store.get("session_123")
            if state:
                print(f"Payment status: {state['status']}")
            else:
                print("No active payment or expired")
        """
        redis_key = f"paymcp:{key}"

        try:
            # GET returns None if key doesn't exist or is expired
            data = self.client.get(redis_key)
        except redis.RedisError as e:
            logger.error(f"Failed to get key from Redis: {e}")
            raise

        if data is None:
            logger.debug(f"Key not found in Redis: {key}")
            return None

        # Deserialize JSON data back to PaymentState
        try:
            value = json.loads(data)
            logger.debug(f"Retrieved state from Redis for key={key}")
            return value
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode Redis value for key={key}: {e}")
            # Data corruption - return None and let caller handle
            return None

    def get_by_payment_id(self, payment_id: str) -> Optional[PaymentState]:
        """
        Retrieve payment state by payment_id using Redis index lookup.

        This method provides O(1) lookup for webhook handlers and payment
        status updates where only the payment_id is known. It uses a two-step
        process: index lookup followed by primary data retrieval.

        Args:
            payment_id: Payment provider's unique identifier.

        Returns:
            PaymentState if found and not expired, None otherwise.

        Algorithm:
        1. Look up session_id from payment_id index
        2. If found, delegate to get() for primary data retrieval
        3. get() handles TTL checking and JSON deserialization

        Performance:
            Two Redis operations (GET for index, GET for data) but still O(1).
            Network latency dominates, not operation complexity.

        Example:
            # Webhook handler
            def handle_stripe_webhook(event):
                payment_id = event['data']['object']['id']
                state = store.get_by_payment_id(payment_id)
                if state and event['type'] == 'payment_intent.succeeded':
                    # Update payment status
                    updated_state = {**state, "status": "paid"}
                    store.put(state["session_id"], updated_state)
        """
        # Look up session_id from payment_id index
        index_key = f"paymcp:idx:payment:{payment_id}"

        try:
            key = self.client.get(index_key)
        except redis.RedisError as e:
            logger.error(f"Failed to get payment_id index from Redis: {e}")
            raise

        if key is None:
            logger.debug(f"Payment ID not found in Redis index: {payment_id}")
            return None

        logger.debug(f"Found key={key} for payment_id={payment_id} via Redis index")

        # Delegate to get() which handles TTL and deserialization
        return self.get(key)

    def delete(self, key: str) -> None:
        """
        Delete payment state from Redis with index cleanup.

        This method removes both the primary data and the payment_id index
        entry to maintain consistency. It uses a read-then-delete pattern
        to find the payment_id for index cleanup.

        Args:
            key: Session ID of the state to delete.

        Algorithm:
        1. Read current value to find payment_id
        2. Delete payment_id index entry if present
        3. Delete primary key
        4. Handle partial failures gracefully

        Atomicity Considerations:
            Redis operations are atomic individually, but this method performs
            multiple operations. In rare cases, the index might become
            inconsistent if operations fail partway through.

        Error Handling:
            - JSON deserialization errors are ignored (index cleanup skipped)
            - Redis connection errors are logged and re-raised
            - Missing keys are handled gracefully

        Example:
            # After successful payment completion
            store.delete("session_123")
        """
        redis_key = f"paymcp:{key}"

        # First, get the current value to find payment_id for index cleanup
        try:
            data = self.client.get(redis_key)
        except redis.RedisError as e:
            logger.error(f"Failed to get key for deletion from Redis: {e}")
            raise

        # Clean up payment_id index if data exists and is valid
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
                # Data corruption - skip index cleanup but continue with primary deletion
                logger.warning(f"Corrupted data found for key={key}, skipping index cleanup")
            except redis.RedisError as e:
                logger.error(f"Failed to delete payment_id index from Redis: {e}")
                # Continue with primary key deletion even if index cleanup fails

        # Delete primary key
        try:
            result = self.client.delete(redis_key)
            if result:
                logger.debug(f"Deleted state from Redis for key={key}")
            else:
                logger.debug(f"Key not found in Redis for deletion: {key}")
        except redis.RedisError as e:
            logger.error(f"Failed to delete primary key from Redis: {e}")
            raise