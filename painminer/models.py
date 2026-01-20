"""
Data models for painminer.

All core data structures used throughout the pipeline.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class SourceType(str, Enum):
    """Type of Reddit content source."""
    POST = "post"
    COMMENT = "comment"


class MVPComplexity(str, Enum):
    """Complexity rating for MVP."""
    XS = "XS"  # Extra small - 1 screen, 1 action
    S = "S"   # Small - 1-2 screens, 1-2 actions
    M = "M"   # Medium - 2-3 screens, 2-3 actions


@dataclass
class PainItem:
    """
    A single pain statement extracted from Reddit.

    Attributes:
        id: Unique identifier for this pain item
        subreddit: Name of the subreddit
        source_type: Whether from post or comment
        post_id: Reddit post ID
        score: Upvote score
        created_utc: Creation timestamp
        text: Normalized pain statement text
        url: Direct URL to the content
        raw_text: Original text before normalization
    """
    id: str
    subreddit: str
    source_type: SourceType
    post_id: str
    score: int
    created_utc: datetime
    text: str
    url: str
    raw_text: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "subreddit": self.subreddit,
            "source_type": self.source_type.value,
            "post_id": self.post_id,
            "score": self.score,
            "created_utc": self.created_utc.isoformat(),
            "text": self.text,
            "url": self.url,
            "raw_text": self.raw_text,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PainItem":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            subreddit=data["subreddit"],
            source_type=SourceType(data["source_type"]),
            post_id=data["post_id"],
            score=data["score"],
            created_utc=datetime.fromisoformat(data["created_utc"]),
            text=data["text"],
            url=data["url"],
            raw_text=data.get("raw_text", ""),
        )


@dataclass
class Cluster:
    """
    A cluster of related pain statements.

    Attributes:
        cluster_id: Unique cluster identifier
        label: Short descriptive label
        count: Number of items in cluster
        example_texts: Representative example texts
        items: All PainItems in this cluster
        avg_score: Average score of items
        total_score: Sum of all scores
    """
    cluster_id: str
    label: str
    count: int
    example_texts: list[str]
    items: list[PainItem]
    avg_score: float = 0.0
    total_score: int = 0

    def __post_init__(self) -> None:
        """Calculate derived fields."""
        if self.items:
            self.total_score = sum(item.score for item in self.items)
            self.avg_score = self.total_score / len(self.items)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "cluster_id": self.cluster_id,
            "label": self.label,
            "count": self.count,
            "example_texts": self.example_texts,
            "items": [item.to_dict() for item in self.items],
            "avg_score": self.avg_score,
            "total_score": self.total_score,
        }


@dataclass
class SolutionShape:
    """
    Inferred solution shape for a cluster.

    Attributes:
        shape_type: Type of solution (reminder, checklist, timer, etc.)
        keywords: Keywords that led to this shape
        requires_social: Whether social features are needed
        requires_marketplace: Whether marketplace features are needed
        requires_realtime: Whether realtime sync is needed
        requires_ai: Whether AI is core to value
        estimated_screens: Estimated number of screens
        estimated_actions: Estimated user actions
        solvable_locally: Whether solvable with local-only data
    """
    shape_type: str
    keywords: list[str] = field(default_factory=list)
    requires_social: bool = False
    requires_marketplace: bool = False
    requires_realtime: bool = False
    requires_ai: bool = False
    estimated_screens: int = 1
    estimated_actions: int = 1
    solvable_locally: bool = True

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "shape_type": self.shape_type,
            "keywords": self.keywords,
            "requires_social": self.requires_social,
            "requires_marketplace": self.requires_marketplace,
            "requires_realtime": self.requires_realtime,
            "requires_ai": self.requires_ai,
            "estimated_screens": self.estimated_screens,
            "estimated_actions": self.estimated_actions,
            "solvable_locally": self.solvable_locally,
        }


@dataclass
class AppIdea:
    """
    Generated iOS app idea from a cluster.

    Attributes:
        idea_name: PascalCase app name
        problem_statement: What problem this solves
        target_user: Who would use this
        core_functions: 1-3 bullet point functions
        screens: 1-3 named screens
        local_data: What data is stored locally
        minimal_notifications: Optional notification ideas
        mvp_complexity: XS/S/M rating
        reddit_evidence: Evidence from Reddit
        cluster: Source cluster
    """
    idea_name: str
    problem_statement: str
    target_user: str
    core_functions: list[str]
    screens: list[str]
    local_data: list[str]
    minimal_notifications: list[str]
    mvp_complexity: MVPComplexity
    reddit_evidence: dict
    cluster: Cluster | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        result = {
            "idea_name": self.idea_name,
            "problem_statement": self.problem_statement,
            "target_user": self.target_user,
            "core_functions": self.core_functions,
            "screens": self.screens,
            "local_data": self.local_data,
            "minimal_notifications": self.minimal_notifications,
            "mvp_complexity": self.mvp_complexity.value,
            "reddit_evidence": self.reddit_evidence,
        }
        if self.cluster:
            result["cluster"] = self.cluster.to_dict()
        return result


@dataclass
class RawRedditPost:
    """
    Raw Reddit post data before processing.

    Attributes:
        id: Reddit post ID
        subreddit: Subreddit name
        title: Post title
        selftext: Post body text
        score: Upvote score
        created_utc: Creation timestamp
        url: URL to post
        num_comments: Number of comments
    """
    id: str
    subreddit: str
    title: str
    selftext: str
    score: int
    created_utc: float
    url: str
    num_comments: int

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "subreddit": self.subreddit,
            "title": self.title,
            "selftext": self.selftext,
            "score": self.score,
            "created_utc": self.created_utc,
            "url": self.url,
            "num_comments": self.num_comments,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RawRedditPost":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            subreddit=data["subreddit"],
            title=data["title"],
            selftext=data["selftext"],
            score=data["score"],
            created_utc=data["created_utc"],
            url=data["url"],
            num_comments=data["num_comments"],
        )


@dataclass
class RawRedditComment:
    """
    Raw Reddit comment data before processing.

    Attributes:
        id: Reddit comment ID
        post_id: Parent post ID
        subreddit: Subreddit name
        body: Comment text
        score: Upvote score
        created_utc: Creation timestamp
        permalink: URL path to comment
    """
    id: str
    post_id: str
    subreddit: str
    body: str
    score: int
    created_utc: float
    permalink: str

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "post_id": self.post_id,
            "subreddit": self.subreddit,
            "body": self.body,
            "score": self.score,
            "created_utc": self.created_utc,
            "permalink": self.permalink,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RawRedditComment":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            post_id=data["post_id"],
            subreddit=data["subreddit"],
            body=data["body"],
            score=data["score"],
            created_utc=data["created_utc"],
            permalink=data["permalink"],
        )
