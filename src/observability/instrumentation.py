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


def start_emissions_tracker():
    global _TRACKER
    if _CODECARBON_AVAILABLE and _TRACKER is None:
        try:
            _TRACKER = EmissionsTracker(measurement_interval=1, save_to_file=False)
            _TRACKER.start()
        except Exception:
            _TRACKER = None


def stop_emissions_tracker():
    global _TRACKER, _EMISSIONS
    if _TRACKER is not None:
        try:
            _EMISSIONS = _TRACKER.stop()
        except Exception:
            _EMISSIONS = None
        finally:
            _TRACKER = None


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
    agg: Dict[str, Any] = {"calls": len(_METRICS), "by_name": {}, "emissions_kg": _EMISSIONS}
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
]


def reset_metrics():
    """Clear collected metrics (for isolated benchmark runs)."""
    global _METRICS
    _METRICS = []
