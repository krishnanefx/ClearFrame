# FactFlow - Full Stack Setup Guide

Complete guide for running the FactFlow application with both backend API and frontend UI.

## Architecture

```
┌─────────────────────┐
│   Frontend (React)  │
│   Port: 5173        │
└──────────┬──────────┘
           │ HTTP
           ▼
┌─────────────────────┐
│   API Server (Flask)│
│   Port: 5001        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   basic_cli.py      │
│   (Analysis Engine) │
└─────────────────────┘
```

## Prerequisites

- Python 3.8+ (for backend)
- Node.js 18+ (for frontend)
- API Keys:
  - `VALYU_API_KEY` (for news search)
  - `HOLISTIC_AI_API_TOKEN` (for LLM analysis)
  - `HOLISTIC_AI_TEAM_ID`

## Quick Start

### 1. Backend Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your API keys

# Start the Flask API server
python3 api_server.py
```

The API server will start on `http://localhost:5001`

### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend/factflow-ui

# Install dependencies (using npm or bun)
npm install
# or
bun install

# Set up environment variables
cp .env.example .env
# Edit .env if you need to change the API URL (default: http://localhost:5001)

# Start the development server
npm run dev
# or
bun run dev
```

The frontend will start on `http://localhost:5173`

### 3. Access the Application

Open your browser and navigate to `http://localhost:5173`

## Environment Variables

### Backend (.env in root directory)

```bash
# Required
VALYU_API_KEY=your_valyu_api_key
HOLISTIC_AI_API_TOKEN=your_holistic_ai_token
HOLISTIC_AI_TEAM_ID=your_team_id

# Optional
API_PORT=5001
FLASK_DEBUG=false
FAST_LLM_MODEL=us.anthropic.claude-3-5-haiku-20241022-v1:0
```

### Frontend (.env in frontend/factflow-ui directory)

```bash
# API endpoint
VITE_API_URL=http://localhost:5001
```

## API Endpoints

### Health Check
```bash
GET /health
```

### Analyze Claim
```bash
POST /api/analyze
Content-Type: application/json

{
  "query": "sudan war",
  "max_results": 9,
  "search_type": "web",
  "response_length": "large",
  "enable_advanced": false
}
```

### Search Articles
```bash
POST /api/search
Content-Type: application/json

{
  "query": "climate change",
  "max_results": 10,
  "search_type": "web",
  "sources": ["bbc.com", "cnn.com"]
}
```

## Testing the API

You can test the API using curl:

```bash
# Health check
curl http://localhost:5001/health

# Analyze a claim
curl -X POST http://localhost:5001/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "sudan war", "max_results": 9}'
```

## Development Workflow

### Run Both Services Concurrently

Terminal 1 - Backend:
```bash
python3 api_server.py
```

Terminal 2 - Frontend:
```bash
cd frontend/factflow-ui
npm run dev
```

### Production Build

Frontend:
```bash
cd frontend/factflow-ui
npm run build
```

The built files will be in `frontend/factflow-ui/dist/`

## Troubleshooting

### CORS Errors
- Make sure `flask-cors` is installed: `pip install flask-cors`
- Check that API_URL in frontend .env matches your backend URL

### API Connection Failed
- Verify backend is running on port 5001
- Check firewall settings
- Ensure .env variables are set correctly

### Missing Dependencies
Backend:
```bash
pip install -r requirements.txt
```

Frontend:
```bash
cd frontend/factflow-ui
npm install
```

### API Key Errors
- Verify all required API keys are set in `.env`
- Check that `.env` file is in the root directory (same level as `api_server.py`)

## Features

### Frontend
- ✅ Real-time claim analysis
- ✅ Bias metrics visualization
- ✅ Source credibility scoring
- ✅ Grandma Mode (simplified view)
- ✅ Responsive design

### Backend
- ✅ Multi-source news aggregation (Valyu)
- ✅ AI-powered bias detection (HolisticAI)
- ✅ Per-article analysis
- ✅ Narrative comparison
- ✅ Coverage diversity tracking
- ✅ Emissions tracking

## Project Structure

```
.
├── api_server.py           # Flask API server
├── basic_cli.py           # Analysis engine
├── requirements.txt       # Python dependencies
├── .env                   # Backend environment variables
├── src/                   # Backend modules
│   ├── analysis/         # Bias detection logic
│   ├── observability/    # Monitoring tools
│   └── utils/            # Utilities
└── frontend/factflow-ui/          # React frontend
    ├── src/
    │   ├── components/   # UI components
    │   ├── pages/        # Page components
    │   └── lib/          # Utilities
    ├── package.json
    └── .env             # Frontend environment variables
```

## Next Steps

1. **Add Authentication**: Implement API key authentication for production
2. **Add Rate Limiting**: Protect API endpoints from abuse
3. **Deploy**: Deploy to cloud platforms (e.g., Heroku, Vercel, AWS)
4. **Caching**: Add Redis for caching analysis results
5. **WebSockets**: Implement real-time updates for long-running analyses

## License

See main project LICENSE file.
