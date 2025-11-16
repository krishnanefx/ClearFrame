# FactFlow Backend-Frontend Integration

## Summary

Successfully integrated `basic_cli.py` backend with `factflow-ui` React frontend through a Flask API server.

## What Was Created

### 1. **API Server** (`api_server.py`)
- Flask REST API that wraps `basic_cli.py` functionality
- CORS enabled for frontend communication
- Two main endpoints:
  - `POST /api/analyze` - Analyze claims with bias detection
  - `POST /api/search` - Search for articles
  - `GET /health` - Health check

### 2. **Updated Frontend** (`factflow-ui/src/pages/Index.tsx`)
- Modified to call backend API instead of static JSON
- Dynamic analysis based on user input
- Real-time results from backend analysis

### 3. **Configuration Files**
- `factflow-ui/.env.example` - Frontend environment template
- `FULLSTACK_SETUP.md` - Comprehensive setup documentation
- `start.sh` - Convenience script to run both services
- `docker-compose.yml` - Docker orchestration
- `Dockerfile.api` & `factflow-ui/Dockerfile` - Container definitions

### 4. **Test Script** (`test_api.py`)
- Automated API testing
- Verifies all endpoints are working

## Quick Start

### Option 1: Using the Startup Script (Recommended)

```bash
# Install backend dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd factflow-ui && npm install && cd ..

# Start both services
./start.sh
```

### Option 2: Manual Start

Terminal 1 - Backend:
```bash
python3 api_server.py
```

Terminal 2 - Frontend:
```bash
cd factflow-ui
npm run dev
```

### Option 3: Docker

```bash
docker-compose up
```

## Testing

```bash
# Start the API server first
python3 api_server.py

# In another terminal, run tests
python3 test_api.py
```

## Architecture Flow

```
User Input (Frontend)
    ↓
React Component (Index.tsx)
    ↓
HTTP POST to /api/analyze
    ↓
Flask API Server (api_server.py)
    ↓
basic_cli.py functions:
  - fetch_with_category_coverage()
  - analyze_articles_bias()
    ↓
Response with bias analysis
    ↓
Frontend displays results
```

## Key Integration Points

1. **Frontend → Backend Communication**
   - Uses `fetch()` API with JSON payloads
   - Configurable API URL via `VITE_API_URL` env variable

2. **Backend Processing**
   - Reuses existing `basic_cli.py` analysis functions
   - Returns structured JSON matching frontend expectations

3. **Data Transformation**
   - Backend formats bias analysis data
   - Frontend maps to UI components (metrics, sources, etc.)

## Environment Variables Required

Backend (`.env` in root):
```
VALYU_API_KEY=your_key
HOLISTIC_AI_API_TOKEN=your_token
HOLISTIC_AI_TEAM_ID=your_team_id
```

Frontend (`factflow-ui/.env`):
```
VITE_API_URL=http://localhost:5001
```

## Next Steps

1. **Deploy to Production**
   - Use Docker Compose or cloud platform
   - Set up proper HTTPS/SSL
   - Configure production environment variables

2. **Add Features**
   - User authentication
   - Request caching (Redis)
   - Rate limiting
   - WebSocket for real-time updates

3. **Monitoring**
   - Add logging/monitoring (e.g., Sentry)
   - Metrics collection (Prometheus)
   - Performance tracking

## Troubleshooting

**API not responding:**
- Check if backend is running on port 5001
- Verify .env file has correct API keys
- Check firewall/network settings

**CORS errors:**
- Ensure `flask-cors` is installed
- Verify API_URL in frontend matches backend

**Analysis fails:**
- Check API keys are valid
- Verify network connectivity to Valyu/HolisticAI APIs
- Check logs in terminal running `api_server.py`

## Files Modified

- `requirements.txt` - Added Flask dependencies
- `factflow-ui/src/pages/Index.tsx` - Updated to call API

## Files Created

- `api_server.py` - Flask API server
- `FULLSTACK_SETUP.md` - Setup documentation
- `start.sh` - Startup script
- `test_api.py` - API tests
- `docker-compose.yml` - Docker orchestration
- `Dockerfile.api` - Backend container
- `factflow-ui/Dockerfile` - Frontend container
- `factflow-ui/.env.example` - Frontend env template

## Success Criteria

✅ Backend API server runs on port 5001  
✅ Frontend UI runs on port 5173  
✅ Frontend can query backend API  
✅ Backend processes queries using `basic_cli.py`  
✅ Results display in frontend UI  
✅ All endpoints are tested  
✅ Documentation is complete  

## Support

For issues or questions, check:
1. `FULLSTACK_SETUP.md` - Detailed setup guide
2. `test_api.py` - Run tests to diagnose issues
3. Terminal logs from both backend and frontend
