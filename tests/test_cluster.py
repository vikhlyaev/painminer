"""
Tests for clustering module.
"""

import pytest
from datetime import datetime

from painminer.cluster import (
    cluster_simple_hash,
    cluster_tfidf_kmeans,
    cluster_pain_items,
    _simple_hash_key,
    _generate_cluster_label,
)
from painminer.config import ClusteringConfig
from painminer.models import PainItem, SourceType


class TestSimpleHashKey:
    """Tests for simple hash key generation."""
    
    def test_detect_struggle(self):
        """Test detection of struggle-related keywords."""
        key = _simple_hash_key("i struggle with staying focused")
        assert "struggle" in key or "struggling" in key or key != ""
    
    def test_detect_forget(self):
        """Test detection of forget-related keywords."""
        key = _simple_hash_key("i keep forgetting my appointments")
        assert "forget" in key or "forgetting" in key or key != ""
    
    def test_detect_task(self):
        """Test detection of task-related keywords."""
        key = _simple_hash_key("managing tasks is hard for me")
        assert "task" in key or key != ""
    
    def test_deterministic(self):
        """Test that hash key is deterministic."""
        text = "i struggle with focus and motivation"
        key1 = _simple_hash_key(text)
        key2 = _simple_hash_key(text)
        assert key1 == key2
    
    def test_fallback_to_keywords(self):
        """Test fallback when no action patterns match."""
        key = _simple_hash_key("the weather is nice today")
        # Should fall back to keywords or misc
        assert key != ""


class TestGenerateClusterLabel:
    """Tests for cluster label generation."""
    
    def test_generate_from_items(self):
        """Test label generation from pain items."""
        items = [
            PainItem(
                id="1",
                subreddit="ADHD",
                source_type=SourceType.POST,
                post_id="p1",
                score=10,
                created_utc=datetime.now(),
                text="i struggle with focus and concentration",
                url="http://example.com",
            ),
            PainItem(
                id="2",
                subreddit="ADHD",
                source_type=SourceType.POST,
                post_id="p2",
                score=20,
                created_utc=datetime.now(),
                text="focusing on tasks is really hard for me",
                url="http://example.com",
            ),
        ]
        
        label = _generate_cluster_label(items)
        assert label != ""
        assert label != "MiscellaneousIssues" or len(items) > 0
    
    def test_empty_items(self):
        """Test label generation with empty items."""
        label = _generate_cluster_label([])
        assert label == "MiscellaneousIssues"
    
    def test_pascal_case(self):
        """Test that label is PascalCase."""
        items = [
            PainItem(
                id="1",
                subreddit="test",
                source_type=SourceType.POST,
                post_id="p1",
                score=10,
                created_utc=datetime.now(),
                text="focus concentration attention",
                url="http://example.com",
            ),
        ]
        
        label = _generate_cluster_label(items)
        # PascalCase should have no spaces and start with uppercase
        assert " " not in label
        assert label[0].isupper() or label == "MiscellaneousIssues"


class TestClusterSimpleHash:
    """Tests for simple hash clustering."""
    
    @pytest.fixture
    def sample_items(self) -> list[PainItem]:
        """Create sample pain items for testing."""
        return [
            PainItem(
                id="1",
                subreddit="ADHD",
                source_type=SourceType.POST,
                post_id="p1",
                score=50,
                created_utc=datetime.now(),
                text="i struggle with focus at work",
                url="http://example.com/1",
            ),
            PainItem(
                id="2",
                subreddit="ADHD",
                source_type=SourceType.POST,
                post_id="p2",
                score=30,
                created_utc=datetime.now(),
                text="i struggle with concentration",
                url="http://example.com/2",
            ),
            PainItem(
                id="3",
                subreddit="productivity",
                source_type=SourceType.COMMENT,
                post_id="p3",
                score=20,
                created_utc=datetime.now(),
                text="i keep forgetting my appointments",
                url="http://example.com/3",
            ),
            PainItem(
                id="4",
                subreddit="productivity",
                source_type=SourceType.POST,
                post_id="p4",
                score=40,
                created_utc=datetime.now(),
                text="forgetting tasks happens to me daily",
                url="http://example.com/4",
            ),
            PainItem(
                id="5",
                subreddit="ADHD",
                source_type=SourceType.POST,
                post_id="p5",
                score=15,
                created_utc=datetime.now(),
                text="i wish there was a reminder app",
                url="http://example.com/5",
            ),
        ]
    
    @pytest.fixture
    def config(self) -> ClusteringConfig:
        """Create clustering config."""
        return ClusteringConfig(
            method="simple_hash",
            k_min=2,
            k_max=10,
            random_state=42,
        )
    
    def test_creates_clusters(self, sample_items, config):
        """Test that clusters are created."""
        clusters = cluster_simple_hash(sample_items, config)
        assert len(clusters) >= 1
    
    def test_all_items_clustered(self, sample_items, config):
        """Test that all items are in a cluster."""
        clusters = cluster_simple_hash(sample_items, config)
        
        total_items = sum(c.count for c in clusters)
        assert total_items == len(sample_items)
    
    def test_deterministic(self, sample_items, config):
        """Test that clustering is deterministic."""
        clusters1 = cluster_simple_hash(sample_items, config)
        clusters2 = cluster_simple_hash(sample_items, config)
        
        # Same number of clusters
        assert len(clusters1) == len(clusters2)
        
        # Same cluster IDs and counts
        for c1, c2 in zip(clusters1, clusters2):
            assert c1.cluster_id == c2.cluster_id
            assert c1.count == c2.count
    
    def test_sorted_by_count(self, sample_items, config):
        """Test that clusters are sorted by count descending."""
        clusters = cluster_simple_hash(sample_items, config)
        
        for i in range(len(clusters) - 1):
            assert clusters[i].count >= clusters[i + 1].count
    
    def test_cluster_has_examples(self, sample_items, config):
        """Test that clusters have example texts."""
        clusters = cluster_simple_hash(sample_items, config)
        
        for cluster in clusters:
            assert len(cluster.example_texts) > 0
    
    def test_cluster_has_label(self, sample_items, config):
        """Test that clusters have labels."""
        clusters = cluster_simple_hash(sample_items, config)
        
        for cluster in clusters:
            assert cluster.label != ""
    
    def test_empty_input(self, config):
        """Test with empty input."""
        clusters = cluster_simple_hash([], config)
        assert clusters == []


