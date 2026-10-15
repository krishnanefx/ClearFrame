#!/bin/bash
# Warm cache for demo prompts in background

cd "$(dirname "$0")/.."

echo "🔥 Warming cache for demo prompts..."
echo "This will pre-analyze common queries for fast demos"
echo ""

# Check if API is running
if ! curl -s http://localhost:5001/health > /dev/null; then
    echo "❌ API server not running on port 5001"
    echo "Please start the API server first:"
    echo "  python3 backend/api_server.py"
    exit 1
fi

# Run cache warming script
python3 backend/warm_cache.py

echo ""
echo "✅ Cache warming complete!"
echo "Demo prompts are now ready for instant results"
