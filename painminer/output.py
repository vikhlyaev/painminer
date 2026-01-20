"""
Output writers for painminer.

Generates Markdown and JSON reports from analysis results.
"""

import json
from datetime import datetime
from pathlib import Path

from painminer.config import OutputConfig, PainminerConfig
from painminer.models import AppIdea, Cluster


class OutputError(Exception):
    """Raised when output generation fails."""
    pass


def _format_config_summary(config: PainminerConfig) -> str:
    """
    Format configuration summary for markdown.

    Args:
        config: Painminer configuration

    Returns:
        Markdown formatted config summary
    """
    lines = [
        "## Configuration Summary\n",
        "### Subreddits",
    ]

    for sub in config.subreddits:
        lines.append(
            f"- **r/{sub.name}**: {sub.period_days} days, "
            f"min {sub.min_upvotes} upvotes, max {sub.max_posts} posts"
        )

    lines.extend([
        "",
        "### Filters",
        f"- Include phrases: {len(config.filters.include_phrases)}",
        f"- Exclude phrases: {len(config.filters.exclude_phrases)}",
        f"- Min pain length: {config.filters.min_pain_length} chars",
        "",
        "### Clustering",
        f"- Method: `{config.clustering.method}`",
        f"- K range: {config.clustering.k_min} - {config.clustering.k_max}",
        f"- Random state: {config.clustering.random_state}",
        "",
    ])

    return "\n".join(lines)


def _format_cluster_markdown(
    cluster: Cluster,
    rank: int,
    examples_count: int = 3,
) -> str:
    """
    Format a cluster for markdown output.

    Args:
        cluster: Cluster to format
        rank: Rank number
        examples_count: Number of examples to show

    Returns:
        Markdown formatted cluster
    """
    lines = [
        f"### #{rank}: {cluster.label}",
        "",
        f"- **Count**: {cluster.count} pain statements",
        f"- **Avg Score**: {cluster.avg_score:.1f}",
        f"- **Total Score**: {cluster.total_score}",
        "",
        "**Examples:**",
    ]

    for i, example in enumerate(cluster.example_texts[:examples_count], 1):
        # Clean up example for display
        example_clean = example.replace("\n", " ").strip()
        if len(example_clean) > 200:
            example_clean = example_clean[:200] + "..."
        lines.append(f"{i}. _{example_clean}_")

    lines.append("")
    return "\n".join(lines)


def _format_idea_markdown(idea: AppIdea, rank: int) -> str:
    """
    Format an app idea for markdown output.

    Args:
        idea: App idea to format
        rank: Rank number

    Returns:
        Markdown formatted idea
    """
    lines = [
        f"### #{rank}: {idea.idea_name}",
        "",
        f"**Complexity**: {idea.mvp_complexity.value}",
        "",
        f"**Problem**: {idea.problem_statement}",
        "",
        f"**Target User**: {idea.target_user}",
        "",
        "**Core Functions**:",
    ]

    for func in idea.core_functions:
        lines.append(f"- {func}")

    lines.extend([
        "",
        "**Screens**:",
    ])

    for screen in idea.screens:
        lines.append(f"- {screen}")

    lines.extend([
        "",
        "**Local Data**:",
    ])

    for data in idea.local_data:
        lines.append(f"- {data}")

    if idea.minimal_notifications:
        lines.extend([
            "",
            "**Notifications**:",
        ])
        for notif in idea.minimal_notifications:
            lines.append(f"- {notif}")

    lines.extend([
        "",
        "**Reddit Evidence**:",
        f"- {idea.reddit_evidence['count']} mentions",
        f"- Avg score: {idea.reddit_evidence['avg_score']}",
    ])

    if idea.reddit_evidence.get('example_urls'):
        lines.append("- Example links:")
        for url in idea.reddit_evidence['example_urls'][:3]:
            lines.append(f"  - {url}")

    lines.extend(["", "---", ""])

    return "\n".join(lines)


