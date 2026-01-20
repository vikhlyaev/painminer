"""
Tests for pain extraction module.
"""

import pytest
from datetime import datetime

from painminer.config import FiltersConfig
from painminer.extract import PainExtractor, normalize_pain_text
from painminer.models import RawRedditPost, RawRedditComment, SourceType


class TestNormalizePainText:
    """Tests for text normalization."""
    
    def test_lowercase(self):
        """Test that text is lowercased."""
        result = normalize_pain_text("I STRUGGLE With This")
        assert result == "i struggle with this"
    
    def test_remove_urls(self):
        """Test that URLs are removed."""
        result = normalize_pain_text("Check this https://example.com/path thing")
        assert "https" not in result
        assert "example.com" not in result
        assert "check this" in result
        assert "thing" in result
    
    def test_remove_subreddit_mentions(self):
        """Test that subreddit mentions are removed."""
        result = normalize_pain_text("I saw this on r/ADHD and r/productivity")
        assert "r/adhd" not in result
        assert "r/productivity" not in result
    
    def test_remove_user_mentions(self):
        """Test that user mentions are removed."""
        result = normalize_pain_text("Thanks u/someuser for the tip")
        assert "u/someuser" not in result
    
    def test_collapse_whitespace(self):
        """Test that whitespace is collapsed."""
        result = normalize_pain_text("Too   much    space")
        assert result == "too much space"
    
    def test_remove_markdown(self):
        """Test that markdown formatting is removed."""
        result = normalize_pain_text("**bold** and *italic* text")
        assert "**" not in result
        assert "*" not in result
    
    def test_remove_markdown_links(self):
        """Test that markdown links are converted to text."""
        result = normalize_pain_text("Check [this link](http://example.com) out")
        assert "this link" in result
        assert "http" not in result
    
    def test_empty_string(self):
        """Test handling of empty string."""
        result = normalize_pain_text("")
        assert result == ""
    
    def test_none_handling(self):
        """Test handling of None-like input."""
        result = normalize_pain_text("")
        assert result == ""


