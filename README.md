# Painminer

A local-only Python CLI tool that extracts repeating "user pain" statements from selected Reddit subreddits, clusters them by intent, and outputs small iOS app ideas (1–3 core functions).

## Features

- **Reddit Integration**: Uses official Reddit API via PRAW (OAuth app credentials)
- **Pain Extraction**: Detects pain/frustration statements using configurable phrase matching
- **Smart Clustering**: Groups similar pain statements using TF-IDF + KMeans or simple hash-based methods
- **Core Scope Filter**: Filters ideas to focus on simple, local-only iOS apps
- **Idea Generation**: Produces actionable app ideas with core functions, screens, and MVP complexity
- **File Caching**: Caches Reddit data to avoid repeated API calls
- **Reproducible Output**: Deterministic results given the same configuration

## Installation

### Requirements

- Python 3.11+
- Reddit API credentials (see below)

### Install Dependencies

```bash
# Clone or download the repository
cd painminer

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package
pip install -e .

# Or install dependencies directly
pip install praw httpx pyyaml scikit-learn pydantic
```

### Development Installation

```bash
pip install -e ".[dev]"
```

## Setting Up Reddit API Credentials

1. Go to https://www.reddit.com/prefs/apps
2. Click "Create App" or "Create Another App"
3. Fill in the details:
   - **name**: painminer (or any name)
   - **App type**: Select "script"
   - **description**: Personal research tool
   - **about url**: (leave blank)
   - **redirect uri**: http://localhost:8080
4. Click "Create app"
5. Note down:
   - **client_id**: The string under "personal use script"
   - **client_secret**: The secret shown

### Set Environment Variables

```bash
export REDDIT_CLIENT_ID="your_client_id"
export REDDIT_CLIENT_SECRET="your_client_secret"
export REDDIT_USERNAME="your_reddit_username"
export REDDIT_PASSWORD="your_reddit_password"
```

Or create a `.env` file and source it:

```bash
# .env file
export REDDIT_CLIENT_ID="abc123"
export REDDIT_CLIENT_SECRET="xyz789"
export REDDIT_USERNAME="myusername"
export REDDIT_PASSWORD="mypassword"
```

```bash
source .env
```

## Usage

### Basic Usage

```bash
# Run with default sample config, output to Markdown
python -m painminer run --config sample_config.yaml --out out.md

# Run with JSON output
python -m painminer run --config sample_config.yaml --out report.json

# Run without cache (re-fetch all data)
python -m painminer run --config config.yaml --out out.md --no-cache

# Verbose output
python -m painminer run --config config.yaml --out out.md --verbose
```

### Cache Management

```bash
# Show cache statistics
python -m painminer cache --stats

# Clear all cached data
python -m painminer cache --clear
```

### Help

```bash
python -m painminer --help
python -m painminer run --help
```

## Configuration

The tool is configured via a YAML file. See `sample_config.yaml` for a complete example.

### Key Configuration Sections

#### Subreddits

```yaml
subreddits:
  - name: "ADHD"
    period_days: 30      # Look back this many days
    min_upvotes: 10      # Minimum post score
    max_posts: 200       # Maximum posts to fetch
    max_comments_per_post: 50  # Comments per post
```

#### Reddit Credentials

```yaml
reddit:
  client_id: "${REDDIT_CLIENT_ID}"
  client_secret: "${REDDIT_CLIENT_SECRET}"
  username: "${REDDIT_USERNAME}"
  password: "${REDDIT_PASSWORD}"
  user_agent: "painminer/0.1 (personal research)"
```

#### Filters

```yaml
filters:
  include_phrases:
    - "I struggle"
    - "I keep forgetting"
    - "I wish"
    - "How do you"
    - "Is there an app"
  exclude_phrases:
    - "politics"
    - "rant"
  min_pain_length: 12
```

#### Clustering

```yaml
clustering:
  method: "tfidf_kmeans"  # or "simple_hash"
  k_min: 5
  k_max: 20
  random_state: 42        # For reproducibility
```

#### Core Filter

```yaml
core_filter:
  reject_if:
    requires_social_network: true
    requires_marketplace: true
    requires_realtime_sync: true
    requires_ai_for_value: true
  accept_if:
    solvable_locally: true
    max_screens: 3
    max_user_actions: 3
```

