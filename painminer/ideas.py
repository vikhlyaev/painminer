"""
Idea generation for painminer.

Generates iOS app ideas from filtered clusters.
"""

import re
from typing import Optional

from painminer.models import AppIdea, Cluster, MVPComplexity, SolutionShape
from painminer.utils import extract_keywords, to_pascal_case, truncate_text


class IdeaGenerationError(Exception):
    """Raised when idea generation fails."""
    pass


# Templates for different solution shapes
SHAPE_TEMPLATES = {
    "reminder": {
        "core_functions": [
            "Set one-tap reminders with custom times",
            "Receive push notifications at scheduled times",
            "Quick reschedule with swipe gestures",
        ],
        "screens": ["ReminderList", "AddReminder", "Settings"],
        "local_data": ["Reminders with timestamps", "Notification preferences"],
        "notifications": ["Scheduled reminder alerts"],
    },
    "checklist": {
        "core_functions": [
            "Create and manage task lists",
            "Check off completed items",
            "Organize tasks by category or priority",
        ],
        "screens": ["TaskList", "AddTask", "Categories"],
        "local_data": ["Tasks with completion status", "Categories"],
        "notifications": ["Optional task reminders"],
    },
    "timer": {
        "core_functions": [
            "Start/stop countdown or stopwatch",
            "Save timer presets for quick access",
            "Background timer with alerts",
        ],
        "screens": ["TimerView", "Presets"],
        "local_data": ["Timer presets", "Session history"],
        "notifications": ["Timer completion alert"],
    },
    "log": {
        "core_functions": [
            "Quick entry logging with timestamps",
            "View history in chronological order",
            "Export or share log data",
        ],
        "screens": ["LogList", "AddEntry", "History"],
        "local_data": ["Log entries with timestamps", "Export format preferences"],
        "notifications": ["Optional daily logging reminder"],
    },
    "note": {
        "core_functions": [
            "Quick capture of text notes",
            "Search through notes",
            "Organize with tags or folders",
        ],
        "screens": ["NoteList", "NoteEditor"],
        "local_data": ["Notes with metadata", "Tags/folders"],
        "notifications": [],
    },
    "habit": {
        "core_functions": [
            "Define daily habits to track",
            "Mark habits complete each day",
            "View streak and progress stats",
        ],
        "screens": ["HabitList", "AddHabit", "Progress"],
        "local_data": ["Habits with daily completion records", "Streak counts"],
        "notifications": ["Daily habit reminders"],
    },
    "calculator": {
        "core_functions": [
            "Perform quick calculations",
            "Save calculation history",
            "Custom formulas or conversions",
        ],
        "screens": ["Calculator"],
        "local_data": ["Calculation history", "Custom formulas"],
        "notifications": [],
    },
    "reference": {
        "core_functions": [
            "Quick access to reference information",
            "Search and filter content",
            "Bookmark frequently used items",
        ],
        "screens": ["ReferenceList", "Detail"],
        "local_data": ["Reference data", "Bookmarks"],
        "notifications": [],
    },
    "utility": {
        "core_functions": [
            "Single-purpose utility function",
            "Quick access from home screen",
            "Minimal configuration needed",
        ],
        "screens": ["MainView", "Settings"],
        "local_data": ["User preferences"],
        "notifications": [],
    },
}


def _generate_app_name(cluster: Cluster, shape: SolutionShape) -> str:
    """
    Generate a PascalCase app name.
    
    Args:
        cluster: Source cluster
        shape: Solution shape
        
    Returns:
        PascalCase app name
    """
    # Try to use cluster label if it's good
    label = cluster.label
    
    # Clean up the label
    if label and len(label) > 3:
        name = label
    else:
        # Generate from keywords
        keywords = shape.keywords[:2] if shape.keywords else extract_keywords(
            " ".join(cluster.example_texts)
        )[:2]
        name = " ".join(keywords)
    
    # Add shape type suffix if needed
    if shape.shape_type not in name.lower():
        shape_suffix = shape.shape_type.capitalize()
        name = f"{name} {shape_suffix}"
    
    # Convert to PascalCase and limit length
    pascal_name = to_pascal_case(name)
    
    # Ensure reasonable length
    if len(pascal_name) > 25:
        pascal_name = pascal_name[:25]
    
    return pascal_name if pascal_name else "SimpleHelper"


def _generate_problem_statement(cluster: Cluster) -> str:
    """
    Generate a problem statement from cluster.
    
    Args:
        cluster: Source cluster
        
    Returns:
        Problem statement string
    """
    # Use the most representative example
    if cluster.example_texts:
        best_example = cluster.example_texts[0]
        # Clean up and truncate
        statement = truncate_text(best_example, 150)
        return f"Users report: \"{statement}\""
    
    return "Users struggle with a common problem that needs a simple solution."


