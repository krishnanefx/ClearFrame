#!/usr/bin/env python3
"""
Observability Dashboard Integration for Track B (Glass Box - Observability)

This module aggregates traces, failures, and reasoning explanations into a unified
dashboard view. Integrates with existing dashboard.json structure and provides
real-time observability metrics.

Features:
- Aggregate execution traces with LangSmith links
- Failure rate tracking and categorization
- Performance metrics (latency, throughput, cost)
- Reasoning quality assessment
- Human-friendly summaries
"""

import json
import os
import sys
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field

# Handle imports for both module and standalone execution
if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.observability.trace_visualizer import ExecutionTrace, TraceVisualizer
from src.observability.failure_analyzer import FailureAnalysis, FailureAnalyzer, FailureCategory, FailureSeverity
from src.observability.reasoning_explainer import ReasoningChain, ReasoningExplainer, ExplanationLevel


@dataclass
class ObservabilityMetrics:
    """Aggregated observability metrics."""
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    average_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    total_cost_usd: float = 0.0
    average_cost_usd: float = 0.0
    failure_rate: float = 0.0
    uptime_percentage: float = 100.0
    
    # Failure breakdown
    failures_by_category: Dict[str, int] = field(default_factory=dict)
    failures_by_severity: Dict[str, int] = field(default_factory=dict)
    
    # Performance
    slowest_operations: List[Dict[str, Any]] = field(default_factory=list)
    most_expensive_operations: List[Dict[str, Any]] = field(default_factory=list)
    
    # Quality
    average_confidence: str = "medium"
    reasoning_quality_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "summary": {
                "total_executions": self.total_executions,
                "successful_executions": self.successful_executions,
                "failed_executions": self.failed_executions,
                "success_rate": round((self.successful_executions / max(self.total_executions, 1)) * 100, 2),
                "failure_rate": round(self.failure_rate, 2),
                "uptime_percentage": round(self.uptime_percentage, 2),
            },
            "performance": {
                "average_latency_ms": round(self.average_latency_ms, 2),
                "p95_latency_ms": round(self.p95_latency_ms, 2),
                "p99_latency_ms": round(self.p99_latency_ms, 2),
                "slowest_operations": self.slowest_operations[:5],
            },
            "cost": {
                "total_cost_usd": round(self.total_cost_usd, 6),
                "average_cost_usd": round(self.average_cost_usd, 6),
                "most_expensive_operations": self.most_expensive_operations[:5],
            },
            "failures": {
                "by_category": self.failures_by_category,
                "by_severity": self.failures_by_severity,
            },
            "quality": {
                "average_confidence": self.average_confidence,
                "reasoning_quality_score": round(self.reasoning_quality_score, 2),
            }
        }


