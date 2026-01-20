"""
Pain statement extraction for painminer.

Detects and normalizes pain statements from Reddit content.
"""

import re
from datetime import datetime

from painminer.config import FiltersConfig
from painminer.models import PainItem, RawRedditComment, RawRedditPost, SourceType
from painminer.utils import generate_id, normalize_text


class ExtractionError(Exception):
    """Raised when extraction fails."""
    pass


class PainExtractor:
    """
    Extracts pain statements from Reddit content.

    Uses configurable include/exclude phrase matching and
    text normalization.
    """

    def __init__(self, filters_config: FiltersConfig) -> None:
        """
        Initialize pain extractor.

        Args:
            filters_config: Filters configuration
        """
        self.filters = filters_config

        # Compile include patterns (case-insensitive)
        self.include_patterns = [
            re.compile(re.escape(phrase), re.IGNORECASE)
            for phrase in filters_config.include_phrases
        ]

        # Compile exclude patterns (case-insensitive)
        self.exclude_patterns = [
            re.compile(re.escape(phrase), re.IGNORECASE)
            for phrase in filters_config.exclude_phrases
        ]

    def _contains_include_phrase(self, text: str) -> bool:
        """Check if text contains any include phrase."""
        if not self.include_patterns:
            return True  # No filter = include all

        for pattern in self.include_patterns:
            if pattern.search(text):
                return True
        return False

    def _contains_exclude_phrase(self, text: str) -> bool:
        """Check if text contains any exclude phrase."""
        for pattern in self.exclude_patterns:
            if pattern.search(text):
                return True
        return False

    def _extract_pain_sentences(self, text: str) -> list[str]:
        """
        Extract sentences containing pain indicators.

        Args:
            text: Input text

        Returns:
            List of pain-related sentences
        """
        if not text:
            return []

        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)

        pain_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()

            # Check minimum length
            if len(sentence) < self.filters.min_pain_length:
                continue

            # Check for include phrases
            if not self._contains_include_phrase(sentence):
                continue

            # Check for exclude phrases
            if self._contains_exclude_phrase(sentence):
                continue

            pain_sentences.append(sentence)

        return pain_sentences

    def extract_from_post(self, post: RawRedditPost) -> list[PainItem]:
        """
        Extract pain statements from a post.

        Args:
            post: Raw Reddit post

        Returns:
            List of extracted PainItems
        """
        items: list[PainItem] = []

        # Combine title and selftext
        full_text = f"{post.title}. {post.selftext}"

        # Check for exclude phrases first
        if self._contains_exclude_phrase(full_text):
            return []

        # Extract pain sentences
        pain_sentences = self._extract_pain_sentences(full_text)

        for i, sentence in enumerate(pain_sentences):
            # Normalize the text
            normalized = normalize_text(sentence)

            if len(normalized) < self.filters.min_pain_length:
                continue

            item_id = generate_id(post.id, "post", str(i))

            item = PainItem(
                id=item_id,
                subreddit=post.subreddit,
                source_type=SourceType.POST,
                post_id=post.id,
                score=post.score,
                created_utc=datetime.utcfromtimestamp(post.created_utc),
                text=normalized,
                url=post.url,
                raw_text=sentence,
            )
            items.append(item)

        return items

    def extract_from_comment(
        self,
        comment: RawRedditComment,
        post_url: str | None = None,
    ) -> list[PainItem]:
        """
        Extract pain statements from a comment.

        Args:
            comment: Raw Reddit comment
            post_url: Optional URL to parent post

        Returns:
            List of extracted PainItems
        """
        items: list[PainItem] = []

        # Check for exclude phrases first
        if self._contains_exclude_phrase(comment.body):
            return []

        # Extract pain sentences
        pain_sentences = self._extract_pain_sentences(comment.body)

        for i, sentence in enumerate(pain_sentences):
            # Normalize the text
            normalized = normalize_text(sentence)

            if len(normalized) < self.filters.min_pain_length:
                continue

            item_id = generate_id(comment.id, "comment", str(i))

            # Build comment URL
            comment_url = f"https://reddit.com{comment.permalink}"

            item = PainItem(
                id=item_id,
                subreddit=comment.subreddit,
                source_type=SourceType.COMMENT,
                post_id=comment.post_id,
                score=comment.score,
                created_utc=datetime.utcfromtimestamp(comment.created_utc),
                text=normalized,
                url=comment_url,
                raw_text=sentence,
            )
            items.append(item)

        return items

    def extract_all(
        self,
        posts: list[RawRedditPost],
        comments: list[RawRedditComment],
    ) -> list[PainItem]:
        """
        Extract pain statements from all posts and comments.

        Args:
            posts: List of raw Reddit posts
            comments: List of raw Reddit comments

        Returns:
            List of all extracted PainItems
        """
        items: list[PainItem] = []

        # Build post URL lookup
        post_urls = {post.id: post.url for post in posts}

        # Extract from posts
        for post in posts:
            post_items = self.extract_from_post(post)
            items.extend(post_items)

        # Extract from comments
        for comment in comments:
            post_url = post_urls.get(comment.post_id)
            comment_items = self.extract_from_comment(comment, post_url)
            items.extend(comment_items)

        return items


def create_extractor(filters_config: FiltersConfig) -> PainExtractor:
    """
    Create a configured pain extractor.

    Args:
        filters_config: Filters configuration

    Returns:
        Configured PainExtractor instance
    """
    return PainExtractor(filters_config)


def normalize_pain_text(text: str) -> str:
    """
    Normalize a pain statement text.

    This is a convenience function that applies full normalization.

    Args:
        text: Raw pain statement text

    Returns:
        Normalized text
    """
    return normalize_text(text)
