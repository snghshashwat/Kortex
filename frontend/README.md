# Kortex Context Graph Dashboard

Interactive visualization of your second brain's semantic knowledge graph.

## Features

- 🎨 Interactive graph visualization with Cytoscape.js
- 🔗 Shows semantic relationships between notes
- 📊 Real-time similarity scores
- 🎯 Adjustable similarity threshold
- 🚀 Next.js + TypeScript

## Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Configure Environment

Copy `.env.example` to `.env.local` and update:

```bash
cp .env.example .env.local
```

Update `NEXT_PUBLIC_API_BASE_URL` to your Render backend URL:

```
NEXT_PUBLIC_API_BASE_URL=https://kortex-l8jo.onrender.com
```

### 3. Run Locally

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### 4. Deploy to Vercel

1. Push this folder to GitHub as a separate repo (or in a monorepo).
2. On Vercel:
   - Connect your GitHub repo
   - Set root directory to `frontend`
   - Add environment variable:
     - `NEXT_PUBLIC_API_BASE_URL` = your Render URL
   - Deploy

## How to Use

1. In Telegram, send `/link` to Kortex.
2. Copy the access token from the bot reply.
3. Paste the token into the dashboard.

4. The graph shows:
   - **Nodes** = your notes
   - **Node size** = how connected the note is
   - **Edges** = semantic relationships
   - **Edge thickness** = similarity strength
   - **Labels** = similarity scores

5. Adjust the similarity threshold to filter connections:
   - Higher = only strongest connections
   - Lower = more connections shown

6. Click nodes to see their ID and connections

## Understanding the Graph

- **Dense clusters** = related topics
- **Isolated nodes** = unique topics
- **Strong edges (thick)** = highly related notes
- **Weak edges (thin)** = loosely related

Use this to discover how your ideas connect!

## Tech Stack

- **Next.js 14** - React framework
- **TypeScript** - Type safety
- **Cytoscape.js** - Graph visualization
- **Axios** - API calls
- **Vercel** - Deployment

## API Integration

Fetches from your Render backend with a bearer token:

```
GET /graph?similarity_threshold=0.7&limit=50
Authorization: Bearer YOUR_TOKEN
```

Response:

```json
{
  "nodes": [{ "id": "msg_id", "label": "text", "created_at": "..." }],
  "edges": [{ "source": "msg_id_1", "target": "msg_id_2", "similarity": 0.85 }],
  "stats": { "total_messages": 10, "total_edges": 15 }
}
```