class ObservabilityDashboard:
    """Unified observability dashboard for agent executions."""
    
    def __init__(self):
        """Initialize dashboard with component trackers."""
        self.trace_visualizer = TraceVisualizer()
        self.failure_analyzer = FailureAnalyzer()
        self.reasoning_explainer = ReasoningExplainer(level=ExplanationLevel.SIMPLE)
        
        self.traces: List[ExecutionTrace] = []
        self.failures: List[FailureAnalysis] = []
        self.reasoning_chains: List[ReasoningChain] = []
        
        self.langsmith_enabled = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
        self.langsmith_project = os.getenv("LANGCHAIN_PROJECT", "default")
    
    def record_execution(self,
                        query: str,
                        trace: Optional[ExecutionTrace] = None,
                        failure: Optional[FailureAnalysis] = None,
                        reasoning: Optional[ReasoningChain] = None) -> None:
        """Record an agent execution with all observability data.
        
        Args:
            query: User query
            trace: Execution trace (optional)
            failure: Failure analysis (optional)
            reasoning: Reasoning chain (optional)
        """
        if trace:
            self.traces.append(trace)
        
        if failure:
            self.failures.append(failure)
        
        if reasoning:
            self.reasoning_chains.append(reasoning)
    
    def get_metrics(self) -> ObservabilityMetrics:
        """Calculate aggregated metrics.
        
        Returns:
            ObservabilityMetrics object
        """
        metrics = ObservabilityMetrics()
        
        # Basic counts
        metrics.total_executions = len(self.traces)
        metrics.failed_executions = len(self.failures)
        metrics.successful_executions = metrics.total_executions - metrics.failed_executions
        
        if metrics.total_executions > 0:
            metrics.failure_rate = (metrics.failed_executions / metrics.total_executions) * 100
            metrics.uptime_percentage = 100 - metrics.failure_rate
        
        # Latency metrics
        if self.traces:
            latencies = [t.total_duration_ms for t in self.traces if t.total_duration_ms]
            if latencies:
                sorted_latencies = sorted(latencies)
                metrics.average_latency_ms = sum(latencies) / len(latencies)
                metrics.p95_latency_ms = sorted_latencies[int(len(sorted_latencies) * 0.95)]
                metrics.p99_latency_ms = sorted_latencies[int(len(sorted_latencies) * 0.99)]
                
                # Slowest operations
                trace_latencies = [(t.query, t.total_duration_ms, t.trace_id) 
                                   for t in self.traces if t.total_duration_ms]
                trace_latencies.sort(key=lambda x: x[1], reverse=True)
                metrics.slowest_operations = [
                    {"query": q, "latency_ms": l, "trace_id": tid}
                    for q, l, tid in trace_latencies[:5]
                ]
        
        # Cost metrics (from trace metadata if available)
        costs = []
        for trace in self.traces:
            cost = trace.metadata.get("cost_usd")
            if cost:
                costs.append(cost)
        
        if costs:
            metrics.total_cost_usd = sum(costs)
            metrics.average_cost_usd = metrics.total_cost_usd / len(costs)
            
            # Most expensive operations
            trace_costs = [(t.query, t.metadata.get("cost_usd", 0), t.trace_id) 
                          for t in self.traces if t.metadata.get("cost_usd")]
            trace_costs.sort(key=lambda x: x[1], reverse=True)
            metrics.most_expensive_operations = [
                {"query": q, "cost_usd": c, "trace_id": tid}
                for q, c, tid in trace_costs[:5]
            ]
        
        # Failure breakdown
        for failure in self.failures:
            cat = failure.category.value
            sev = failure.severity.value
            metrics.failures_by_category[cat] = metrics.failures_by_category.get(cat, 0) + 1
            metrics.failures_by_severity[sev] = metrics.failures_by_severity.get(sev, 0) + 1
        
        # Reasoning quality
        if self.reasoning_chains:
            confidence_scores = {"high": 3, "medium": 2, "low": 1}
            scores = [confidence_scores.get(rc.confidence_overall, 2) 
                     for rc in self.reasoning_chains]
            avg_score = sum(scores) / len(scores)
            metrics.reasoning_quality_score = (avg_score / 3) * 100  # Convert to percentage
            
            if avg_score >= 2.5:
                metrics.average_confidence = "high"
            elif avg_score >= 1.5:
                metrics.average_confidence = "medium"
            else:
                metrics.average_confidence = "low"
        
        return metrics
    
    def generate_dashboard(self, output_file: Optional[str] = None) -> Dict[str, Any]:
        """Generate complete dashboard payload.
        
        Args:
            output_file: Optional file path to save dashboard JSON
            
        Returns:
            Dashboard dictionary
        """
        metrics = self.get_metrics()
        
        dashboard = {
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "langsmith_enabled": self.langsmith_enabled,
                "langsmith_project": self.langsmith_project,
                "total_traces": len(self.traces),
                "total_failures": len(self.failures),
            },
            "metrics": metrics.to_dict(),
            "recent_executions": self._get_recent_executions(limit=10),
            "failure_details": self._get_failure_details(limit=5),
            "langsmith_links": self._get_langsmith_links(),
        }
        
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(dashboard, f, indent=2)
        
        return dashboard
    
    def _get_recent_executions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent execution summaries."""
        recent = []
        for trace in self.traces[-limit:]:
            recent.append({
                "trace_id": trace.trace_id,
                "query": trace.query,
                "timestamp": trace.start_time.isoformat(),
                "duration_ms": trace.total_duration_ms,
                "status": trace.status.value,
                "spans_count": len(trace.spans),
            })
        return recent
    
    def _get_failure_details(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent failure summaries."""
        failure_details = []
        for failure in self.failures[-limit:]:
            failure_details.append({
                "failure_id": failure.failure_id,
                "query": failure.context.query,
                "timestamp": failure.context.timestamp.isoformat(),
                "category": failure.category.value,
                "severity": failure.severity.value,
                "root_cause": failure.root_cause,
                "remediation_steps": failure.remediation_steps[:3],  # Top 3
            })
        return failure_details
    
    def _get_langsmith_links(self) -> List[Dict[str, str]]:
        """Get LangSmith trace links if available."""
        if not self.langsmith_enabled:
            return []
        
        links = []
        for trace in self.traces[-20:]:  # Last 20 traces
            # Construct LangSmith URL
            # Format: https://smith.langchain.com/o/{org}/projects/{project}/r/{trace_id}
            link = {
                "trace_id": trace.trace_id,
                "query": trace.query,
                "url": f"https://smith.langchain.com/o/{self.langsmith_project}/traces/{trace.trace_id}",
                "timestamp": trace.start_time.isoformat(),
            }
            links.append(link)
        
        return links
    
    def render_dashboard_summary(self) -> str:
        """Render a human-readable dashboard summary.
        
        Returns:
            Formatted summary string
        """
        metrics = self.get_metrics()
        
        lines = []
        lines.append("=" * 80)
        lines.append("📊 OBSERVABILITY DASHBOARD SUMMARY")
        lines.append("=" * 80)
        lines.append(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        if self.langsmith_enabled:
            lines.append(f"🔍 LangSmith: ENABLED (Project: {self.langsmith_project})")
        else:
            lines.append("🔍 LangSmith: DISABLED")
        
        lines.append("")
        
        # Summary stats
        lines.append("EXECUTION SUMMARY:")
        lines.append(f"  Total Executions: {metrics.total_executions}")
        lines.append(f"  ✅ Successful: {metrics.successful_executions}")
        lines.append(f"  ❌ Failed: {metrics.failed_executions}")
        lines.append(f"  Success Rate: {100 - metrics.failure_rate:.1f}%")
        lines.append(f"  Uptime: {metrics.uptime_percentage:.1f}%")
        lines.append("")
        
        # Performance
        lines.append("PERFORMANCE:")
        lines.append(f"  Average Latency: {metrics.average_latency_ms:.2f}ms")
        lines.append(f"  P95 Latency: {metrics.p95_latency_ms:.2f}ms")
        lines.append(f"  P99 Latency: {metrics.p99_latency_ms:.2f}ms")
        
        if metrics.slowest_operations:
            lines.append(f"  Slowest Query: {metrics.slowest_operations[0]['latency_ms']:.2f}ms")
        lines.append("")
        
        # Cost
        if metrics.total_cost_usd > 0:
            lines.append("COST:")
            lines.append(f"  Total Cost: ${metrics.total_cost_usd:.6f}")
            lines.append(f"  Average Cost/Query: ${metrics.average_cost_usd:.6f}")
            lines.append("")
        
        # Failures
        if metrics.failed_executions > 0:
            lines.append("FAILURES:")
            lines.append(f"  Failure Rate: {metrics.failure_rate:.1f}%")
            
            if metrics.failures_by_category:
                lines.append("  By Category:")
                for cat, count in sorted(metrics.failures_by_category.items(), 
                                        key=lambda x: x[1], reverse=True):
                    lines.append(f"    - {cat}: {count}")
            
            if metrics.failures_by_severity:
                lines.append("  By Severity:")
                for sev, count in sorted(metrics.failures_by_severity.items(),
                                        key=lambda x: x[1], reverse=True):
                    icon = "🔴" if sev == "critical" else "🟠" if sev == "high" else "🟡"
                    lines.append(f"    {icon} {sev}: {count}")
            lines.append("")
        
        # Quality
        if self.reasoning_chains:
            lines.append("REASONING QUALITY:")
            lines.append(f"  Average Confidence: {metrics.average_confidence.upper()}")
            lines.append(f"  Quality Score: {metrics.reasoning_quality_score:.1f}/100")
            lines.append("")
        
        # LangSmith links
        if self.langsmith_enabled and self.traces:
            lines.append("LANGSMITH TRACES:")
            lines.append(f"  View all traces: https://smith.langchain.com/o/{self.langsmith_project}")
            recent_traces = self.traces[-3:]
            for trace in recent_traces:
                lines.append(f"  - {trace.query[:50]}: https://smith.langchain.com/o/{self.langsmith_project}/traces/{trace.trace_id}")
            lines.append("")
        
        lines.append("=" * 80)
        return "\n".join(lines)


# Global dashboard instance
_dashboard = ObservabilityDashboard()


def get_dashboard() -> ObservabilityDashboard:
    """Get the global dashboard instance."""
    return _dashboard


def record_execution(**kwargs) -> None:
    """Record an execution (convenience function)."""
    _dashboard.record_execution(**kwargs)


def generate_dashboard(output_file: Optional[str] = None) -> Dict[str, Any]:
    """Generate dashboard (convenience function)."""
    return _dashboard.generate_dashboard(output_file)


# Demo/test code
if __name__ == "__main__":
    print("=== Observability Dashboard Demo ===\n")
    
    from trace_visualizer import SpanType, SpanStatus
    
    dashboard = ObservabilityDashboard()
    
    # Simulate some executions
    for i in range(5):
        # Create trace
        trace = dashboard.trace_visualizer.start_trace(f"Query {i+1}: AI regulation news")
        
        # Add spans
        agent_span = dashboard.trace_visualizer.add_span(
            SpanType.AGENT, "NewsAgent",
            inputs={"query": f"Query {i+1}"}
        )
        dashboard.trace_visualizer.end_span(agent_span, outputs={"result": "success"})
        
        # End trace
        dashboard.trace_visualizer.end_trace(SpanStatus.SUCCESS)
        trace.metadata["cost_usd"] = 0.005 * (i + 1)
        
        # Record
        dashboard.record_execution(query=f"Query {i+1}", trace=trace)
    
    # Simulate a failure
    try:
        raise ValueError("Rate limit exceeded: 429 Too Many Requests")
    except ValueError as e:
        failure = dashboard.failure_analyzer.analyze_failure(
            error=e,
            query="Failed query",
            step_name="SearchStep",
        )
        dashboard.record_execution(query="Failed query", failure=failure)
    
    # Generate and display dashboard
    print(dashboard.render_dashboard_summary())
    
    # Save to file
    output = dashboard.generate_dashboard("observability_dashboard.json")
    print("\n✅ Dashboard saved to: observability_dashboard.json")
    print(f"\nDashboard contains {len(output['recent_executions'])} recent executions")
