"""
Network utilities for painminer.

Handles proxy configuration, HTTP transport, and request management.
"""

import random
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from painminer.config import NetworkConfig, ThrottlingConfig


class NetworkError(Exception):
    """Raised when network operations fail."""
    pass


class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""
    pass


@dataclass
class ProxyProvider:
    """
    Manages proxy rotation for network requests.

    Supports single proxy or pool rotation modes.
    """
    enabled: bool = False
    mode: str = "single"  # single | pool
    single_http: str = ""
    single_https: str = ""
    pool: list[str] = field(default_factory=list)
    rotate_every: int = 25
    _request_count: int = 0
    _current_pool_index: int = 0

    def get_proxies(self) -> dict[str, str] | None:
        """
        Get current proxy configuration.

        Returns:
            Dictionary with http and https proxy URLs, or None if disabled
        """
        if not self.enabled:
            return None

        if self.mode == "single":
            proxies = {}
            if self.single_http:
                proxies["http://"] = self.single_http
            if self.single_https:
                proxies["https://"] = self.single_https
            return proxies if proxies else None

        elif self.mode == "pool" and self.pool:
            # Rotate every N requests
            self._request_count += 1
            if self._request_count >= self.rotate_every:
                self._request_count = 0
                self._current_pool_index = (
                    self._current_pool_index + 1
                ) % len(self.pool)

            proxy_url = self.pool[self._current_pool_index]
            return {
                "http://": proxy_url,
                "https://": proxy_url,
            }

        return None

    def reset(self) -> None:
        """Reset rotation state."""
        self._request_count = 0
        self._current_pool_index = 0


class Throttler:
    """
    Rate limiter with exponential backoff.

    Ensures requests don't exceed rate limits and handles retries.
    """

    def __init__(
        self,
        min_delay_ms: int = 800,
        max_delay_ms: int = 2500,
        max_retries: int = 4,
        backoff_base_sec: float = 2.0,
    ) -> None:
        """
        Initialize throttler.

        Args:
            min_delay_ms: Minimum delay between requests in milliseconds
            max_delay_ms: Maximum delay between requests in milliseconds
            max_retries: Maximum number of retry attempts
            backoff_base_sec: Base for exponential backoff calculation
        """
        self.min_delay_ms = min_delay_ms
        self.max_delay_ms = max_delay_ms
        self.max_retries = max_retries
        self.backoff_base_sec = backoff_base_sec
        self._last_request_time: float = 0

    def wait(self) -> None:
        """
        Wait before making the next request.

        Adds a random delay between min_delay_ms and max_delay_ms.
        """
        now = time.time()

        # Calculate delay
        delay_ms = random.randint(self.min_delay_ms, self.max_delay_ms)
        delay_sec = delay_ms / 1000.0

        # Calculate time since last request
        elapsed = now - self._last_request_time

        # Wait if needed
        if elapsed < delay_sec:
            time.sleep(delay_sec - elapsed)

        self._last_request_time = time.time()

    def get_backoff_delay(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        # Exponential backoff with jitter
        base_delay = self.backoff_base_sec * (2 ** attempt)
        jitter = random.uniform(0, 0.5 * base_delay)
        return float(base_delay + jitter)

    def should_retry(self, attempt: int) -> bool:
        """
        Check if should retry after failure.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            True if should retry
        """
        return attempt < self.max_retries


class NetworkClient:
    """
    HTTP client with proxy and throttling support.

    Provides a unified interface for making HTTP requests with
    configurable proxies, timeouts, and rate limiting.
    """

    def __init__(
        self,
        network_config: NetworkConfig,
        throttling_config: ThrottlingConfig,
    ) -> None:
        """
        Initialize network client.

        Args:
            network_config: Network configuration
            throttling_config: Throttling configuration
        """
        self.timeout = network_config.timeout_sec

        # Set up proxy provider
        self.proxy_provider = ProxyProvider(
            enabled=network_config.proxies_enabled,
            mode=network_config.proxies_mode,
            single_http=network_config.proxies_single.http,
            single_https=network_config.proxies_single.https,
            pool=network_config.proxies_pool,
            rotate_every=network_config.rotate_every_requests,
        )

        # Set up throttler
        self.throttler = Throttler(
            min_delay_ms=throttling_config.min_delay_ms,
            max_delay_ms=throttling_config.max_delay_ms,
            max_retries=throttling_config.max_retries,
            backoff_base_sec=throttling_config.backoff_base_sec,
        )

        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            proxies = self.proxy_provider.get_proxies()
            self._client = httpx.Client(
                timeout=self.timeout,
                proxy=proxies.get("http://") if proxies else None,
                follow_redirects=True,
            )
        return self._client

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Make an HTTP request with retries and throttling.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            **kwargs: Additional arguments for httpx

        Returns:
            HTTP response

        Raises:
            NetworkError: If all retries fail
            RateLimitError: If rate limited and retries exhausted
        """
        last_error: Exception | None = None

        for attempt in range(self.throttler.max_retries + 1):
            try:
                # Apply throttling
                self.throttler.wait()

                # Make request
                client = self._get_client()
                response = client.request(method, url, **kwargs)

                # Check for rate limiting
                if response.status_code == 429:
                    if self.throttler.should_retry(attempt):
                        delay = self.throttler.get_backoff_delay(attempt)
                        time.sleep(delay)
                        continue
                    raise RateLimitError(f"Rate limited after {attempt + 1} attempts")

                # Raise for other errors
                response.raise_for_status()
                return response

            except httpx.HTTPStatusError as e:
                last_error = e
                if not self.throttler.should_retry(attempt):
                    break
                delay = self.throttler.get_backoff_delay(attempt)
                time.sleep(delay)

            except httpx.RequestError as e:
                last_error = e
                if not self.throttler.should_retry(attempt):
                    break
                delay = self.throttler.get_backoff_delay(attempt)
                time.sleep(delay)

        raise NetworkError(
            f"Request failed after {self.throttler.max_retries + 1} attempts: {last_error}"
        )

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        """Make a GET request."""
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        """Make a POST request."""
        return self.request("POST", url, **kwargs)

    def __enter__(self) -> "NetworkClient":
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()


def create_network_client(
    network_config: NetworkConfig,
    throttling_config: ThrottlingConfig,
) -> NetworkClient:
    """
    Create a configured network client.

    Args:
        network_config: Network configuration
        throttling_config: Throttling configuration

    Returns:
        Configured NetworkClient instance
    """
    return NetworkClient(network_config, throttling_config)
