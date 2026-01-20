# Painminer Web UI

A modern web interface for Painminer built with Next.js and Tailwind CSS.

## Features

- **Interactive Analysis Form**: Configure subreddits, filters, and clustering options
- **Real-time Progress Tracking**: Watch analysis progress with live updates
- **Beautiful Results View**: Browse app ideas and pain clusters with detailed information
- **Job History**: Track past analyses and revisit results
- **Local Credential Storage**: Reddit API credentials are stored locally in browser
- **Cache Management**: View cache stats and clear cached data

## Tech Stack

- **Next.js 16** - React framework with App Router
- **Tailwind CSS** - Utility-first CSS framework
- **React Query** - Data fetching and state management
- **Lucide React** - Beautiful icons
- **TypeScript** - Type safety

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn
- Running Painminer API (FastAPI backend)

### Installation

```bash
# Navigate to web directory
cd web

# Install dependencies
npm install

# Copy environment file
cp .env.example .env.local

# Edit .env.local if needed (default API URL is http://localhost:8000)
```

### Development

```bash
# Start the development server
npm run dev
```

The app will be available at [http://localhost:3000](http://localhost:3000).

### Production Build

```bash
# Build for production
npm run build

# Start production server
npm start
```

## Running with Backend

1. Start the FastAPI backend:

```bash
# From project root
uvicorn painminer.api:app --reload --host 0.0.0.0 --port 8000
```

2. Start the web UI:

```bash
# From web directory
npm run dev
```

3. Open [http://localhost:3000](http://localhost:3000) in your browser

## Project Structure

```
web/
├── src/
│   ├── app/
│   │   ├── globals.css      # Global styles
│   │   ├── layout.tsx       # Root layout with providers
│   │   └── page.tsx         # Home page
│   ├── components/
│   │   ├── analysis-form.tsx    # Main form for configuring analysis
│   │   ├── dashboard.tsx        # Main dashboard component
│   │   ├── job-progress.tsx     # Progress tracking component
│   │   ├── jobs-list.tsx        # Job history sidebar
│   │   ├── providers.tsx        # React Query provider
│   │   ├── results-view.tsx     # Results display component
│   │   └── status-bar.tsx       # API connection status
│   └── lib/
│       ├── api.ts           # API client functions
│       ├── hooks.ts         # React Query hooks
│       └── types.ts         # TypeScript types
├── .env.example             # Environment variables template
├── .env.local               # Local environment variables
├── package.json
└── README.md
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | URL of the Painminer API | `http://localhost:8000` |

## License

MIT