def generate_markdown_report(
    config: PainminerConfig,
    clusters: list[Cluster],
    ideas: list[AppIdea],
    output_config: OutputConfig,
) -> str:
    """
    Generate a complete Markdown report.

    Args:
        config: Painminer configuration
        clusters: All clusters
        ideas: Generated app ideas
        output_config: Output configuration

    Returns:
        Complete Markdown report string
    """
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        "# Painminer Report",
        "",
        f"_Generated: {timestamp}_",
        "",
        _format_config_summary(config),
        "---",
        "",
    ]

    # Top clusters section
    lines.extend([
        "## Top Pain Clusters",
        "",
        f"Showing top {output_config.top_clusters} clusters by size.",
        "",
    ])

    for i, cluster in enumerate(clusters[:output_config.top_clusters], 1):
        lines.append(_format_cluster_markdown(
            cluster,
            i,
            output_config.include_examples_per_cluster,
        ))

    lines.extend([
        "---",
        "",
    ])

    # App ideas section
    lines.extend([
        "## Candidate iOS App Ideas",
        "",
        f"Generated {len(ideas)} feasible app ideas from filtered clusters.",
        "",
    ])

    for i, idea in enumerate(ideas, 1):
        lines.append(_format_idea_markdown(idea, i))

    # Summary
    lines.extend([
        "## Summary",
        "",
        f"- **Total clusters**: {len(clusters)}",
        f"- **Feasible ideas**: {len(ideas)}",
        f"- **Subreddits analyzed**: {len(config.subreddits)}",
        "",
        "_Report generated by painminer_",
    ])

    return "\n".join(lines)


def generate_json_report(
    config: PainminerConfig,
    clusters: list[Cluster],
    ideas: list[AppIdea],
    output_config: OutputConfig,
) -> dict:
    """
    Generate a complete JSON report.

    Args:
        config: Painminer configuration
        clusters: All clusters
        ideas: Generated app ideas
        output_config: Output configuration

    Returns:
        Complete report as dictionary
    """
    timestamp = datetime.utcnow().isoformat()

    # Config summary
    config_summary = {
        "subreddits": [
            {
                "name": sub.name,
                "period_days": sub.period_days,
                "min_upvotes": sub.min_upvotes,
                "max_posts": sub.max_posts,
            }
            for sub in config.subreddits
        ],
        "clustering_method": config.clustering.method,
        "random_state": config.clustering.random_state,
    }

    # Top clusters
    top_clusters = [
        cluster.to_dict()
        for cluster in clusters[:output_config.top_clusters]
    ]

    # Ideas
    ideas_data = [idea.to_dict() for idea in ideas]

    return {
        "generated_at": timestamp,
        "config_summary": config_summary,
        "statistics": {
            "total_clusters": len(clusters),
            "feasible_ideas": len(ideas),
            "subreddits_analyzed": len(config.subreddits),
        },
        "top_clusters": top_clusters,
        "ideas": ideas_data,
    }


class OutputWriter:
    """
    Writes analysis results to files.
    """

    def __init__(self, output_config: OutputConfig) -> None:
        """
        Initialize output writer.

        Args:
            output_config: Output configuration
        """
        self.config = output_config

    def write_markdown(
        self,
        output_path: str | Path,
        config: PainminerConfig,
        clusters: list[Cluster],
        ideas: list[AppIdea],
    ) -> None:
        """
        Write Markdown report to file.

        Args:
            output_path: Path to output file
            config: Painminer configuration
            clusters: All clusters
            ideas: Generated app ideas
        """
        report = generate_markdown_report(
            config,
            clusters,
            ideas,
            self.config,
        )

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            f.write(report)

    def write_json(
        self,
        output_path: str | Path,
        config: PainminerConfig,
        clusters: list[Cluster],
        ideas: list[AppIdea],
    ) -> None:
        """
        Write JSON report to file.

        Args:
            output_path: Path to output file
            config: Painminer configuration
            clusters: All clusters
            ideas: Generated app ideas
        """
        report = generate_json_report(
            config,
            clusters,
            ideas,
            self.config,
        )

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

    def write(
        self,
        output_path: str | Path,
        config: PainminerConfig,
        clusters: list[Cluster],
        ideas: list[AppIdea],
        format: str = "md",
    ) -> None:
        """
        Write report to file in specified format.

        Args:
            output_path: Path to output file
            config: Painminer configuration
            clusters: All clusters
            ideas: Generated app ideas
            format: Output format (md or json)
        """
        if format == "json":
            self.write_json(output_path, config, clusters, ideas)
        else:
            self.write_markdown(output_path, config, clusters, ideas)


def create_output_writer(output_config: OutputConfig) -> OutputWriter:
    """
    Create an output writer.

    Args:
        output_config: Output configuration

    Returns:
        OutputWriter instance
    """
    return OutputWriter(output_config)
