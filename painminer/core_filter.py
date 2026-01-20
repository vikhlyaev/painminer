"""
Core scope filter for painminer.

Filters clusters based on feasibility for simple iOS apps.
"""

import re
from dataclasses import dataclass

from painminer.config import CoreFilterConfig
from painminer.models import Cluster, SolutionShape
from painminer.utils import extract_keywords


class CoreFilterError(Exception):
    """Raised when filtering fails."""
    pass


# Keywords that indicate different solution shapes
SOLUTION_SHAPE_PATTERNS = {
    "reminder": [
        r'\bremind(er|ers|ing)?\b',
        r'\bnotif(y|ication|ications)\b',
        r'\balert(s)?\b',
        r'\bdon\'t forget\b',
        r'\bforget(ting)?\b',
    ],
    "checklist": [
        r'\blist(s)?\b',
        r'\bchecklist(s)?\b',
        r'\btodo(s)?\b',
        r'\bto-do(s)?\b',
        r'\btask(s)?\b',
        r'\btrack(ing)?\b',
    ],
    "timer": [
        r'\btimer(s)?\b',
        r'\btime(r|rs)?\b',
        r'\bpomodoro\b',
        r'\bcountdown\b',
        r'\bstopwatch\b',
        r'\bbreak(s)?\b',
    ],
    "log": [
        r'\blog(s|ging)?\b',
        r'\bjournal(ing)?\b',
        r'\bdiary\b',
        r'\btrack(ing)?\b',
        r'\brecord(ing)?\b',
        r'\bmonitor(ing)?\b',
    ],
    "note": [
        r'\bnote(s)?\b',
        r'\bquick note\b',
        r'\bjot down\b',
        r'\bwrite down\b',
        r'\bcapture\b',
    ],
    "habit": [
        r'\bhabit(s)?\b',
        r'\broutine(s)?\b',
        r'\bdaily\b',
        r'\bstreak(s)?\b',
        r'\bconsisten(t|cy)\b',
    ],
    "calculator": [
        r'\bcalculat(e|or|ion)\b',
        r'\bconvert(er|ing)?\b',
        r'\bmath\b',
        r'\bbudget(ing)?\b',
    ],
    "reference": [
        r'\breference\b',
        r'\blookup\b',
        r'\bquick access\b',
        r'\binfo(rmation)?\b',
    ],
}

# Keywords indicating rejection signals
SOCIAL_SIGNALS = [
    r'\bshare\b', r'\bsharing\b', r'\bsocial\b', r'\bfriend(s)?\b',
    r'\bfollow(er|ers|ing)?\b', r'\bpost(ing)?\b', r'\bfeed\b',
    r'\bcommunity\b', r'\bgroup(s)?\b', r'\bmessag(e|es|ing)\b',
    r'\bchat(ting)?\b', r'\bnetwork(ing)?\b',
]

MARKETPLACE_SIGNALS = [
    r'\bmarketplace\b', r'\bbuy(ing)?\b', r'\bsell(ing)?\b',
    r'\bpurchase\b', r'\bpayment(s)?\b', r'\btransaction(s)?\b',
    r'\bstore\b', r'\bshop(ping)?\b', r'\border(s|ing)?\b',
]

REALTIME_SIGNALS = [
    r'\breal-?time\b', r'\blive\b', r'\bstream(ing)?\b',
    r'\bsync(ing|hroniz)?\b', r'\bcollaborat(e|ion|ive)\b',
    r'\bmultiplayer\b', r'\binstant\b',
]

AI_SIGNALS = [
    r'\bai\b', r'\bartificial intelligence\b', r'\bmachine learning\b',
    r'\bml\b', r'\bgpt\b', r'\bchatgpt\b', r'\bllm\b',
    r'\bsmart suggest(ion)?\b', r'\bpredict(ion|ive)?\b',
    r'\brecommend(ation)?\b', r'\banalyz(e|ing|is)\b',
]


