"""
Clustering module for painminer.

Groups pain statements into clusters using different methods.
"""

import hashlib
import math
import re
from collections import defaultdict
from typing import Callable

from painminer.config import ClusteringConfig
from painminer.models import Cluster, PainItem
from painminer.utils import extract_keywords, to_pascal_case


class ClusteringError(Exception):
    """Raised when clustering fails."""
    pass


def _generate_cluster_label(items: list[PainItem], max_words: int = 4) -> str:
    """
    Generate a short label for a cluster based on common keywords.
    
    Args:
        items: Pain items in the cluster
        max_words: Maximum words in label
        
    Returns:
        Cluster label string
    """
    # Collect all keywords
    keyword_counts: dict[str, int] = defaultdict(int)
    
    for item in items:
        keywords = extract_keywords(item.text)
        for kw in keywords:
            keyword_counts[kw] += 1
    
    # Get top keywords
    sorted_keywords = sorted(
        keyword_counts.items(),
        key=lambda x: x[1],
        reverse=True,
    )
    
    top_keywords = [kw for kw, _ in sorted_keywords[:max_words]]
    
    if not top_keywords:
        return "MiscellaneousIssues"
    
    # Create PascalCase label
    label = to_pascal_case(" ".join(top_keywords))
    return label if label else "MiscellaneousIssues"


def _simple_hash_key(text: str) -> str:
    """
    Generate a simple hash key for clustering.
    
    Extracts verb-like patterns and object keywords for grouping.
    
    Args:
        text: Normalized pain statement text
        
    Returns:
        Hash key string
    """
    # Common pain-related verbs/actions
    action_patterns = [
        r'\b(struggle|struggling)\b',
        r'\b(forget|forgetting|forgot)\b',
        r'\b(wish|wishing)\b',
        r'\b(need|needing)\b',
        r'\b(want|wanting)\b',
        r'\b(cant|cannot|can\'t)\b',
        r'\b(hard|difficult)\b',
        r'\b(problem|issue)\b',
        r'\b(help|helping)\b',
        r'\b(track|tracking)\b',
        r'\b(remember|remembering)\b',
        r'\b(organize|organizing)\b',
        r'\b(manage|managing)\b',
        r'\b(focus|focusing)\b',
        r'\b(procrastinate|procrastinating)\b',
        r'\b(overwhelm|overwhelming|overwhelmed)\b',
        r'\b(anxiety|anxious)\b',
        r'\b(motivation|motivate)\b',
        r'\b(schedule|scheduling)\b',
        r'\b(routine|routines)\b',
        r'\b(habit|habits)\b',
        r'\b(task|tasks)\b',
        r'\b(time|timing)\b',
        r'\b(sleep|sleeping)\b',
        r'\b(medication|meds)\b',
        r'\b(reminder|reminders)\b',
        r'\b(list|lists)\b',
        r'\b(note|notes)\b',
        r'\b(app|apps)\b',
    ]
    
    # Find matching patterns
    matches = []
    for pattern in action_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            # Extract the base word
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                matches.append(match.group(1).lower())
    
    # Sort for determinism
    matches = sorted(set(matches))
    
    if not matches:
        # Fall back to first few keywords
        keywords = extract_keywords(text)[:3]
        matches = sorted(keywords)
    
    # Create key
    key = "_".join(matches[:3]) if matches else "misc"
    return key


def cluster_simple_hash(
    items: list[PainItem],
    config: ClusteringConfig,
) -> list[Cluster]:
    """
    Cluster pain items using simple hash-based grouping.
    
    Groups items by extracted action/object patterns.
    Fully deterministic.
    
    Args:
        items: Pain items to cluster
        config: Clustering configuration
        
    Returns:
        List of clusters
    """
    if not items:
        return []
    
    # Group by hash key
    groups: dict[str, list[PainItem]] = defaultdict(list)
    
    for item in items:
        key = _simple_hash_key(item.text)
        groups[key].append(item)
    
    # Convert to clusters
    clusters: list[Cluster] = []
    
    for i, (key, group_items) in enumerate(sorted(groups.items())):
        # Generate label
        label = _generate_cluster_label(group_items)
        
        # Get example texts
        sorted_items = sorted(group_items, key=lambda x: x.score, reverse=True)
        example_texts = [item.text for item in sorted_items[:5]]
        
        cluster = Cluster(
            cluster_id=f"hash_{i:03d}",
            label=label,
            count=len(group_items),
            example_texts=example_texts,
            items=sorted_items,
        )
        clusters.append(cluster)
    
    # Sort by count descending
    clusters.sort(key=lambda c: c.count, reverse=True)
    
    return clusters