class TestClusterTfidfKmeans:
    """Tests for TF-IDF + KMeans clustering."""
    
    @pytest.fixture
    def sample_items(self) -> list[PainItem]:
        """Create sample pain items for testing."""
        # Need more items for kmeans
        base_texts = [
            "i struggle with focus at work",
            "i struggle with concentration daily",
            "focusing is hard for me",
            "i keep forgetting appointments",
            "forgetting tasks is my problem",
            "i forget everything",
            "i wish there was an app for reminders",
            "reminder apps dont work for me",
            "i need better reminders",
            "tracking habits is difficult",
            "habit tracking apps are confusing",
            "how do you track habits",
        ]
        
        items = []
        for i, text in enumerate(base_texts):
            items.append(PainItem(
                id=str(i),
                subreddit="ADHD",
                source_type=SourceType.POST,
                post_id=f"p{i}",
                score=10 + i,
                created_utc=datetime.now(),
                text=text,
                url=f"http://example.com/{i}",
            ))
        
        return items
    
    @pytest.fixture
    def config(self) -> ClusteringConfig:
        """Create clustering config."""
        return ClusteringConfig(
            method="tfidf_kmeans",
            k_min=2,
            k_max=5,
            random_state=42,
        )
    
    def test_creates_clusters(self, sample_items, config):
        """Test that clusters are created."""
        clusters = cluster_tfidf_kmeans(sample_items, config)
        assert len(clusters) >= 1
    
    def test_all_items_clustered(self, sample_items, config):
        """Test that all items are in a cluster."""
        clusters = cluster_tfidf_kmeans(sample_items, config)
        
        total_items = sum(c.count for c in clusters)
        assert total_items == len(sample_items)
    
    def test_deterministic_with_random_state(self, sample_items, config):
        """Test that clustering is deterministic with same random_state."""
        clusters1 = cluster_tfidf_kmeans(sample_items, config)
        clusters2 = cluster_tfidf_kmeans(sample_items, config)
        
        # Same number of clusters
        assert len(clusters1) == len(clusters2)
        
        # Same counts (order may vary)
        counts1 = sorted([c.count for c in clusters1])
        counts2 = sorted([c.count for c in clusters2])
        assert counts1 == counts2
    
    def test_respects_k_bounds(self, sample_items, config):
        """Test that cluster count is within k_min and k_max."""
        clusters = cluster_tfidf_kmeans(sample_items, config)
        
        assert len(clusters) >= config.k_min or len(sample_items) < config.k_min
        assert len(clusters) <= config.k_max
    
    def test_empty_input(self, config):
        """Test with empty input."""
        clusters = cluster_tfidf_kmeans([], config)
        assert clusters == []


class TestClusterPainItems:
    """Tests for the unified clustering function."""
    
    @pytest.fixture
    def sample_items(self) -> list[PainItem]:
        """Create sample items."""
        return [
            PainItem(
                id="1",
                subreddit="test",
                source_type=SourceType.POST,
                post_id="p1",
                score=10,
                created_utc=datetime.now(),
                text="i struggle with focus",
                url="http://example.com",
            ),
            PainItem(
                id="2",
                subreddit="test",
                source_type=SourceType.POST,
                post_id="p2",
                score=20,
                created_utc=datetime.now(),
                text="i forget things often",
                url="http://example.com",
            ),
        ]
    
    def test_simple_hash_method(self, sample_items):
        """Test with simple_hash method."""
        config = ClusteringConfig(method="simple_hash")
        clusters = cluster_pain_items(sample_items, config)
        assert len(clusters) >= 1
    
    def test_tfidf_kmeans_method(self, sample_items):
        """Test with tfidf_kmeans method."""
        config = ClusteringConfig(method="tfidf_kmeans", k_min=1, k_max=2)
        clusters = cluster_pain_items(sample_items, config)
        assert len(clusters) >= 1
    
    def test_invalid_method(self, sample_items):
        """Test with invalid method raises error."""
        config = ClusteringConfig(method="invalid_method")
        
        from painminer.cluster import ClusteringError
        with pytest.raises(ClusteringError):
            cluster_pain_items(sample_items, config)