def _match_any_pattern(text: str, patterns: list[str]) -> bool:
    """Check if text matches any of the patterns."""
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def _detect_solution_shape(cluster: Cluster) -> SolutionShape:
    """
    Detect the likely solution shape for a cluster.

    Analyzes cluster content to determine what type of app
    would solve the problem.

    Args:
        cluster: Cluster to analyze

    Returns:
        SolutionShape with detected characteristics
    """
    # Combine all text for analysis
    all_text = " ".join([item.text for item in cluster.items])
    all_text += " " + " ".join(cluster.example_texts)

    # Detect shape type
    shape_scores: dict[str, int] = {}
    shape_keywords: dict[str, list[str]] = {}

    for shape_type, patterns in SOLUTION_SHAPE_PATTERNS.items():
        score = 0
        matched = []
        for pattern in patterns:
            matches = re.findall(pattern, all_text, re.IGNORECASE)
            if matches:
                score += len(matches)
                matched.extend(matches)
        if score > 0:
            shape_scores[shape_type] = score
            shape_keywords[shape_type] = list(set(matched))[:5]

    # Get best shape type
    if shape_scores:
        best_shape = max(shape_scores.keys(), key=lambda k: shape_scores[k])
        keywords = shape_keywords.get(best_shape, [])
    else:
        best_shape = "utility"
        keywords = extract_keywords(all_text)[:5]

    # Detect rejection signals
    requires_social = _match_any_pattern(all_text, SOCIAL_SIGNALS)
    requires_marketplace = _match_any_pattern(all_text, MARKETPLACE_SIGNALS)
    requires_realtime = _match_any_pattern(all_text, REALTIME_SIGNALS)
    requires_ai = _match_any_pattern(all_text, AI_SIGNALS)

    # Estimate complexity
    # Simple heuristics based on shape type
    screen_estimates = {
        "reminder": 2,
        "checklist": 2,
        "timer": 1,
        "log": 2,
        "note": 2,
        "habit": 2,
        "calculator": 1,
        "reference": 1,
        "utility": 2,
    }

    action_estimates = {
        "reminder": 2,
        "checklist": 2,
        "timer": 1,
        "log": 2,
        "note": 1,
        "habit": 2,
        "calculator": 1,
        "reference": 1,
        "utility": 2,
    }

    estimated_screens = screen_estimates.get(best_shape, 2)
    estimated_actions = action_estimates.get(best_shape, 2)

    # Adjust for complexity signals
    if requires_social or requires_marketplace:
        estimated_screens += 2
        estimated_actions += 2
    if requires_realtime:
        estimated_screens += 1
        estimated_actions += 1

    # Determine if solvable locally
    solvable_locally = not (
        requires_social or
        requires_marketplace or
        requires_realtime or
        requires_ai
    )

    return SolutionShape(
        shape_type=best_shape,
        keywords=keywords,
        requires_social=requires_social,
        requires_marketplace=requires_marketplace,
        requires_realtime=requires_realtime,
        requires_ai=requires_ai,
        estimated_screens=estimated_screens,
        estimated_actions=estimated_actions,
        solvable_locally=solvable_locally,
    )


@dataclass
class FilterResult:
    """Result of filtering a cluster."""
    cluster: Cluster
    solution_shape: SolutionShape
    passed: bool
    rejection_reasons: list[str]


class CoreFilter:
    """
    Filters clusters based on feasibility rules.

    Applies reject_if and accept_if rules to determine
    which clusters are suitable for simple iOS apps.
    """

    def __init__(self, config: CoreFilterConfig) -> None:
        """
        Initialize core filter.

        Args:
            config: Core filter configuration
        """
        self.config = config

    def filter_cluster(self, cluster: Cluster) -> FilterResult:
        """
        Filter a single cluster.

        Args:
            cluster: Cluster to filter

        Returns:
            FilterResult with pass/fail status and reasons
        """
        # Detect solution shape
        shape = _detect_solution_shape(cluster)

        rejection_reasons: list[str] = []

        # Apply reject_if rules
        reject_config = self.config.reject_if

        if reject_config.requires_social_network and shape.requires_social:
            rejection_reasons.append("Requires social network features")

        if reject_config.requires_marketplace and shape.requires_marketplace:
            rejection_reasons.append("Requires marketplace features")

        if reject_config.requires_realtime_sync and shape.requires_realtime:
            rejection_reasons.append("Requires real-time synchronization")

        if reject_config.requires_ai_for_value and shape.requires_ai:
            rejection_reasons.append("Requires AI for core value")

        # Apply accept_if rules
        accept_config = self.config.accept_if

        if accept_config.solvable_locally and not shape.solvable_locally:
            rejection_reasons.append("Cannot be solved with local-only data")

        if shape.estimated_screens > accept_config.max_screens:
            rejection_reasons.append(
                f"Estimated {shape.estimated_screens} screens "
                f"exceeds max {accept_config.max_screens}"
            )

        if shape.estimated_actions > accept_config.max_user_actions:
            rejection_reasons.append(
                f"Estimated {shape.estimated_actions} actions "
                f"exceeds max {accept_config.max_user_actions}"
            )

        passed = len(rejection_reasons) == 0

        return FilterResult(
            cluster=cluster,
            solution_shape=shape,
            passed=passed,
            rejection_reasons=rejection_reasons,
        )

    def filter_clusters(self, clusters: list[Cluster]) -> list[FilterResult]:
        """
        Filter multiple clusters.

        Args:
            clusters: Clusters to filter

        Returns:
            List of FilterResults
        """
        return [self.filter_cluster(cluster) for cluster in clusters]

    def get_passing_clusters(
        self,
        clusters: list[Cluster],
    ) -> list[tuple[Cluster, SolutionShape]]:
        """
        Get only clusters that pass the filter.

        Args:
            clusters: Clusters to filter

        Returns:
            List of (cluster, solution_shape) tuples for passing clusters
        """
        results = self.filter_clusters(clusters)
        return [
            (result.cluster, result.solution_shape)
            for result in results
            if result.passed
        ]


def create_core_filter(config: CoreFilterConfig) -> CoreFilter:
    """
    Create a configured core filter.

    Args:
        config: Core filter configuration

    Returns:
        Configured CoreFilter instance
    """
    return CoreFilter(config)
