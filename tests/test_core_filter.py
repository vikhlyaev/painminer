"""
Tests for core filter module.
"""

import pytest
from datetime import datetime

from painminer.core_filter import (
    CoreFilter,
    FilterResult,
    _detect_solution_shape,
    _match_any_pattern,
    SOCIAL_SIGNALS,
    MARKETPLACE_SIGNALS,
    REALTIME_SIGNALS,
    AI_SIGNALS,
)
from painminer.config import (
    CoreFilterConfig,
    CoreFilterRejectConfig,
    CoreFilterAcceptConfig,
)
from painminer.models import Cluster, PainItem, SolutionShape, SourceType


class TestMatchAnyPattern:
    """Tests for pattern matching helper."""
    
    def test_match_social(self):
        """Test matching social signals."""
        text = "I want to share this with my friends"
        assert _match_any_pattern(text, SOCIAL_SIGNALS)
    
    def test_match_marketplace(self):
        """Test matching marketplace signals."""
        text = "I want to buy and sell items"
        assert _match_any_pattern(text, MARKETPLACE_SIGNALS)
    
    def test_match_realtime(self):
        """Test matching realtime signals."""
        text = "I need real-time sync across devices"
        assert _match_any_pattern(text, REALTIME_SIGNALS)
    
    def test_match_ai(self):
        """Test matching AI signals."""
        text = "I wish AI could recommend things"
        assert _match_any_pattern(text, AI_SIGNALS)
    
    def test_no_match(self):
        """Test when no patterns match."""
        text = "I struggle with remembering tasks"
        assert not _match_any_pattern(text, SOCIAL_SIGNALS)
        assert not _match_any_pattern(text, MARKETPLACE_SIGNALS)
    
    def test_case_insensitive(self):
        """Test case-insensitive matching."""
        text = "I want to SHARE and POST on SOCIAL media"
        assert _match_any_pattern(text, SOCIAL_SIGNALS)


class TestDetectSolutionShape:
    """Tests for solution shape detection."""
    
    def _create_cluster(self, texts: list[str]) -> Cluster:
        """Helper to create a cluster from texts."""
        items = []
        for i, text in enumerate(texts):
            items.append(PainItem(
                id=str(i),
                subreddit="test",
                source_type=SourceType.POST,
                post_id=f"p{i}",
                score=10,
                created_utc=datetime.now(),
                text=text,
                url="http://example.com",
            ))
        
        return Cluster(
            cluster_id="test",
            label="Test",
            count=len(items),
            example_texts=texts[:3],
            items=items,
        )
    
    def test_detect_reminder_shape(self):
        """Test detection of reminder solution shape."""
        cluster = self._create_cluster([
            "i need reminders for my appointments",
            "i forget to take my medication",
            "notifications would help me remember",
        ])
        
        shape = _detect_solution_shape(cluster)
        assert shape.shape_type in ("reminder", "log", "habit", "utility")
    
    def test_detect_checklist_shape(self):
        """Test detection of checklist solution shape."""
        cluster = self._create_cluster([
            "i need a todo list for my tasks",
            "tracking my checklist is hard",
            "i want to check off items",
        ])
        
        shape = _detect_solution_shape(cluster)
        assert shape.shape_type in ("checklist", "log", "habit", "utility")
    
    def test_detect_timer_shape(self):
        """Test detection of timer solution shape."""
        cluster = self._create_cluster([
            "i need a pomodoro timer",
            "countdown timers help me focus",
            "i use stopwatch for work sessions",
        ])
        
        shape = _detect_solution_shape(cluster)
        assert shape.shape_type in ("timer", "utility")
    
    def test_detect_social_requirement(self):
        """Test detection of social requirements."""
        cluster = self._create_cluster([
            "i want to share my progress with friends",
            "following others would motivate me",
            "posting updates helps me stay accountable",
        ])
        
        shape = _detect_solution_shape(cluster)
        assert shape.requires_social
    
    def test_detect_local_only(self):
        """Test detection of local-only solvable problems."""
        cluster = self._create_cluster([
            "i need reminders for daily tasks",
            "simple timer would help",
            "tracking my habits locally",
        ])
        
        shape = _detect_solution_shape(cluster)
        assert shape.solvable_locally
    
    def test_screen_estimate(self):
        """Test screen count estimation."""
        cluster = self._create_cluster([
            "i need a simple timer",
        ])
        
        shape = _detect_solution_shape(cluster)
        assert 1 <= shape.estimated_screens <= 3


