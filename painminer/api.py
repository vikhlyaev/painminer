"""
FastAPI backend for painminer web UI.

Provides REST API endpoints for the painminer pipeline.
"""

import logging
import uuid
from datetime import datetime
from enum import Enum

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from painminer.cache import RedditCache
from painminer.cluster import create_clusterer
from painminer.config import (
    ClusteringConfig,
    CoreFilterConfig,
    FiltersConfig,
    NetworkConfig,
    OutputConfig,
    PainminerConfig,
    ProxySingleConfig,
    RedditConfig,
    SubredditConfig,
    ThrottlingConfig,
)
from painminer.core_filter import create_core_filter
from painminer.extract import create_extractor
from painminer.ideas import create_idea_generator
from painminer.reddit_client import create_reddit_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Painminer API",
    description="API for extracting user pain statements from Reddit and generating iOS app ideas",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== Models ==============

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SubredditInput(BaseModel):
    name: str
    period_days: int = 30
    min_upvotes: int = 10
    max_posts: int = 100
    max_comments_per_post: int = 30


class RedditCredentials(BaseModel):
    client_id: str
    client_secret: str
    username: str
    password: str
    user_agent: str = "painminer/0.1 (personal research)"


class FiltersInput(BaseModel):
    include_phrases: list[str] = Field(default_factory=lambda: [
        "I struggle", "I keep forgetting", "I wish", "How do you",
        "Is there an app", "Anyone else"
    ])
    exclude_phrases: list[str] = Field(default_factory=lambda: ["politics", "rant"])
    min_pain_length: int = 12


class ClusteringInput(BaseModel):
    method: str = "tfidf_kmeans"
    k_min: int = 5
    k_max: int = 20
    random_state: int = 42


class ProxyConfigInput(BaseModel):
    enabled: bool = False
    mode: str = "single"  # single | pool
    single_http: str = ""
    single_https: str = ""
    pool: list[str] = Field(default_factory=list)
    rotate_every_requests: int = 25


class NetworkConfigInput(BaseModel):
    timeout_sec: int = 20
    proxy: ProxyConfigInput = Field(default_factory=ProxyConfigInput)


class AnalysisRequest(BaseModel):
    subreddits: list[SubredditInput]
    reddit: RedditCredentials
    filters: FiltersInput = Field(default_factory=FiltersInput)
    clustering: ClusteringInput = Field(default_factory=ClusteringInput)
    network: NetworkConfigInput = Field(default_factory=NetworkConfigInput)
    use_cache: bool = True


class JobInfo(BaseModel):
    job_id: str
    status: JobStatus
    progress: int = 0
    message: str = ""
    created_at: datetime
    completed_at: datetime | None = None
    result: dict | None = None
    error: str | None = None


class PainItemResponse(BaseModel):
    id: str
    subreddit: str
    source_type: str
    post_id: str
    score: int
    text: str
    url: str


class ClusterResponse(BaseModel):
    cluster_id: str
    label: str
    count: int
    avg_score: float
    total_score: int
    example_texts: list[str]
    items: list[PainItemResponse]


class AppIdeaResponse(BaseModel):
    idea_name: str
    problem_statement: str
    target_user: str
    core_functions: list[str]
    screens: list[str]
    local_data: list[str]
    minimal_notifications: list[str]
    mvp_complexity: str
    reddit_evidence: dict


class AnalysisResult(BaseModel):
    total_posts: int
    total_comments: int
    total_pain_items: int
    total_clusters: int
    total_ideas: int
    clusters: list[ClusterResponse]
    ideas: list[AppIdeaResponse]


# ============== In-memory job storage ==============

jobs: dict[str, JobInfo] = {}


# ============== Helper functions ==============

