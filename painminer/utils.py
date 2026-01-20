"""
Utility functions for painminer.

Common helper functions used across modules.
"""

import hashlib
import re
import unicodedata
from datetime import datetime
from typing import Any


def normalize_text(text: str) -> str:
    """
    Normalize text for pain statement extraction.
    
    Performs:
    - Lowercasing
    - URL removal
    - Subreddit/user mention removal
    - Whitespace collapsing
    - Unicode normalization
    
    Args:
        text: Raw text to normalize
        
    Returns:
        Normalized text string
    """
    if not text:
        return ""
    
    # Unicode normalization
    text = unicodedata.normalize("NFKC", text)
    
    # Lowercase
    text = text.lower()
    
    # Remove URLs
    text = re.sub(
        r'https?://[^\s<>"{}|\\^`\[\]]+',
        '',
        text
    )
    
    # Remove subreddit mentions (r/subreddit)
    text = re.sub(r'\br/\w+', '', text)
    
    # Remove user mentions (u/username)
    text = re.sub(r'\bu/\w+', '', text)
    
    # Remove markdown links [text](url)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    
    # Remove markdown formatting
    text = re.sub(r'[*_~`#>]', '', text)
    
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def extract_sentences(text: str) -> list[str]:
    """
    Extract sentences from text.
    
    Args:
        text: Input text
        
    Returns:
        List of sentences
    """
    if not text:
        return []
    
    # Simple sentence splitting on common terminators
    # Handles: . ! ? and also handles abbreviations somewhat
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    # Filter out very short sentences
    return [s.strip() for s in sentences if len(s.strip()) > 5]


def generate_id(*parts: str) -> str:
    """
    Generate a deterministic ID from parts.
    
    Args:
        *parts: String parts to hash
        
    Returns:
        Short hash string
    """
    combined = "|".join(str(p) for p in parts)
    return hashlib.sha256(combined.encode()).hexdigest()[:12]


def timestamp_to_datetime(timestamp: float) -> datetime:
    """
    Convert Unix timestamp to datetime.
    
    Args:
        timestamp: Unix timestamp (seconds since epoch)
        
    Returns:
        datetime object
    """
    return datetime.utcfromtimestamp(timestamp)


def datetime_to_timestamp(dt: datetime) -> float:
    """
    Convert datetime to Unix timestamp.
    
    Args:
        dt: datetime object
        
    Returns:
        Unix timestamp
    """
    return dt.timestamp()


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add when truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def to_pascal_case(text: str) -> str:
    """
    Convert text to PascalCase.
    
    Args:
        text: Input text
        
    Returns:
        PascalCase string
    """
    # Remove non-alphanumeric characters
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    
    # Split into words
    words = text.split()
    
    # Capitalize each word
    return ''.join(word.capitalize() for word in words)


def extract_keywords(text: str, min_length: int = 3) -> list[str]:
    """
    Extract keywords from text.
    
    Args:
        text: Input text
        min_length: Minimum keyword length
        
    Returns:
        List of keywords
    """
    # Normalize
    text = normalize_text(text)
    
    # Common English stop words
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
        'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these',
        'those', 'it', 'its', "it's", 'i', 'me', 'my', 'you', 'your', 'we',
        'our', 'they', 'their', 'what', 'which', 'who', 'when', 'where',
        'why', 'how', 'all', 'each', 'every', 'both', 'few', 'more', 'most',
        'some', 'any', 'no', 'not', 'only', 'same', 'so', 'than', 'too',
        'very', 'just', 'also', 'now', 'here', 'there', 'then', 'if', 'else',
        'about', 'into', 'through', 'during', 'before', 'after', 'above',
        'below', 'up', 'down', 'out', 'off', 'over', 'under', 'again',
        'further', 'once', 'such', 'like', 'get', 'got', 'really', 'even',
        'much', 'many', 'one', 'two', 'thing', 'things', 'way', 'want',
        'know', 'think', 'make', 'time', 'go', 'going', 'been', 'being',
        'dont', "don't", 'doesnt', "doesn't", 'didnt', "didn't", 'cant',
        "can't", 'wont', "won't", 'im', "i'm", 'ive', "i've", 'id', "i'd",
    }
    
    # Extract words
    words = re.findall(r'\b[a-z]+\b', text)
    
    # Filter
    keywords = [
        w for w in words
        if len(w) >= min_length and w not in stop_words
    ]
    
    return keywords


def safe_filename(text: str, max_length: int = 50) -> str:
    """
    Convert text to a safe filename.
    
    Args:
        text: Input text
        max_length: Maximum filename length
        
    Returns:
        Safe filename string
    """
    # Remove or replace unsafe characters
    safe = re.sub(r'[^\w\s-]', '', text)
    safe = re.sub(r'\s+', '_', safe)
    safe = safe.strip('_')
    
    if len(safe) > max_length:
        safe = safe[:max_length]
    
    return safe or "unnamed"


def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable form.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Human-readable duration string
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def chunk_list(items: list[Any], chunk_size: int) -> list[list[Any]]:
    """
    Split a list into chunks.
    
    Args:
        items: List to split
        chunk_size: Size of each chunk
        
    Returns:
        List of chunks
    """
    return [
        items[i:i + chunk_size]
        for i in range(0, len(items), chunk_size)
    ]
