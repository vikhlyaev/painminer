"""
CLI entry point for painminer.

Provides command-line interface for running the analysis pipeline.
"""

import argparse
import logging
import sys
from pathlib import Path

from painminer import __version__
from painminer.cache import RedditCache
from painminer.cluster import create_clusterer
from painminer.config import ConfigError, load_config, validate_config
from painminer.core_filter import create_core_filter
from painminer.extract import create_extractor
from painminer.ideas import create_idea_generator
from painminer.output import create_output_writer
from painminer.reddit_client import RedditClientError, create_reddit_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class CLIError(Exception):
    """Raised when CLI operations fail."""
    pass


def run_pipeline(
    config_path: str,
    output_path: str,
    output_format: str = "md",
    use_cache: bool = True,
) -> int:
    """
    Run the complete painminer pipeline.

    Args:
        config_path: Path to configuration file
        output_path: Path to output file
        output_format: Output format (md or json)
        use_cache: Whether to use caching

    Returns:
        Exit code (0 for success)
    """
    logger.info(f"Starting painminer v{__version__}")
    logger.info(f"Config: {config_path}")
    logger.info(f"Output: {output_path} ({output_format})")

    # Load configuration
    try:
        logger.info("Loading configuration...")
        config = load_config(config_path)

        # Validate and show warnings
        warnings = validate_config(config)
        for warning in warnings:
            logger.warning(warning)

    except FileNotFoundError as e:
        logger.error(f"Configuration file not found: {e}")
        return 1
    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    # Create Reddit client
    try:
        logger.info("Initializing Reddit client...")
        reddit_client = create_reddit_client(config, use_cache=use_cache)
    except RedditClientError as e:
        logger.error(f"Failed to initialize Reddit client: {e}")
        return 1

    # Fetch data
    try:
        logger.info("Fetching Reddit data...")
        posts, comments = reddit_client.fetch_all(config)
        logger.info(f"Fetched {len(posts)} posts and {len(comments)} comments")

        if not posts:
            logger.warning("No posts fetched. Check subreddit names and filters.")
            return 1

    except RedditClientError as e:
        logger.error(f"Failed to fetch Reddit data: {e}")
        return 1

    # Extract pain statements
    logger.info("Extracting pain statements...")
    extractor = create_extractor(config.filters)
    pain_items = extractor.extract_all(posts, comments)
    logger.info(f"Extracted {len(pain_items)} pain statements")

    if not pain_items:
        logger.warning(
            "No pain statements extracted. "
            "Check include_phrases and min_pain_length settings."
        )
        return 1

    # Cluster pain statements
    logger.info(f"Clustering using {config.clustering.method}...")
    clusterer = create_clusterer(config.clustering)
    clusters = clusterer.cluster(pain_items)
    logger.info(f"Created {len(clusters)} clusters")

    if not clusters:
        logger.warning("No clusters created.")
        return 1

    # Filter clusters
    logger.info("Filtering clusters for feasibility...")
    core_filter = create_core_filter(config.core_filter)
    passing_clusters = core_filter.get_passing_clusters(clusters)
    logger.info(f"{len(passing_clusters)} clusters passed filters")

    # Generate ideas
    logger.info("Generating app ideas...")
    idea_generator = create_idea_generator()
    ideas = idea_generator.generate_all(passing_clusters)

    # Sort ideas by cluster size and avg score
    ideas.sort(
        key=lambda x: (x.cluster.count if x.cluster else 0, x.reddit_evidence.get('avg_score', 0)),
        reverse=True,
    )

    logger.info(f"Generated {len(ideas)} app ideas")

    # Write output
    logger.info(f"Writing output to {output_path}...")
    output_writer = create_output_writer(config.output)
    output_writer.write(
        output_path,
        config,
        clusters,
        ideas,
        format=output_format,
    )

    logger.info("Done!")

    # Print summary
    print(f"\n{'='*50}")
    print("PAINMINER SUMMARY")
    print(f"{'='*50}")
    print(f"Posts analyzed:      {len(posts)}")
    print(f"Comments analyzed:   {len(comments)}")
    print(f"Pain statements:     {len(pain_items)}")
    print(f"Clusters created:    {len(clusters)}")
    print(f"Feasible app ideas:  {len(ideas)}")
    print(f"Output written to:   {output_path}")
    print(f"{'='*50}\n")

    return 0


def clear_cache() -> int:
    """
    Clear the cache directory.

    Returns:
        Exit code (0 for success)
    """
    cache = RedditCache()
    count = cache.clear()
    logger.info(f"Cleared {count} cached files")
    return 0


def show_cache_stats() -> int:
    """
    Show cache statistics.

    Returns:
        Exit code (0 for success)
    """
    cache = RedditCache()
    stats = cache.get_stats()

    print("\nCache Statistics:")
    print(f"  Directory: {stats['directory']}")
    print(f"  Files: {stats['file_count']}")
    print(f"  Size: {stats['total_size_mb']} MB")

    return 0


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog="painminer",
        description=(
            "Extract user pain statements from Reddit and generate iOS app ideas. "
            "A local-only CLI tool for personal research."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m painminer run --config sample_config.yaml --out out.md
  python -m painminer run --config config.yaml --out report.json --format json
  python -m painminer run --config config.yaml --out out.md --no-cache
  python -m painminer cache --clear
  python -m painminer cache --stats
        """,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"painminer {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Run command
    run_parser = subparsers.add_parser(
        "run",
        help="Run the painminer analysis pipeline",
    )
    run_parser.add_argument(
        "--config",
        "-c",
        required=True,
        help="Path to YAML configuration file",
    )
    run_parser.add_argument(
        "--out",
        "-o",
        required=True,
        help="Path to output file",
    )
    run_parser.add_argument(
        "--format",
        "-f",
        choices=["md", "json"],
        default=None,
        help="Output format (default: inferred from file extension)",
    )
    run_parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable caching (re-fetch all data)",
    )
    run_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    # Cache command
    cache_parser = subparsers.add_parser(
        "cache",
        help="Manage the cache",
    )
    cache_parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear all cached data",
    )
    cache_parser.add_argument(
        "--stats",
        action="store_true",
        help="Show cache statistics",
    )

    return parser


def main(args: list[str] | None = None) -> int:
    """
    Main CLI entry point.

    Args:
        args: Command line arguments (uses sys.argv if None)

    Returns:
        Exit code
    """
    parser = create_parser()
    parsed_args = parser.parse_args(args)

    if parsed_args.command is None:
        parser.print_help()
        return 0

    if parsed_args.command == "run":
        # Set log level
        if parsed_args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)

        # Determine output format
        output_format = parsed_args.format
        if output_format is None:
            # Infer from file extension
            output_path = Path(parsed_args.out)
            if output_path.suffix.lower() == ".json":
                output_format = "json"
            else:
                output_format = "md"

        return run_pipeline(
            config_path=parsed_args.config,
            output_path=parsed_args.out,
            output_format=output_format,
            use_cache=not parsed_args.no_cache,
        )

    elif parsed_args.command == "cache":
        if parsed_args.clear:
            return clear_cache()
        elif parsed_args.stats:
            return show_cache_stats()
        else:
            print("Use --clear or --stats with the cache command")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
