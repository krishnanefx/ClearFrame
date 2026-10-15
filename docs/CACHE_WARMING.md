# Demo Cache Warming

This directory contains scripts to pre-cache analysis results for demo prompts, ensuring **instant results** (<100ms) during presentations.

## Performance Impact

- **Without Cache**: 25-40 seconds per query
- **With Cache**: <100ms (0.008s measured) - **3000x faster!** ⚡

## Quick Start

1. **Start the API server** (if not already running):
   ```bash
   python3 backend/api_server.py
   ```

2. **Warm the cache**:
   ```bash
   ./scripts/warm_demo_cache.sh
   ```
   
   Or manually:
   ```bash
   python3 backend/warm_cache.py
   ```

3. **Check cache status**:
   ```bash
   curl http://localhost:5001/api/cache/status | python3 -m json.tool
   ```

## Demo Prompts

The following prompts are pre-cached for instant demo results:

- 🇸🇩 **News on the war in Sudan**
- 🇵🇸 **News on the war in Palestine and Gaza**
- 🇺🇦 **News on the war in Ukraine**
- 💼 **News on Trump's tariffs**

## How It Works

1. **Frontend**: Displays suggested prompt buttons in the UI
2. **Backend**: Checks for full analysis cache using MD5 hash of the query
3. **Cache Hit**: Returns complete response instantly (0 API calls, 0 emissions)
4. **Cache Miss**: Runs full analysis, then caches result for future use
5. **Dual Cache**: Stores both grandma briefs AND full analysis responses

## Cache Architecture

Two-tier caching system for maximum performance:

### Full Analysis Cache (NEW - for instant demos)
- **Location**: `data/analysis_cache/`
- **Contains**: Complete analysis response (articles, bias scores, all metrics)
- **Speed**: <100ms response time
- **Purpose**: Demo performance

### Grandma Brief Cache (Legacy)
- **Location**: `data/grandma_cache/`  
- **Contains**: Only the simplified summary
- **Purpose**: Avoid redundant LLM calls for summaries

## Cache Location

Cached results are stored in two directories:

### Full Analysis Cache
```
data/analysis_cache/
├── 652a3291b6d29ed9ba3e6bd65accf4d8.json  # Sudan (complete response)
├── 99239eee38453c9438d1c8f3862067df.json  # Palestine (complete response)
├── ee4c0c5235fc1a06a3592b44b596386f.json  # Ukraine (complete response)
└── f6ee61690786207300ad8cdaa0300ad4.json  # Tariffs (complete response)
```

### Grandma Brief Cache (legacy)
```
data/grandma_cache/
├── 652a3291b6d29ed9ba3e6bd65accf4d8.json  # Sudan (brief only)
├── 99239eee38453c9438d1c8f3862067df.json  # Palestine (brief only)
├── ee4c0c5235fc1a06a3592b44b596386f.json  # Ukraine (brief only)
└── f6ee61690786207300ad8cdaa0300ad4.json  # Tariffs (brief only)
```

Each cached file is named using MD5 hash of the query string.

## Benefits

✅ **Instant Results**: Cached queries return in <100ms (3000x faster!)  
✅ **Zero Cost**: No API calls for cached queries (saves $$$)  
✅ **Zero Emissions**: No LLM calls = 0g CO₂  
✅ **Demo Ready**: Perfect for live demonstrations to judges  
✅ **Transparent**: Users see identical results, just faster  
✅ **Automatic**: No special flags needed - works automatically  

## Notes

- Cache warming can take 5-10 minutes for all prompts
- Each prompt analyzes 9+ articles with full bias detection
- Cache files are persistent across server restarts
- Cache is automatically used when available (no special flag needed)
