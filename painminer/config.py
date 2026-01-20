"""
Configuration loader and validation for painminer.

Loads YAML config files with environment variable substitution
and validates against expected schema.
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml


class ConfigError(Exception):
    """Raised when configuration is invalid."""
    pass


@dataclass
class SubredditConfig:
    """Configuration for a single subreddit."""
    name: str
    period_days: int = 30
    min_upvotes: int = 10
    max_posts: int = 200
    max_comments_per_post: int = 50


@dataclass
class RedditConfig:
    """Reddit API credentials configuration."""
    client_id: str
    client_secret: str
    username: str
    password: str
    user_agent: str = "painminer/0.1 (personal research)"


@dataclass
class ProxySingleConfig:
    """Single proxy configuration."""
    http: str = ""
    https: str = ""


@dataclass
class NetworkConfig:
    """Network and proxy configuration."""
    timeout_sec: int = 20
    proxies_enabled: bool = False
    proxies_mode: str = "single"  # single | pool
    proxies_single: ProxySingleConfig = field(default_factory=ProxySingleConfig)
    proxies_pool: list[str] = field(default_factory=list)
    rotate_every_requests: int = 25


@dataclass
class ThrottlingConfig:
    """Rate limiting configuration."""
    min_delay_ms: int = 800
    max_delay_ms: int = 2500
    max_retries: int = 4
    backoff_base_sec: float = 2.0


@dataclass
class FiltersConfig:
    """Pain detection filters configuration."""
    include_phrases: list[str] = field(default_factory=list)
    exclude_phrases: list[str] = field(default_factory=list)
    min_pain_length: int = 12


@dataclass
class ClusteringConfig:
    """Clustering algorithm configuration."""
    method: str = "tfidf_kmeans"  # tfidf_kmeans | simple_hash
    k_min: int = 5
    k_max: int = 20
    random_state: int = 42


@dataclass
class CoreFilterRejectConfig:
    """Rules for rejecting clusters."""
    requires_social_network: bool = True
    requires_marketplace: bool = True
    requires_realtime_sync: bool = True
    requires_ai_for_value: bool = True


@dataclass
class CoreFilterAcceptConfig:
    """Rules for accepting clusters."""
    solvable_locally: bool = True
    max_screens: int = 3
    max_user_actions: int = 3
    value_explained_seconds: int = 10


@dataclass
class CoreFilterConfig:
    """Core scope filter configuration."""
    reject_if: CoreFilterRejectConfig = field(default_factory=CoreFilterRejectConfig)
    accept_if: CoreFilterAcceptConfig = field(default_factory=CoreFilterAcceptConfig)


@dataclass
class OutputConfig:
    """Output configuration."""
    top_clusters: int = 15
    include_examples_per_cluster: int = 3


@dataclass
class PainminerConfig:
    """
    Complete painminer configuration.
    
    This is the root configuration object containing all settings.
    """
    subreddits: list[SubredditConfig]
    reddit: RedditConfig
    network: NetworkConfig = field(default_factory=NetworkConfig)
    throttling: ThrottlingConfig = field(default_factory=ThrottlingConfig)
    filters: FiltersConfig = field(default_factory=FiltersConfig)
    clustering: ClusteringConfig = field(default_factory=ClusteringConfig)
    core_filter: CoreFilterConfig = field(default_factory=CoreFilterConfig)
    output: OutputConfig = field(default_factory=OutputConfig)


def substitute_env_vars(value: str) -> str:
    """
    Substitute environment variables in a string.
    
    Supports ${VAR_NAME} syntax.
    
    Args:
        value: String potentially containing ${VAR_NAME} patterns
        
    Returns:
        String with environment variables substituted
        
    Raises:
        ConfigError: If required environment variable is not set
    """
    pattern = r'\$\{([^}]+)\}'
    
    def replace_var(match: re.Match) -> str:
        var_name = match.group(1)
        env_value = os.environ.get(var_name)
        if env_value is None:
            raise ConfigError(
                f"Environment variable '{var_name}' is not set. "
                f"Please set it before running painminer."
            )
        return env_value
    
    return re.sub(pattern, replace_var, value)


def process_env_vars(obj: Any) -> Any:
    """
    Recursively process environment variables in a config object.
    
    Args:
        obj: Configuration object (dict, list, or scalar)
        
    Returns:
        Processed object with environment variables substituted
    """
    if isinstance(obj, dict):
        return {k: process_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [process_env_vars(item) for item in obj]
    elif isinstance(obj, str):
        return substitute_env_vars(obj)
    return obj


def parse_subreddit_config(data: dict) -> SubredditConfig:
    """Parse a single subreddit configuration."""
    return SubredditConfig(
        name=data.get("name", ""),
        period_days=data.get("period_days", 30),
        min_upvotes=data.get("min_upvotes", 10),
        max_posts=data.get("max_posts", 200),
        max_comments_per_post=data.get("max_comments_per_post", 50),
    )


def parse_reddit_config(data: dict) -> RedditConfig:
    """Parse Reddit API configuration."""
    required = ["client_id", "client_secret", "username", "password"]
    for key in required:
        if key not in data or not data[key]:
            raise ConfigError(f"Reddit config missing required field: {key}")
    
    return RedditConfig(
        client_id=data["client_id"],
        client_secret=data["client_secret"],
        username=data["username"],
        password=data["password"],
        user_agent=data.get("user_agent", "painminer/0.1 (personal research)"),
    )


def parse_network_config(data: Optional[dict]) -> NetworkConfig:
    """Parse network configuration."""
    if not data:
        return NetworkConfig()
    
    proxies = data.get("proxies", {})
    single = proxies.get("single", {})
    
    return NetworkConfig(
        timeout_sec=data.get("timeout_sec", 20),
        proxies_enabled=proxies.get("enabled", False),
        proxies_mode=proxies.get("mode", "single"),
        proxies_single=ProxySingleConfig(
            http=single.get("http", ""),
            https=single.get("https", ""),
        ),
        proxies_pool=proxies.get("pool", []),
        rotate_every_requests=proxies.get("rotate_every_requests", 25),
    )


def parse_throttling_config(data: Optional[dict]) -> ThrottlingConfig:
    """Parse throttling configuration."""
    if not data:
        return ThrottlingConfig()
    
    return ThrottlingConfig(
        min_delay_ms=data.get("min_delay_ms", 800),
        max_delay_ms=data.get("max_delay_ms", 2500),
        max_retries=data.get("max_retries", 4),
        backoff_base_sec=data.get("backoff_base_sec", 2.0),
    )


def parse_filters_config(data: Optional[dict]) -> FiltersConfig:
    """Parse filters configuration."""
    if not data:
        return FiltersConfig()
    
    return FiltersConfig(
        include_phrases=data.get("include_phrases", []),
        exclude_phrases=data.get("exclude_phrases", []),
        min_pain_length=data.get("min_pain_length", 12),
    )


def parse_clustering_config(data: Optional[dict]) -> ClusteringConfig:
    """Parse clustering configuration."""
    if not data:
        return ClusteringConfig()
    
    method = data.get("method", "tfidf_kmeans")
    if method not in ("tfidf_kmeans", "simple_hash"):
        raise ConfigError(
            f"Invalid clustering method: {method}. "
            f"Must be 'tfidf_kmeans' or 'simple_hash'."
        )
    
    return ClusteringConfig(
        method=method,
        k_min=data.get("k_min", 5),
        k_max=data.get("k_max", 20),
        random_state=data.get("random_state", 42),
    )


def parse_core_filter_config(data: Optional[dict]) -> CoreFilterConfig:
    """Parse core filter configuration."""
    if not data:
        return CoreFilterConfig()
    
    reject_if = data.get("reject_if", {})
    accept_if = data.get("accept_if", {})
    
    return CoreFilterConfig(
        reject_if=CoreFilterRejectConfig(
            requires_social_network=reject_if.get("requires_social_network", True),
            requires_marketplace=reject_if.get("requires_marketplace", True),
            requires_realtime_sync=reject_if.get("requires_realtime_sync", True),
            requires_ai_for_value=reject_if.get("requires_ai_for_value", True),
        ),
        accept_if=CoreFilterAcceptConfig(
            solvable_locally=accept_if.get("solvable_locally", True),
            max_screens=accept_if.get("max_screens", 3),
            max_user_actions=accept_if.get("max_user_actions", 3),
            value_explained_seconds=accept_if.get("value_explained_seconds", 10),
        ),
    )


def parse_output_config(data: Optional[dict]) -> OutputConfig:
    """Parse output configuration."""
    if not data:
        return OutputConfig()
    
    return OutputConfig(
        top_clusters=data.get("top_clusters", 15),
        include_examples_per_cluster=data.get("include_examples_per_cluster", 3),
    )


def load_config(config_path: str | Path) -> PainminerConfig:
    """
    Load and validate configuration from a YAML file.
    
    Args:
        config_path: Path to the YAML configuration file
        
    Returns:
        Validated PainminerConfig object
        
    Raises:
        ConfigError: If configuration is invalid or file not found
        FileNotFoundError: If config file doesn't exist
    """
    path = Path(config_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in config file: {e}")
    
    if not raw_config:
        raise ConfigError("Configuration file is empty")
    
    # Process environment variables
    try:
        config_data = process_env_vars(raw_config)
    except ConfigError:
        raise
    
    # Validate required sections
    if "subreddits" not in config_data or not config_data["subreddits"]:
        raise ConfigError("Configuration must include at least one subreddit")
    
    if "reddit" not in config_data:
        raise ConfigError("Configuration must include reddit credentials")
    
    # Parse all sections
    subreddits = [
        parse_subreddit_config(sub) 
        for sub in config_data["subreddits"]
    ]
    
    return PainminerConfig(
        subreddits=subreddits,
        reddit=parse_reddit_config(config_data["reddit"]),
        network=parse_network_config(config_data.get("network")),
        throttling=parse_throttling_config(config_data.get("throttling")),
        filters=parse_filters_config(config_data.get("filters")),
        clustering=parse_clustering_config(config_data.get("clustering")),
        core_filter=parse_core_filter_config(config_data.get("core_filter")),
        output=parse_output_config(config_data.get("output")),
    )


def validate_config(config: PainminerConfig) -> list[str]:
    """
    Validate configuration and return list of warnings.
    
    Args:
        config: Configuration to validate
        
    Returns:
        List of warning messages (empty if no warnings)
    """
    warnings = []
    
    # Check subreddit settings
    for sub in config.subreddits:
        if sub.max_posts > 500:
            warnings.append(
                f"Subreddit {sub.name}: max_posts={sub.max_posts} is high, "
                f"may take a long time to fetch"
            )
        if sub.period_days > 90:
            warnings.append(
                f"Subreddit {sub.name}: period_days={sub.period_days} is very long, "
                f"Reddit search may not return accurate results"
            )
    
    # Check throttling
    if config.throttling.min_delay_ms < 500:
        warnings.append(
            "min_delay_ms < 500 may trigger Reddit rate limits"
        )
    
    # Check clustering
    if config.clustering.k_max < config.clustering.k_min:
        warnings.append(
            f"clustering.k_max ({config.clustering.k_max}) < "
            f"k_min ({config.clustering.k_min}), will use k_min"
        )
    
    return warnings