def _generate_target_user(cluster: Cluster, shape: SolutionShape) -> str:
    """
    Generate target user description.
    
    Args:
        cluster: Source cluster
        shape: Solution shape
        
    Returns:
        Target user description
    """
    # Extract from subreddit if available
    subreddits = set(item.subreddit for item in cluster.items)
    
    if subreddits:
        sub_str = ", ".join(sorted(subreddits)[:3])
        return f"People interested in {sub_str} topics who need {shape.shape_type} functionality"
    
    return f"Anyone who needs a simple {shape.shape_type} tool"


def _determine_complexity(shape: SolutionShape) -> MVPComplexity:
    """
    Determine MVP complexity rating.
    
    Args:
        shape: Solution shape
        
    Returns:
        MVPComplexity rating
    """
    total = shape.estimated_screens + shape.estimated_actions
    
    if total <= 2:
        return MVPComplexity.XS
    elif total <= 4:
        return MVPComplexity.S
    else:
        return MVPComplexity.M


def _get_reddit_evidence(cluster: Cluster, max_urls: int = 5) -> dict:
    """
    Get Reddit evidence for a cluster.
    
    Args:
        cluster: Source cluster
        max_urls: Maximum URLs to include
        
    Returns:
        Dictionary with count and example URLs
    """
    # Get unique URLs sorted by score
    unique_urls = []
    seen = set()
    
    for item in sorted(cluster.items, key=lambda x: x.score, reverse=True):
        if item.url not in seen:
            seen.add(item.url)
            unique_urls.append(item.url)
            if len(unique_urls) >= max_urls:
                break
    
    return {
        "count": cluster.count,
        "total_score": cluster.total_score,
        "avg_score": round(cluster.avg_score, 1),
        "example_urls": unique_urls,
    }


def generate_idea(
    cluster: Cluster,
    shape: SolutionShape,
) -> AppIdea:
    """
    Generate an app idea from a cluster and shape.
    
    Args:
        cluster: Source cluster
        shape: Solution shape
        
    Returns:
        Generated AppIdea
    """
    # Get templates
    template = SHAPE_TEMPLATES.get(shape.shape_type, SHAPE_TEMPLATES["utility"])
    
    # Generate name
    idea_name = _generate_app_name(cluster, shape)
    
    # Generate problem statement
    problem_statement = _generate_problem_statement(cluster)
    
    # Generate target user
    target_user = _generate_target_user(cluster, shape)
    
    # Get core functions (limit to 3)
    core_functions = template["core_functions"][:3]
    
    # Get screens (limit to 3)
    screens = template["screens"][:3]
    
    # Get local data
    local_data = template["local_data"]
    
    # Get notifications
    notifications = template.get("notifications", [])
    
    # Determine complexity
    complexity = _determine_complexity(shape)
    
    # Get Reddit evidence
    evidence = _get_reddit_evidence(cluster)
    
    return AppIdea(
        idea_name=idea_name,
        problem_statement=problem_statement,
        target_user=target_user,
        core_functions=core_functions,
        screens=screens,
        local_data=local_data,
        minimal_notifications=notifications,
        mvp_complexity=complexity,
        reddit_evidence=evidence,
        cluster=cluster,
    )


class IdeaGenerator:
    """
    Generates app ideas from filtered clusters.
    """
    
    def __init__(self) -> None:
        """Initialize idea generator."""
        pass
    
    def generate(
        self,
        cluster: Cluster,
        shape: SolutionShape,
    ) -> AppIdea:
        """
        Generate an idea from a cluster.
        
        Args:
            cluster: Source cluster
            shape: Solution shape
            
        Returns:
            Generated AppIdea
        """
        return generate_idea(cluster, shape)
    
    def generate_all(
        self,
        clusters_with_shapes: list[tuple[Cluster, SolutionShape]],
    ) -> list[AppIdea]:
        """
        Generate ideas for multiple clusters.
        
        Args:
            clusters_with_shapes: List of (cluster, shape) tuples
            
        Returns:
            List of generated AppIdeas
        """
        ideas = []
        for cluster, shape in clusters_with_shapes:
            idea = self.generate(cluster, shape)
            ideas.append(idea)
        return ideas


def create_idea_generator() -> IdeaGenerator:
    """
    Create an idea generator.
    
    Returns:
        IdeaGenerator instance
    """
    return IdeaGenerator()