def build_config(request: AnalysisRequest) -> PainminerConfig:
    """Build PainminerConfig from API request."""
    subreddits = [
        SubredditConfig(
            name=s.name,
            period_days=s.period_days,
            min_upvotes=s.min_upvotes,
            max_posts=s.max_posts,
            max_comments_per_post=s.max_comments_per_post,
        )
        for s in request.subreddits
    ]

    reddit = RedditConfig(
        client_id=request.reddit.client_id,
        client_secret=request.reddit.client_secret,
        username=request.reddit.username,
        password=request.reddit.password,
        user_agent=request.reddit.user_agent,
    )

    filters = FiltersConfig(
        include_phrases=request.filters.include_phrases,
        exclude_phrases=request.filters.exclude_phrases,
        min_pain_length=request.filters.min_pain_length,
    )

    clustering = ClusteringConfig(
        method=request.clustering.method,
        k_min=request.clustering.k_min,
        k_max=request.clustering.k_max,
        random_state=request.clustering.random_state,
    )

    # Build network config with proxy settings
    network = NetworkConfig(
        timeout_sec=request.network.timeout_sec,
        proxies_enabled=request.network.proxy.enabled,
        proxies_mode=request.network.proxy.mode,
        proxies_single=ProxySingleConfig(
            http=request.network.proxy.single_http,
            https=request.network.proxy.single_https,
        ),
        proxies_pool=request.network.proxy.pool,
        rotate_every_requests=request.network.proxy.rotate_every_requests,
    )

    return PainminerConfig(
        subreddits=subreddits,
        reddit=reddit,
        filters=filters,
        clustering=clustering,
        network=network,
        throttling=ThrottlingConfig(),
        core_filter=CoreFilterConfig(),
        output=OutputConfig(),
    )


async def run_analysis(job_id: str, request: AnalysisRequest) -> None:
    """Run the analysis pipeline in background."""
    job = jobs[job_id]

    try:
        job.status = JobStatus.RUNNING
        job.message = "Building configuration..."
        job.progress = 5

        config = build_config(request)

        # Create Reddit client
        job.message = "Connecting to Reddit..."
        job.progress = 10

        reddit_client = create_reddit_client(config, use_cache=request.use_cache)

        # Fetch data
        job.message = "Fetching Reddit data..."
        job.progress = 15

        posts, comments = reddit_client.fetch_all(config)

        job.message = f"Fetched {len(posts)} posts and {len(comments)} comments"
        job.progress = 40

        if not posts:
            raise ValueError("No posts fetched. Check subreddit names and filters.")

        # Extract pain statements
        job.message = "Extracting pain statements..."
        job.progress = 50

        extractor = create_extractor(config.filters)
        pain_items = extractor.extract_all(posts, comments)

        job.message = f"Extracted {len(pain_items)} pain statements"
        job.progress = 60

        if not pain_items:
            raise ValueError("No pain statements extracted. Check include_phrases.")

        # Cluster
        job.message = "Clustering pain statements..."
        job.progress = 70

        clusterer = create_clusterer(config.clustering)
        clusters = clusterer.cluster(pain_items)

        job.message = f"Created {len(clusters)} clusters"
        job.progress = 80

        # Filter
        job.message = "Filtering clusters..."
        job.progress = 85

        core_filter = create_core_filter(config.core_filter)
        passing_clusters = core_filter.get_passing_clusters(clusters)

        # Generate ideas
        job.message = "Generating app ideas..."
        job.progress = 90

        idea_generator = create_idea_generator()
        ideas = idea_generator.generate_all(passing_clusters)

        # Sort ideas
        ideas.sort(
            key=lambda x: (x.cluster.count if x.cluster else 0, x.reddit_evidence.get('avg_score', 0)),
            reverse=True,
        )

        # Build response
        job.progress = 95
        job.message = "Preparing results..."

        clusters_response = []
        for cluster in clusters[:15]:  # Top 15
            items_response = [
                PainItemResponse(
                    id=item.id,
                    subreddit=item.subreddit,
                    source_type=item.source_type.value,
                    post_id=item.post_id,
                    score=item.score,
                    text=item.text,
                    url=item.url,
                )
                for item in cluster.items[:10]  # Top 10 items per cluster
            ]

            clusters_response.append(ClusterResponse(
                cluster_id=cluster.cluster_id,
                label=cluster.label,
                count=cluster.count,
                avg_score=cluster.avg_score,
                total_score=cluster.total_score,
                example_texts=cluster.example_texts[:3],
                items=items_response,
            ))

        ideas_response = [
            AppIdeaResponse(
                idea_name=idea.idea_name,
                problem_statement=idea.problem_statement,
                target_user=idea.target_user,
                core_functions=idea.core_functions,
                screens=idea.screens,
                local_data=idea.local_data,
                minimal_notifications=idea.minimal_notifications,
                mvp_complexity=idea.mvp_complexity.value,
                reddit_evidence=idea.reddit_evidence,
            )
            for idea in ideas
        ]

        result = AnalysisResult(
            total_posts=len(posts),
            total_comments=len(comments),
            total_pain_items=len(pain_items),
            total_clusters=len(clusters),
            total_ideas=len(ideas),
            clusters=clusters_response,
            ideas=ideas_response,
        )

        job.status = JobStatus.COMPLETED
        job.progress = 100
        job.message = "Analysis completed successfully!"
        job.completed_at = datetime.utcnow()
        job.result = result.model_dump()

    except Exception as e:
        logger.exception(f"Job {job_id} failed")
        job.status = JobStatus.FAILED
        job.error = str(e)
        job.message = f"Failed: {str(e)}"
        job.completed_at = datetime.utcnow()


