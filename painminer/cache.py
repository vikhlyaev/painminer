"""
File-based caching for painminer.

Caches Reddit API responses to avoid repeated fetches.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from painminer.models import RawRedditComment, RawRedditPost


class CacheError(Exception):
    """Raised when cache operations fail."""
    pass


@dataclass
class CacheEntry:
    """
    A single cache entry with metadata.

    Attributes:
        key: Cache key
        data: Cached data
        created_at: When the entry was created
        expires_at: Optional expiration time
    """
    key: str
    data: Any
    created_at: datetime
    expires_at: datetime | None = None

    def is_expired(self) -> bool:
        """Check if the entry has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "key": self.key,
            "data": self.data,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CacheEntry":
        """Create from dictionary."""
        return cls(
            key=data["key"],
            data=data["data"],
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=(
                datetime.fromisoformat(data["expires_at"])
                if data.get("expires_at")
                else None
            ),
        )


class FileCache:
    """
    File-based cache for storing Reddit data.

    Stores data as JSON files in a cache directory.
    """

    def __init__(self, cache_dir: str | Path = "cache") -> None:
        """
        Initialize file cache.

        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = Path(cache_dir)
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        """Ensure cache directory exists."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, key: str) -> Path:
        """
        Get file path for a cache key.

        Args:
            key: Cache key

        Returns:
            Path to cache file
        """
        # Hash the key for safe filename
        key_hash = hashlib.sha256(key.encode()).hexdigest()[:16]
        # Also include readable prefix
        safe_prefix = "".join(c if c.isalnum() else "_" for c in key[:30])
        filename = f"{safe_prefix}_{key_hash}.json"
        return self.cache_dir / filename

    def get(self, key: str) -> Any | None:
        """
        Get cached data for a key.

        Args:
            key: Cache key

        Returns:
            Cached data or None if not found/expired
        """
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, encoding="utf-8") as f:
                entry_data = json.load(f)

            entry = CacheEntry.from_dict(entry_data)

            if entry.is_expired():
                # Remove expired entry
                cache_path.unlink(missing_ok=True)
                return None

            return entry.data

        except (json.JSONDecodeError, KeyError, OSError):
            # Invalid cache file, remove it
            cache_path.unlink(missing_ok=True)
            return None

    def set(
        self,
        key: str,
        data: Any,
        expires_at: datetime | None = None,
    ) -> None:
        """
        Store data in cache.

        Args:
            key: Cache key
            data: Data to cache
            expires_at: Optional expiration time
        """
        self._ensure_dir()

        entry = CacheEntry(
            key=key,
            data=data,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
        )

        cache_path = self._get_cache_path(key)

        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(entry.to_dict(), f, indent=2, ensure_ascii=False)
        except OSError as e:
            raise CacheError(f"Failed to write cache file: {e}") from e

    def delete(self, key: str) -> bool:
        """
        Delete a cache entry.

        Args:
            key: Cache key

        Returns:
            True if entry was deleted
        """
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            cache_path.unlink()
            return True
        return False

    def clear(self) -> int:
        """
        Clear all cache entries.

        Returns:
            Number of entries deleted
        """
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
                count += 1
            except OSError:
                pass
        return count

    def exists(self, key: str) -> bool:
        """
        Check if a cache entry exists and is valid.

        Args:
            key: Cache key

        Returns:
            True if entry exists and is not expired
        """
        return self.get(key) is not None

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        total_size = 0
        file_count = 0

        for cache_file in self.cache_dir.glob("*.json"):
            file_count += 1
            total_size += cache_file.stat().st_size

        return {
            "directory": str(self.cache_dir),
            "file_count": file_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
        }


class RedditCache:
    """
    Specialized cache for Reddit data.

    Provides methods for caching posts and comments with
    subreddit and time-based keys.
    """

    def __init__(self, cache_dir: str | Path = "cache") -> None:
        """
        Initialize Reddit cache.

        Args:
            cache_dir: Directory to store cache files
        """
        self.cache = FileCache(cache_dir)

    def _make_posts_key(
        self,
        subreddit: str,
        period_days: int,
        min_upvotes: int,
        max_posts: int,
    ) -> str:
        """Generate cache key for posts query."""
        return f"posts_{subreddit}_{period_days}d_{min_upvotes}up_{max_posts}max"

    def _make_comments_key(
        self,
        post_id: str,
        max_comments: int,
    ) -> str:
        """Generate cache key for comments query."""
        return f"comments_{post_id}_{max_comments}max"

    def get_posts(
        self,
        subreddit: str,
        period_days: int,
        min_upvotes: int,
        max_posts: int,
    ) -> list[RawRedditPost] | None:
        """
        Get cached posts for a subreddit query.

        Args:
            subreddit: Subreddit name
            period_days: Time period in days
            min_upvotes: Minimum upvotes filter
            max_posts: Maximum posts to return

        Returns:
            List of cached posts or None if not cached
        """
        key = self._make_posts_key(subreddit, period_days, min_upvotes, max_posts)
        data = self.cache.get(key)

        if data is None:
            return None

        return [RawRedditPost.from_dict(p) for p in data]

    def set_posts(
        self,
        subreddit: str,
        period_days: int,
        min_upvotes: int,
        max_posts: int,
        posts: list[RawRedditPost],
    ) -> None:
        """
        Cache posts for a subreddit query.

        Args:
            subreddit: Subreddit name
            period_days: Time period in days
            min_upvotes: Minimum upvotes filter
            max_posts: Maximum posts to return
            posts: Posts to cache
        """
        key = self._make_posts_key(subreddit, period_days, min_upvotes, max_posts)
        data = [p.to_dict() for p in posts]
        self.cache.set(key, data)

    def get_comments(
        self,
        post_id: str,
        max_comments: int,
    ) -> list[RawRedditComment] | None:
        """
        Get cached comments for a post.

        Args:
            post_id: Reddit post ID
            max_comments: Maximum comments to return

        Returns:
            List of cached comments or None if not cached
        """
        key = self._make_comments_key(post_id, max_comments)
        data = self.cache.get(key)

        if data is None:
            return None

        return [RawRedditComment.from_dict(c) for c in data]

    def set_comments(
        self,
        post_id: str,
        max_comments: int,
        comments: list[RawRedditComment],
    ) -> None:
        """
        Cache comments for a post.

        Args:
            post_id: Reddit post ID
            max_comments: Maximum comments to return
            comments: Comments to cache
        """
        key = self._make_comments_key(post_id, max_comments)
        data = [c.to_dict() for c in comments]
        self.cache.set(key, data)

    def clear(self) -> int:
        """Clear all cached data."""
        return self.cache.clear()

    def get_stats(self) -> dict:
        """Get cache statistics."""
        return self.cache.get_stats()