class TestCoreFilter:
    """Tests for CoreFilter class."""
    
    @pytest.fixture
    def default_config(self) -> CoreFilterConfig:
        """Create default filter config."""
        return CoreFilterConfig(
            reject_if=CoreFilterRejectConfig(
                requires_social_network=True,
                requires_marketplace=True,
                requires_realtime_sync=True,
                requires_ai_for_value=True,
            ),
            accept_if=CoreFilterAcceptConfig(
                solvable_locally=True,
                max_screens=3,
                max_user_actions=3,
                value_explained_seconds=10,
            ),
        )
    
    @pytest.fixture
    def core_filter(self, default_config) -> CoreFilter:
        """Create filter instance."""
        return CoreFilter(default_config)
    
    def _create_cluster(self, texts: list[str], label: str = "Test") -> Cluster:
        """Helper to create a cluster."""
        items = []
        for i, text in enumerate(texts):
            items.append(PainItem(
                id=str(i),
                subreddit="test",
                source_type=SourceType.POST,
                post_id=f"p{i}",
                score=10 + i,
                created_utc=datetime.now(),
                text=text,
                url="http://example.com",
            ))
        
        return Cluster(
            cluster_id=f"cluster_{label.lower()}",
            label=label,
            count=len(items),
            example_texts=texts[:3],
            items=items,
        )
    
    def test_accept_simple_local_app(self, core_filter):
        """Test that simple local apps pass filter."""
        cluster = self._create_cluster([
            "i need reminders for taking medication",
            "simple notification would help",
            "just a local timer app",
        ])
        
        result = core_filter.filter_cluster(cluster)
        assert result.passed
        assert len(result.rejection_reasons) == 0
    
    def test_reject_social_requirement(self, core_filter):
        """Test that social requirements cause rejection."""
        cluster = self._create_cluster([
            "i want to share my progress on social media",
            "following friends would motivate me",
            "posting updates to community",
        ])
        
        result = core_filter.filter_cluster(cluster)
        assert not result.passed
        assert any("social" in r.lower() for r in result.rejection_reasons)
    
    def test_reject_marketplace_requirement(self, core_filter):
        """Test that marketplace requirements cause rejection."""
        cluster = self._create_cluster([
            "i want to buy and sell used items",
            "marketplace for local transactions",
            "payment processing needed",
        ])
        
        result = core_filter.filter_cluster(cluster)
        assert not result.passed
        assert any("marketplace" in r.lower() for r in result.rejection_reasons)
    
    def test_reject_realtime_requirement(self, core_filter):
        """Test that realtime sync requirements cause rejection."""
        cluster = self._create_cluster([
            "i need real-time collaboration",
            "live sync with team members",
            "instant updates across devices",
        ])
        
        result = core_filter.filter_cluster(cluster)
        assert not result.passed
        assert any("real-time" in r.lower() for r in result.rejection_reasons)
    
    def test_reject_ai_requirement(self, core_filter):
        """Test that AI requirements cause rejection."""
        cluster = self._create_cluster([
            "i need ai to analyze my patterns",
            "machine learning recommendations",
            "gpt-powered assistant",
        ])
        
        result = core_filter.filter_cluster(cluster)
        assert not result.passed
        assert any("ai" in r.lower() for r in result.rejection_reasons)
    
    def test_filter_multiple_clusters(self, core_filter):
        """Test filtering multiple clusters."""
        clusters = [
            self._create_cluster(
                ["simple reminder app needed"],
                label="Reminders"
            ),
            self._create_cluster(
                ["social network for productivity"],
                label="Social"
            ),
            self._create_cluster(
                ["local habit tracker"],
                label="Habits"
            ),
        ]
        
        results = core_filter.filter_clusters(clusters)
        assert len(results) == 3
        
        # At least some should pass
        passed = [r for r in results if r.passed]
        assert len(passed) >= 1
    
    def test_get_passing_clusters(self, core_filter):
        """Test getting only passing clusters."""
        clusters = [
            self._create_cluster(
                ["simple timer needed"],
                label="Timer"
            ),
            self._create_cluster(
                ["share with friends feature"],
                label="Social"
            ),
        ]
        
        passing = core_filter.get_passing_clusters(clusters)
        
        # Should return tuples of (cluster, shape)
        for cluster, shape in passing:
            assert isinstance(cluster, Cluster)
            assert isinstance(shape, SolutionShape)
    
    def test_result_contains_solution_shape(self, core_filter):
        """Test that result contains solution shape."""
        cluster = self._create_cluster(["simple reminder app"])
        
        result = core_filter.filter_cluster(cluster)
        
        assert result.solution_shape is not None
        assert isinstance(result.solution_shape, SolutionShape)


class TestCoreFilterEdgeCases:
    """Edge case tests for core filter."""
    
    def test_empty_cluster(self):
        """Test with empty cluster."""
        config = CoreFilterConfig()
        filter = CoreFilter(config)
        
        cluster = Cluster(
            cluster_id="empty",
            label="Empty",
            count=0,
            example_texts=[],
            items=[],
        )
        
        result = filter.filter_cluster(cluster)
        # Should still produce a result
        assert result is not None
    
    def test_relaxed_config(self):
        """Test with relaxed config that accepts more."""
        config = CoreFilterConfig(
            reject_if=CoreFilterRejectConfig(
                requires_social_network=False,
                requires_marketplace=False,
                requires_realtime_sync=False,
                requires_ai_for_value=False,
            ),
            accept_if=CoreFilterAcceptConfig(
                solvable_locally=False,
                max_screens=10,
                max_user_actions=10,
            ),
        )
        filter = CoreFilter(config)
        
        # Even social apps should pass
        cluster = Cluster(
            cluster_id="social",
            label="Social",
            count=1,
            example_texts=["share with friends"],
            items=[
                PainItem(
                    id="1",
                    subreddit="test",
                    source_type=SourceType.POST,
                    post_id="p1",
                    score=10,
                    created_utc=datetime.now(),
                    text="share with friends",
                    url="http://example.com",
                ),
            ],
        )
        
        result = filter.filter_cluster(cluster)
        assert result.passed
    
    def test_mixed_content_cluster(self):
        """Test cluster with mixed content."""
        config = CoreFilterConfig()
        filter = CoreFilter(config)
        
        items = [
            PainItem(
                id="1",
                subreddit="test",
                source_type=SourceType.POST,
                post_id="p1",
                score=10,
                created_utc=datetime.now(),
                text="simple reminder for tasks",
                url="http://example.com",
            ),
            PainItem(
                id="2",
                subreddit="test",
                source_type=SourceType.POST,
                post_id="p2",
                score=20,
                created_utc=datetime.now(),
                text="another local utility feature",
                url="http://example.com",
            ),
        ]
        
        cluster = Cluster(
            cluster_id="mixed",
            label="Mixed",
            count=len(items),
            example_texts=[i.text for i in items],
            items=items,
        )
        
        result = filter.filter_cluster(cluster)
        # Should handle mixed content gracefully
        assert result is not None