## Sample Output

### Markdown Report

```markdown
# Painminer Report

_Generated: 2025-01-20 12:00:00 UTC_

## Configuration Summary

### Subreddits
- **r/ADHD**: 30 days, min 10 upvotes, max 200 posts
- **r/productivity**: 30 days, min 15 upvotes, max 150 posts

---

## Top Pain Clusters

### #1: FocusConcentration

- **Count**: 45 pain statements
- **Avg Score**: 32.5
- **Total Score**: 1462

**Examples:**
1. _i struggle with staying focused at work for more than 20 minutes_
2. _focusing on tasks is really hard when there are distractions_
3. _i keep losing focus and dont know how to get back on track_

---

## Candidate iOS App Ideas

### #1: FocusTimer

**Complexity**: S

**Problem**: Users report: "i struggle with staying focused at work..."

**Target User**: People interested in ADHD, productivity topics who need timer functionality

**Core Functions**:
- Start/stop countdown or stopwatch
- Save timer presets for quick access
- Background timer with alerts

**Screens**:
- TimerView
- Presets

**Local Data**:
- Timer presets
- Session history

**Reddit Evidence**:
- 45 mentions
- Avg score: 32.5
```

### JSON Report

```json
{
  "generated_at": "2025-01-20T12:00:00",
  "statistics": {
    "total_clusters": 15,
    "feasible_ideas": 8,
    "subreddits_analyzed": 3
  },
  "ideas": [
    {
      "idea_name": "FocusTimer",
      "problem_statement": "Users report: \"i struggle with staying focused...\"",
      "target_user": "People interested in ADHD topics...",
      "core_functions": ["Start/stop countdown...", "..."],
      "screens": ["TimerView", "Presets"],
      "mvp_complexity": "S",
      "reddit_evidence": {
        "count": 45,
        "avg_score": 32.5
      }
    }
  ]
}
```

## Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=painminer

# Run specific test file
pytest tests/test_extract.py -v
```

## Project Structure

```
painminer/
├── __init__.py         # Package initialization
├── __main__.py         # Entry point for python -m
├── cli.py              # Command-line interface
├── config.py           # Configuration loading and validation
├── models.py           # Data models (PainItem, Cluster, AppIdea, etc.)
├── network.py          # Network utilities, proxy support, throttling
├── cache.py            # File-based caching
├── utils.py            # Utility functions
├── reddit_client.py    # Reddit API client using PRAW
├── extract.py          # Pain statement extraction
├── cluster.py          # Clustering algorithms
├── core_filter.py      # Core scope filtering
├── ideas.py            # App idea generation
└── output.py           # Markdown and JSON output writers

tests/
├── __init__.py
├── test_extract.py     # Tests for extraction
├── test_cluster.py     # Tests for clustering
└── test_core_filter.py # Tests for filtering
```

## Rate Limits & Being a Good Citizen

This tool respects Reddit's API guidelines:

- **Throttling**: Configurable delays between requests (default: 800-2500ms)
- **Retries**: Exponential backoff on failures
- **Caching**: Results are cached to minimize repeated API calls
- **User Agent**: Identifies as a personal research tool

Please:
- Don't reduce delays below recommended minimums
- Use caching to avoid unnecessary API calls
- Don't run the tool excessively
- Respect Reddit's terms of service

## Troubleshooting

### "Environment variable not set" error

Make sure you've exported all required environment variables:

```bash
export REDDIT_CLIENT_ID="..."
export REDDIT_CLIENT_SECRET="..."
export REDDIT_USERNAME="..."
export REDDIT_PASSWORD="..."
```

### "Authentication failed" error

- Verify your Reddit app is type "script"
- Check that username and password are correct
- Ensure the app is authorized for your account

### "No pain statements extracted" warning

- Check your `include_phrases` configuration
- Lower `min_pain_length` if statements are too short
- Verify subreddit names are correct

### "Rate limited" errors

- Increase `min_delay_ms` and `max_delay_ms`
- Reduce `max_posts` per subreddit
- Wait and try again later

## License

MIT License - for personal research use only.

## Disclaimer

This tool is for personal research purposes only. Use responsibly and in accordance with Reddit's terms of service. The generated app ideas are suggestions based on observed patterns and should be validated with additional research.