class TestPainExtractor:
    """Tests for PainExtractor class."""
    
    @pytest.fixture
    def default_config(self) -> FiltersConfig:
        """Create default filter config for tests."""
        return FiltersConfig(
            include_phrases=[
                "I struggle",
                "I keep forgetting",
                "I wish",
                "How do you",
            ],
            exclude_phrases=[
                "politics",
                "rant",
            ],
            min_pain_length=12,
        )
    
    @pytest.fixture
    def extractor(self, default_config) -> PainExtractor:
        """Create extractor instance."""
        return PainExtractor(default_config)
    
    def test_detect_include_phrase(self, extractor):
        """Test that include phrases are detected."""
        text = "I struggle with staying focused at work."
        assert extractor._contains_include_phrase(text)
    
    def test_detect_include_phrase_case_insensitive(self, extractor):
        """Test that include phrase detection is case-insensitive."""
        text = "I STRUGGLE with staying focused."
        assert extractor._contains_include_phrase(text)
    
    def test_no_include_phrase(self, extractor):
        """Test text without include phrases."""
        text = "This is a normal sentence without any trigger phrases."
        assert not extractor._contains_include_phrase(text)
    
    def test_detect_exclude_phrase(self, extractor):
        """Test that exclude phrases are detected."""
        text = "This is just a rant about my day."
        assert extractor._contains_exclude_phrase(text)
    
    def test_detect_exclude_phrase_case_insensitive(self, extractor):
        """Test that exclude phrase detection is case-insensitive."""
        text = "Let's talk about POLITICS here."
        assert extractor._contains_exclude_phrase(text)
    
    def test_no_exclude_phrase(self, extractor):
        """Test text without exclude phrases."""
        text = "I struggle with staying focused."
        assert not extractor._contains_exclude_phrase(text)
    
    def test_extract_pain_sentences(self, extractor):
        """Test extraction of pain sentences."""
        text = (
            "I struggle with staying focused at work. "
            "It's really hard. "
            "I wish there was an app for this."
        )
        sentences = extractor._extract_pain_sentences(text)
        assert len(sentences) == 2  # Two sentences with include phrases
        assert any("struggle" in s.lower() for s in sentences)
        assert any("wish" in s.lower() for s in sentences)
    
    def test_exclude_filters_sentences(self, extractor):
        """Test that sentences with exclude phrases are filtered."""
        text = (
            "I struggle with staying focused. "
            "This is a rant about productivity. "
            "I wish apps worked better."
        )
        sentences = extractor._extract_pain_sentences(text)
        assert not any("rant" in s.lower() for s in sentences)
    
    def test_min_length_filter(self, extractor):
        """Test that short sentences are filtered."""
        text = "I wish. I struggle with very long sentences about productivity."
        sentences = extractor._extract_pain_sentences(text)
        # "I wish." is too short (< 12 chars)
        assert not any(s == "I wish." for s in sentences)
    
    def test_extract_from_post(self, extractor):
        """Test extraction from a Reddit post."""
        post = RawRedditPost(
            id="test123",
            subreddit="ADHD",
            title="I struggle with focus",
            selftext="I keep forgetting important tasks. It's frustrating.",
            score=50,
            created_utc=datetime.now().timestamp(),
            url="https://reddit.com/r/ADHD/test123",
            num_comments=10,
        )
        
        items = extractor.extract_from_post(post)
        
        assert len(items) >= 1
        for item in items:
            assert item.subreddit == "ADHD"
            assert item.source_type == SourceType.POST
            assert item.post_id == "test123"
            assert item.score == 50
    
    def test_extract_from_post_with_exclude(self, extractor):
        """Test that posts with exclude phrases return empty."""
        post = RawRedditPost(
            id="test456",
            subreddit="ADHD",
            title="Politics rant",
            selftext="This is about politics and I'm frustrated.",
            score=30,
            created_utc=datetime.now().timestamp(),
            url="https://reddit.com/r/ADHD/test456",
            num_comments=5,
        )
        
        items = extractor.extract_from_post(post)
        assert len(items) == 0
    
    def test_extract_from_comment(self, extractor):
        """Test extraction from a Reddit comment."""
        comment = RawRedditComment(
            id="comment123",
            post_id="test123",
            subreddit="productivity",
            body="I struggle with the same issue. How do you handle it?",
            score=25,
            created_utc=datetime.now().timestamp(),
            permalink="/r/productivity/comments/test123/comment123/",
        )
        
        items = extractor.extract_from_comment(comment)
        
        assert len(items) >= 1
        for item in items:
            assert item.subreddit == "productivity"
            assert item.source_type == SourceType.COMMENT
            assert item.post_id == "test123"
    
    def test_extract_all(self, extractor):
        """Test extraction from multiple posts and comments."""
        posts = [
            RawRedditPost(
                id="post1",
                subreddit="ADHD",
                title="I struggle with focus",
                selftext="Need help.",
                score=50,
                created_utc=datetime.now().timestamp(),
                url="https://reddit.com/r/ADHD/post1",
                num_comments=5,
            ),
        ]
        
        comments = [
            RawRedditComment(
                id="comment1",
                post_id="post1",
                subreddit="ADHD",
                body="I wish there was a better solution for this problem.",
                score=10,
                created_utc=datetime.now().timestamp(),
                permalink="/r/ADHD/comments/post1/comment1/",
            ),
        ]
        
        items = extractor.extract_all(posts, comments)
        
        # Should have items from both sources
        assert len(items) >= 1
        
        # Check both source types are present
        source_types = {item.source_type for item in items}
        # At least one source type should be present
        assert len(source_types) >= 1


class TestPainExtractorEdgeCases:
    """Edge case tests for PainExtractor."""
    
    def test_empty_include_phrases(self):
        """Test with empty include phrases (should include all)."""
        config = FiltersConfig(
            include_phrases=[],
            exclude_phrases=["spam"],
            min_pain_length=5,
        )
        extractor = PainExtractor(config)
        
        # With no include filter, should match any text
        assert extractor._contains_include_phrase("Any text here")
    
    def test_empty_exclude_phrases(self):
        """Test with empty exclude phrases."""
        config = FiltersConfig(
            include_phrases=["I struggle"],
            exclude_phrases=[],
            min_pain_length=5,
        )
        extractor = PainExtractor(config)
        
        # Nothing should be excluded
        assert not extractor._contains_exclude_phrase("Any text with rant")
    
    def test_unicode_handling(self):
        """Test handling of Unicode text."""
        config = FiltersConfig(
            include_phrases=["I struggle"],
            exclude_phrases=[],
            min_pain_length=5,
        )
        extractor = PainExtractor(config)
        
        text = "I struggle with émojis 🎉 and spëcial çharacters"
        assert extractor._contains_include_phrase(text)
    
    def test_multiline_text(self):
        """Test handling of multiline text."""
        config = FiltersConfig(
            include_phrases=["I struggle"],
            exclude_phrases=[],
            min_pain_length=10,
        )
        extractor = PainExtractor(config)
        
        text = """I struggle with this.
        
        It happens all the time.
        
        I struggle with that too."""
        
        sentences = extractor._extract_pain_sentences(text)
        assert len(sentences) >= 1
