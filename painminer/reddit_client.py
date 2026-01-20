"""
Reddit API client for painminer.

Uses PRAW to fetch posts and comments from specified subreddits.
"""

import logging
import random
import time
from datetime import datetime, timedelta

import praw
import requests
from praw.models import MoreComments

from painminer.cache import RedditCache
from painminer.config import (
    NetworkConfig,
    PainminerConfig,
    RedditConfig,
    SubredditConfig,
    ThrottlingConfig,
)
from painminer.models import RawRedditComment, RawRedditPost

logger = logging.getLogger(__name__)


class RedditClientError(Exception):
    """Raised when Reddit API operations fail."""
    pass


class RedditClient:
    """
    Reddit API client using PRAW.

    Fetches posts and comments from subreddits with caching
    and rate limiting support.
    """

    def __init__(
        self,
        reddit_config: RedditConfig,
        throttling_config: ThrottlingConfig,
        network_config: NetworkConfig | None = None,
        cache: RedditCache | None = None,
        use_cache: bool = True,
    ) -> None:
        """
        Initialize Reddit client.

        Args:
            reddit_config: Reddit API credentials
            throttling_config: Rate limiting configuration
            network_config: Network and proxy configuration
            cache: Optional cache instance
            use_cache: Whether to use caching
        """
        self.reddit_config = reddit_config
        self.throttling_config = throttling_config
        self.network_config = network_config or NetworkConfig()
        self.cache = cache or RedditCache()
        self.use_cache = use_cache

        self._reddit: praw.Reddit | None = None
        self._last_request_time: float = 0
        self._request_count: int = 0
        self._current_proxy_index: int = 0

    def _get_proxies(self) -> dict[str, str] | None:
        """
        Get proxy configuration for current request.

        Returns:
            Dictionary with proxy settings or None if proxies disabled
        """
        if not self.network_config.proxies_enabled:
            return None

        if self.network_config.proxies_mode == "single":
            proxies = {}
            if self.network_config.proxies_single.http:
                proxies["http"] = self.network_config.proxies_single.http
            if self.network_config.proxies_single.https:
                proxies["https"] = self.network_config.proxies_single.https
            return proxies if proxies else None

        elif self.network_config.proxies_mode == "pool":
            pool = self.network_config.proxies_pool
            if not pool:
                return None

            # Get current proxy from pool
            proxy_url = pool[self._current_proxy_index % len(pool)]
            return {"http": proxy_url, "https": proxy_url}

        return None

    def _rotate_proxy_if_needed(self) -> None:
        """Rotate to next proxy in pool if rotation threshold reached."""
        if (
            self.network_config.proxies_enabled
            and self.network_config.proxies_mode == "pool"
            and self.network_config.proxies_pool
        ):
            self._request_count += 1
            if self._request_count >= self.network_config.rotate_every_requests:
                self._request_count = 0
                self._current_proxy_index += 1
                pool_size = len(self.network_config.proxies_pool)
                logger.debug(
                    f"Rotating proxy to index {self._current_proxy_index % pool_size}"
                )
                # Reset Reddit instance to use new proxy
                self._reddit = None

    def _create_session(self) -> requests.Session:
        """
        Create a requests session with proxy configuration.

        Returns:
            Configured requests.Session instance
        """
        session = requests.Session()

        proxies = self._get_proxies()
        if proxies:
            session.proxies.update(proxies)
            logger.info(f"Using proxy: {list(proxies.values())[0]}")

        # Store timeout in session for later use (timeout is per-request, not session attribute)
        session.timeout = self.network_config.timeout_sec  # type: ignore[attr-defined]

        return session

    def _get_reddit(self) -> praw.Reddit:
        """Get or create PRAW Reddit instance."""
        if self._reddit is None:
            try:
                # Create session with proxy configuration
                requestor_kwargs = {}
                session = self._create_session()
                requestor_kwargs["session"] = session

                self._reddit = praw.Reddit(
                    client_id=self.reddit_config.client_id,
                    client_secret=self.reddit_config.client_secret,
                    username=self.reddit_config.username,
                    password=self.reddit_config.password,
                    user_agent=self.reddit_config.user_agent,
                    requestor_kwargs=requestor_kwargs,
                )
                # Verify authentication
                _ = self._reddit.user.me()
                logger.info("Successfully authenticated with Reddit API")
            except Exception as e:
                raise RedditClientError(f"Failed to authenticate with Reddit: {e}") from e

        return self._reddit

    def _throttle(self) -> None:
        """Apply rate limiting delay and handle proxy rotation."""
        now = time.time()

        # Random delay between min and max
        delay_ms = random.randint(
            self.throttling_config.min_delay_ms,
            self.throttling_config.max_delay_ms,
        )
        delay_sec = delay_ms / 1000.0

        # Wait if needed
        elapsed = now - self._last_request_time
        if elapsed < delay_sec:
            time.sleep(delay_sec - elapsed)

        self._last_request_time = time.time()

        # Check if we need to rotate proxy
        self._rotate_proxy_if_needed()

    def _retry_with_backoff(self, func, *args, **kwargs):  # type: ignore[no-untyped-def]
        """Execute function with exponential backoff on failure."""
        last_error = None

        for attempt in range(self.throttling_config.max_retries + 1):
            try:
                self._throttle()
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.throttling_config.max_retries:
                    delay = self.throttling_config.backoff_base_sec * (2 ** attempt)
                    jitter = random.uniform(0, 0.5 * delay)
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}), "
                        f"retrying in {delay + jitter:.1f}s: {e}"
                    )
                    time.sleep(delay + jitter)

        raise RedditClientError(
            f"Request failed after {self.throttling_config.max_retries + 1} attempts: {last_error}"
        )

    def _get_time_filter(self, period_days: int) -> str:
        """
        Get PRAW time filter for period.

        Args:
            period_days: Number of days

        Returns:
            PRAW time filter string
        """
        if period_days <= 1:
            return "day"
        elif period_days <= 7:
            return "week"
        elif period_days <= 30:
            return "month"
        elif period_days <= 365:
            return "year"
        else:
            return "all"

    def fetch_posts(
        self,
        subreddit_config: SubredditConfig,
    ) -> list[RawRedditPost]:
        """
        Fetch posts from a subreddit.

        Args:
            subreddit_config: Subreddit configuration

        Returns:
            List of raw Reddit posts
        """
        subreddit_name = subreddit_config.name
        period_days = subreddit_config.period_days
        min_upvotes = subreddit_config.min_upvotes
        max_posts = subreddit_config.max_posts

        # Check cache first
        if self.use_cache:
            cached = self.cache.get_posts(
                subreddit_name,
                period_days,
                min_upvotes,
                max_posts,
            )
            if cached is not None:
                logger.info(
                    f"Using cached posts for r/{subreddit_name} "
                    f"({len(cached)} posts)"
                )
                return cached

        logger.info(f"Fetching posts from r/{subreddit_name}...")

        reddit = self._get_reddit()
        subreddit = reddit.subreddit(subreddit_name)

        # Calculate cutoff time
        cutoff_time = datetime.utcnow() - timedelta(days=period_days)
        cutoff_timestamp = cutoff_time.timestamp()

        # Get time filter
        time_filter = self._get_time_filter(period_days)

        posts: list[RawRedditPost] = []

        # Fetch posts using top filter
        def fetch_batch():  # type: ignore[no-untyped-def]
            return subreddit.top(time_filter=time_filter, limit=max_posts * 2)

        try:
            submissions = self._retry_with_backoff(fetch_batch)

            for submission in submissions:  # type: ignore[union-attr]
                # Check time filter
                if submission.created_utc < cutoff_timestamp:
                    continue

                # Check upvotes
                if submission.score < min_upvotes:
                    continue

                # Create post object
                post = RawRedditPost(
                    id=submission.id,
                    subreddit=subreddit_name,
                    title=submission.title,
                    selftext=submission.selftext or "",
                    score=submission.score,
                    created_utc=submission.created_utc,
                    url=f"https://reddit.com{submission.permalink}",
                    num_comments=submission.num_comments,
                )
                posts.append(post)

                if len(posts) >= max_posts:
                    break

                # Apply throttling between iterations
                self._throttle()

        except Exception as e:
            raise RedditClientError(f"Failed to fetch posts from r/{subreddit_name}: {e}") from e

        logger.info(f"Fetched {len(posts)} posts from r/{subreddit_name}")

        # Cache results
        if self.use_cache:
            self.cache.set_posts(
                subreddit_name,
                period_days,
                min_upvotes,
                max_posts,
                posts,
            )

        return posts

    def fetch_comments(
        self,
        post: RawRedditPost,
        max_comments: int,
    ) -> list[RawRedditComment]:
        """
        Fetch top comments for a post.

        Args:
            post: Reddit post
            max_comments: Maximum comments to fetch

        Returns:
            List of raw Reddit comments
        """
        # Check cache first
        if self.use_cache:
            cached = self.cache.get_comments(post.id, max_comments)
            if cached is not None:
                logger.debug(f"Using cached comments for post {post.id}")
                return cached

        logger.debug(f"Fetching comments for post {post.id}...")

        reddit = self._get_reddit()

        comments: list[RawRedditComment] = []

        def fetch_submission():  # type: ignore[no-untyped-def]
            return reddit.submission(id=post.id)

        try:
            submission = self._retry_with_backoff(fetch_submission)

            # Sort by score (best)
            submission.comment_sort = "best"  # type: ignore[attr-defined]

            # Replace MoreComments with actual comments (limited)
            submission.comments.replace_more(limit=0)  # type: ignore[attr-defined]

            # Get top-level comments sorted by score
            all_comments = list(submission.comments)  # type: ignore[attr-defined]
            all_comments.sort(key=lambda c: c.score if hasattr(c, 'score') else 0, reverse=True)

            for comment in all_comments[:max_comments]:
                if isinstance(comment, MoreComments):
                    continue

                raw_comment = RawRedditComment(
                    id=comment.id,
                    post_id=post.id,
                    subreddit=post.subreddit,
                    body=comment.body or "",
                    score=comment.score,
                    created_utc=comment.created_utc,
                    permalink=comment.permalink,
                )
                comments.append(raw_comment)

        except Exception as e:
            logger.warning(f"Failed to fetch comments for post {post.id}: {e}")
            return []

        # Cache results
        if self.use_cache:
            self.cache.set_comments(post.id, max_comments, comments)

        return comments

    def fetch_all(
        self,
        config: PainminerConfig,
    ) -> tuple[list[RawRedditPost], list[RawRedditComment]]:
        """
        Fetch all posts and comments for configured subreddits.

        Args:
            config: Painminer configuration

        Returns:
            Tuple of (posts, comments)
        """
        all_posts: list[RawRedditPost] = []
        all_comments: list[RawRedditComment] = []

        for subreddit_config in config.subreddits:
            # Fetch posts
            posts = self.fetch_posts(subreddit_config)
            all_posts.extend(posts)

            # Fetch comments for each post
            for post in posts:
                comments = self.fetch_comments(
                    post,
                    subreddit_config.max_comments_per_post,
                )
                all_comments.extend(comments)

        logger.info(
            f"Total fetched: {len(all_posts)} posts, {len(all_comments)} comments"
        )

        return all_posts, all_comments


def create_reddit_client(
    config: PainminerConfig,
    use_cache: bool = True,
) -> RedditClient:
    """
    Create a configured Reddit client.

    Args:
        config: Painminer configuration
        use_cache: Whether to use caching

    Returns:
        Configured RedditClient instance
    """
    cache = RedditCache() if use_cache else None

    return RedditClient(
        reddit_config=config.reddit,
        throttling_config=config.throttling,
        network_config=config.network,
        cache=cache,
        use_cache=use_cache,
    )