# ============== API Endpoints ==============

@app.get("/")
async def root() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "painminer-api", "version": "0.1.0"}


@app.post("/api/analyze", response_model=JobInfo)
async def start_analysis(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
) -> JobInfo:
    """Start a new analysis job."""
    job_id = str(uuid.uuid4())

    job = JobInfo(
        job_id=job_id,
        status=JobStatus.PENDING,
        progress=0,
        message="Job created",
        created_at=datetime.utcnow(),
    )
    jobs[job_id] = job

    background_tasks.add_task(run_analysis, job_id, request)

    return job


@app.get("/api/jobs/{job_id}", response_model=JobInfo)
async def get_job_status(job_id: str) -> JobInfo:
    """Get the status of a job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    return jobs[job_id]


@app.get("/api/jobs", response_model=list[JobInfo])
async def list_jobs() -> list[JobInfo]:
    """List all jobs."""
    return list(jobs.values())


@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str) -> dict[str, str]:
    """Delete a job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    del jobs[job_id]
    return {"status": "deleted", "job_id": job_id}


@app.get("/api/cache/stats")
async def get_cache_stats() -> dict:
    """Get cache statistics."""
    cache = RedditCache()
    return cache.get_stats()


@app.post("/api/cache/clear")
async def clear_cache() -> dict[str, object]:
    """Clear the cache."""
    cache = RedditCache()
    count = cache.clear()
    return {"status": "cleared", "files_deleted": count}


@app.get("/api/presets/subreddits")
async def get_subreddit_presets() -> list[dict[str, str]]:
    """Get preset subreddit configurations."""
    return [
        {"name": "ADHD", "description": "ADHD community - productivity and focus issues"},
        {"name": "productivity", "description": "Productivity tips and struggles"},
        {"name": "GetMotivated", "description": "Motivation and self-improvement"},
        {"name": "getdisciplined", "description": "Building discipline and habits"},
        {"name": "DecidingToBeBetter", "description": "Self-improvement journey"},
        {"name": "Anxiety", "description": "Anxiety management"},
        {"name": "depression", "description": "Depression support"},
        {"name": "selfimprovement", "description": "General self-improvement"},
        {"name": "nosurf", "description": "Reducing screen time and internet use"},
        {"name": "digitalminimalism", "description": "Digital wellness"},
    ]


@app.get("/api/presets/phrases")
async def get_phrase_presets() -> dict[str, list[str]]:
    """Get preset include/exclude phrases."""
    return {
        "include": [
            "I struggle",
            "I keep forgetting",
            "I wish",
            "How do you",
            "Is there an app",
            "Anyone else",
            "I can't seem to",
            "It's so hard to",
            "I always forget",
            "Does anyone know",
            "I need help with",
            "frustrated with",
            "having trouble",
            "can't figure out",
        ],
        "exclude": [
            "politics",
            "rant",
            "meme",
            "joke",
            "shitpost",
        ],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
