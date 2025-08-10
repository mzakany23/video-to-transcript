"""
Resilience patterns: retry, circuit breaker, timeout handling
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Optional

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """Retry strategies"""

    FIXED_DELAY = "fixed_delay"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"


class CircuitBreakerState(Enum):
    """Circuit breaker states"""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class RetryConfig:
    """Retry configuration"""

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    backoff_multiplier: float = 2.0
    jitter: bool = True


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""

    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    expected_exception: type = Exception


class RetryableError(Exception):
    """Base class for retryable errors"""

    pass


class NonRetryableError(Exception):
    """Base class for non-retryable errors"""

    pass


class CircuitBreakerError(Exception):
    """Circuit breaker is open"""

    pass


class CircuitBreaker:
    """Circuit breaker implementation"""

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.success_count = 0

    def can_execute(self) -> bool:
        """Check if execution is allowed"""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                logger.info("Circuit breaker state changed to HALF_OPEN")
                return True
            return False
        else:  # HALF_OPEN
            return True

    def record_success(self):
        """Record successful execution"""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= 3:  # Reset after 3 successes
                self._reset()
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = 0

    def record_failure(self):
        """Record failed execution"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.state == CircuitBreakerState.HALF_OPEN:
            self._trip()
        elif (
            self.state == CircuitBreakerState.CLOSED
            and self.failure_count >= self.config.failure_threshold
        ):
            self._trip()

    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset"""
        if self.last_failure_time is None:
            return True

        time_since_failure = datetime.now() - self.last_failure_time
        return time_since_failure.total_seconds() >= self.config.recovery_timeout

    def _trip(self):
        """Trip the circuit breaker"""
        self.state = CircuitBreakerState.OPEN
        logger.warning(f"Circuit breaker OPEN - {self.failure_count} failures")

    def _reset(self):
        """Reset the circuit breaker"""
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        logger.info("Circuit breaker CLOSED - reset successful")


def with_retry(config: RetryConfig):
    """Retry decorator"""

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    result = await func(*args, **kwargs)
                    if attempt > 0:
                        logger.info(f"{func.__name__} succeeded on attempt {attempt + 1}")
                    return result

                except NonRetryableError:
                    logger.error(f"{func.__name__} failed with non-retryable error")
                    raise

                except Exception as e:
                    last_exception = e

                    if attempt == config.max_attempts - 1:
                        logger.error(f"{func.__name__} failed after {config.max_attempts} attempts")
                        break

                    delay = _calculate_delay(config, attempt)
                    logger.warning(
                        f"{func.__name__} attempt {attempt + 1} failed: {str(e)}. "
                        f"Retrying in {delay:.2f}s"
                    )

                    await asyncio.sleep(delay)

            raise last_exception

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    result = func(*args, **kwargs)
                    if attempt > 0:
                        logger.info(f"{func.__name__} succeeded on attempt {attempt + 1}")
                    return result

                except NonRetryableError:
                    logger.error(f"{func.__name__} failed with non-retryable error")
                    raise

                except Exception as e:
                    last_exception = e

                    if attempt == config.max_attempts - 1:
                        logger.error(f"{func.__name__} failed after {config.max_attempts} attempts")
                        break

                    delay = _calculate_delay(config, attempt)
                    logger.warning(
                        f"{func.__name__} attempt {attempt + 1} failed: {str(e)}. "
                        f"Retrying in {delay:.2f}s"
                    )

                    time.sleep(delay)

            raise last_exception

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


def with_circuit_breaker(config: CircuitBreakerConfig):
    """Circuit breaker decorator"""
    circuit_breaker = CircuitBreaker(config)

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not circuit_breaker.can_execute():
                raise CircuitBreakerError("Circuit breaker is open")

            try:
                result = await func(*args, **kwargs)
                circuit_breaker.record_success()
                return result
            except config.expected_exception:
                circuit_breaker.record_failure()
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not circuit_breaker.can_execute():
                raise CircuitBreakerError("Circuit breaker is open")

            try:
                result = func(*args, **kwargs)
                circuit_breaker.record_success()
                return result
            except config.expected_exception:
                circuit_breaker.record_failure()
                raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


def with_timeout(timeout_seconds: float):
    """Timeout decorator"""

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                logger.error(f"{func.__name__} timed out after {timeout_seconds}s")
                raise

        # For sync functions, we can't easily implement timeout without threads
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger.warning(f"Timeout not implemented for sync function {func.__name__}")
            return func(*args, **kwargs)

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


def _calculate_delay(config: RetryConfig, attempt: int) -> float:
    """Calculate delay for retry attempt"""
    if config.strategy == RetryStrategy.FIXED_DELAY:
        delay = config.base_delay
    elif config.strategy == RetryStrategy.LINEAR_BACKOFF:
        delay = config.base_delay * (attempt + 1)
    else:  # EXPONENTIAL_BACKOFF
        delay = config.base_delay * (config.backoff_multiplier**attempt)

    # Apply max delay limit
    delay = min(delay, config.max_delay)

    # Add jitter if enabled
    if config.jitter:
        import random

        jitter = delay * 0.1 * random.random()  # Up to 10% jitter
        delay = delay + jitter

    return delay


# Convenience functions for common patterns
def retry_on_error(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
):
    """Simple retry decorator with common defaults"""
    config = RetryConfig(max_attempts=max_attempts, base_delay=base_delay, strategy=strategy)
    return with_retry(config)


def circuit_breaker(failure_threshold: int = 5, recovery_timeout: float = 60.0):
    """Simple circuit breaker decorator with common defaults"""
    config = CircuitBreakerConfig(
        failure_threshold=failure_threshold, recovery_timeout=recovery_timeout
    )
    return with_circuit_breaker(config)


def timeout(seconds: float):
    """Simple timeout decorator"""
    return with_timeout(seconds)


# Usage examples in docstring
"""
Usage Examples:

@retry_on_error(max_attempts=5, base_delay=2.0)
@timeout(30.0)
async def transcribe_audio(file_path: str):
    # This will retry up to 5 times with exponential backoff
    # and timeout after 30 seconds
    pass

@circuit_breaker(failure_threshold=3, recovery_timeout=120.0)
async def external_api_call():
    # Circuit breaker will open after 3 failures
    # and try again after 2 minutes
    pass

# Custom retry configuration
@with_retry(RetryConfig(
    max_attempts=10,
    base_delay=0.5,
    max_delay=30.0,
    strategy=RetryStrategy.LINEAR_BACKOFF
))
async def critical_operation():
    pass
"""