def cluster_tfidf_kmeans(
    items: list[PainItem],
    config: ClusteringConfig,
) -> list[Cluster]:
    """
    Cluster pain items using TF-IDF + KMeans.
    
    Uses scikit-learn for vectorization and clustering.
    Deterministic with fixed random_state.
    
    Args:
        items: Pain items to cluster
        config: Clustering configuration
        
    Returns:
        List of clusters
    """
    if not items:
        return []
    
    # Import sklearn here to make it optional
    try:
        from sklearn.cluster import KMeans
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics import silhouette_score
    except ImportError:
        raise ClusteringError(
            "scikit-learn is required for tfidf_kmeans clustering. "
            "Install with: pip install scikit-learn"
        )
    
    # Get texts
    texts = [item.text for item in items]
    
    # Vectorize with TF-IDF
    vectorizer = TfidfVectorizer(
        max_features=1000,
        stop_words='english',
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.95,
    )
    
    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
    except ValueError:
        # Not enough documents for min_df=2
        vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.95,
        )
        tfidf_matrix = vectorizer.fit_transform(texts)
    
    # Determine optimal k
    n_samples = len(items)
    k_min = min(config.k_min, n_samples)
    k_max = min(config.k_max, n_samples)
    
    if k_min >= n_samples:
        k_min = max(2, n_samples // 2)
    if k_max >= n_samples:
        k_max = max(k_min, n_samples // 2)
    
    # Simple heuristic: sqrt(n) bounded by k_min and k_max
    k_heuristic = int(math.sqrt(n_samples))
    k_optimal = max(k_min, min(k_max, k_heuristic))
    
    # If we have enough samples, try to find better k using silhouette
    if n_samples >= 20 and k_max > k_min:
        best_score = -1
        best_k = k_optimal
        
        for k in range(k_min, min(k_max + 1, k_min + 5)):  # Limit search
            if k >= n_samples:
                break
            
            kmeans = KMeans(
                n_clusters=k,
                random_state=config.random_state,
                n_init=10,
                max_iter=300,
            )
            labels = kmeans.fit_predict(tfidf_matrix)
            
            # Check if we have more than one cluster
            if len(set(labels)) > 1:
                try:
                    score = silhouette_score(tfidf_matrix, labels)
                    if score > best_score:
                        best_score = score
                        best_k = k
                except ValueError:
                    pass
        
        k_optimal = best_k
    
    # Final clustering
    kmeans = KMeans(
        n_clusters=k_optimal,
        random_state=config.random_state,
        n_init=10,
        max_iter=300,
    )
    labels = kmeans.fit_predict(tfidf_matrix)
    
    # Group items by cluster
    groups: dict[int, list[PainItem]] = defaultdict(list)
    for item, label in zip(items, labels):
        groups[label].append(item)
    
    # Convert to clusters
    clusters: list[Cluster] = []
    
    for label_id in sorted(groups.keys()):
        group_items = groups[label_id]
        
        # Generate label
        cluster_label = _generate_cluster_label(group_items)
        
        # Get example texts (sorted by score)
        sorted_items = sorted(group_items, key=lambda x: x.score, reverse=True)
        example_texts = [item.text for item in sorted_items[:5]]
        
        cluster = Cluster(
            cluster_id=f"km_{label_id:03d}",
            label=cluster_label,
            count=len(group_items),
            example_texts=example_texts,
            items=sorted_items,
        )
        clusters.append(cluster)
    
    # Sort by count descending
    clusters.sort(key=lambda c: c.count, reverse=True)
    
    return clusters


def cluster_pain_items(
    items: list[PainItem],
    config: ClusteringConfig,
) -> list[Cluster]:
    """
    Cluster pain items using configured method.
    
    Args:
        items: Pain items to cluster
        config: Clustering configuration
        
    Returns:
        List of clusters
    """
    if config.method == "simple_hash":
        return cluster_simple_hash(items, config)
    elif config.method == "tfidf_kmeans":
        return cluster_tfidf_kmeans(items, config)
    else:
        raise ClusteringError(f"Unknown clustering method: {config.method}")


class Clusterer:
    """
    Pain statement clusterer.
    
    Provides a class-based interface for clustering.
    """
    
    def __init__(self, config: ClusteringConfig) -> None:
        """
        Initialize clusterer.
        
        Args:
            config: Clustering configuration
        """
        self.config = config
    
    def cluster(self, items: list[PainItem]) -> list[Cluster]:
        """
        Cluster pain items.
        
        Args:
            items: Pain items to cluster
            
        Returns:
            List of clusters
        """
        return cluster_pain_items(items, self.config)


def create_clusterer(config: ClusteringConfig) -> Clusterer:
    """
    Create a configured clusterer.
    
    Args:
        config: Clustering configuration
        
    Returns:
        Configured Clusterer instance
    """
    return Clusterer(config)
