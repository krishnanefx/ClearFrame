import time
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

# Fallback import for CodeCarbon
try:
    from codecarbon import EmissionsTracker  # type: ignore
    _CODECARBON_AVAILABLE = True
except Exception:
    _CODECARBON_AVAILABLE = False
    EmissionsTracker = None  # type: ignore

_METRICS: List[Dict[str, Any]] = []
_EMISSIONS: Optional[float] = None
_TRACKER: Optional[EmissionsTracker] = None
_API_REQUESTS: int = 0  # Track API requests for emissions calculation
_LLM_CALLS: int = 0  # Track LLM calls for emissions calculation


def start_emissions_tracker():
    """Initialize emissions tracking."""
    global _TRACKER, _API_REQUESTS, _LLM_CALLS
    _API_REQUESTS = 0
    _LLM_CALLS = 0
    if _CODECARBON_AVAILABLE and _TRACKER is None:
        try:
            _TRACKER = EmissionsTracker(measurement_interval=1, save_to_file=False)
            _TRACKER.start()
        except Exception:
            _TRACKER = None


def stop_emissions_tracker():
    """Stop emissions tracking and calculate based on API requests and LLM calls (5g each)."""
    global _TRACKER, _EMISSIONS, _API_REQUESTS, _LLM_CALLS
    # Calculate emissions: 5g CO2e per API request + 5g per LLM call
    total_calls = _API_REQUESTS + _LLM_CALLS
    _EMISSIONS = (total_calls * 5.0) / 1000.0  # Convert grams to kg
    
    # Also try CodeCarbon if available (but prefer our calculation)
    if _TRACKER is not None:
        try:
            _TRACKER.stop()
        except Exception:
            pass
        finally:
            _TRACKER = None


def track_api_request():
    """Increment API request counter for emissions calculation."""
    global _API_REQUESTS
    _API_REQUESTS += 1


def track_llm_call():
    """Increment LLM call counter for emissions calculation."""
    global _LLM_CALLS
    _LLM_CALLS += 1


def instrument(name: str):
    """Decorator to capture latency and simple success metrics for functions."""
    def deco(fn: Callable):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            success = True
            error_type = None
            try:
                return fn(*args, **kwargs)
            except Exception as e:  # noqa: BLE001
                success = False
                error_type = type(e).__name__
                raise
            finally:
                end = time.perf_counter()
                _METRICS.append({
                    "name": name,
                    "latency_ms": round((end - start) * 1000, 2),
                    "success": success,
                    "error_type": error_type,
                })
        return wrapper
    return deco


def get_metrics() -> Dict[str, Any]:
    agg: Dict[str, Any] = {
        "calls": len(_METRICS), 
        "by_name": {}, 
        "emissions_kg": _EMISSIONS,
        "api_requests": _API_REQUESTS,
        "llm_calls": _LLM_CALLS,
        "total_emissions_events": _API_REQUESTS + _LLM_CALLS,
        "emissions_per_event_g": 5.0
    }
    for m in _METRICS:
        n = m["name"]
        byn = agg["by_name"].setdefault(n, {"count": 0, "failures": 0, "latencies_ms": []})
        byn["count"] += 1
        if not m["success"]:
            byn["failures"] += 1
        byn["latencies_ms"].append(m["latency_ms"])
    # summarize latencies
    for n, stats in agg["by_name"].items():
        lat = stats["latencies_ms"]
        if lat:
            stats["p50_ms"] = sorted(lat)[len(lat)//2]
            stats["avg_ms"] = round(sum(lat)/len(lat), 2)
            stats["max_ms"] = max(lat)
        else:
            stats["p50_ms"] = stats["avg_ms"] = stats["max_ms"] = 0
    return agg

__all__ = [
    "instrument",
    "start_emissions_tracker",
    "stop_emissions_tracker",
    "get_metrics",
    "reset_metrics",
    "track_api_request",
    "track_llm_call",
]


def reset_metrics():
    """Clear collected metrics (for isolated benchmark runs)."""
    global _METRICS, _API_REQUESTS, _EMISSIONS, _LLM_CALLS
    _METRICS = []
    _API_REQUESTS = 0
    _LLM_CALLS = 0
    _EMISSIONS = None
