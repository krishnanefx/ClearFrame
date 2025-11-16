#!/usr/bin/env python3
"""
Execution Trace Visualization for Track B (Glass Box - Observability)

This module captures and formats LangChain execution traces into human-readable views:
- Timeline view: chronological sequence of agent actions
- Tree view: hierarchical representation of tool calls and reasoning
- Span details: detailed breakdown of each execution step

Integrates with LangSmith for automatic trace capture and provides local
visualization for debugging and analysis.
"""

import os
import json
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from enum import Enum


class SpanType(Enum):
    """Types of execution spans in agent traces."""
    AGENT = "agent"
    TOOL = "tool"
    LLM = "llm"
    CHAIN = "chain"
    RETRIEVER = "retriever"
    PARSER = "parser"


class SpanStatus(Enum):
    """Execution status of a span."""
    SUCCESS = "success"
    ERROR = "error"
    RUNNING = "running"
    PENDING = "pending"


@dataclass
class ExecutionSpan:
    """Represents a single execution span in the trace."""
    span_id: str
    parent_id: Optional[str]
    span_type: SpanType
    name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    status: SpanStatus = SpanStatus.PENDING
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    children: List['ExecutionSpan'] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary for JSON serialization."""
        result = {
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "span_type": self.span_type.value,
            "name": self.name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status.value,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "metadata": self.metadata,
            "error": self.error,
        }
        if self.children:
            result["children"] = [child.to_dict() for child in self.children]
        return result


@dataclass
class ExecutionTrace:
    """Complete execution trace for an agent run."""
    trace_id: str
    query: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_duration_ms: Optional[float] = None
    status: SpanStatus = SpanStatus.RUNNING
    root_span: Optional[ExecutionSpan] = None
    spans: List[ExecutionSpan] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert trace to dictionary for JSON serialization."""
        return {
            "trace_id": self.trace_id,
            "query": self.query,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_duration_ms": self.total_duration_ms,
            "status": self.status.value,
            "root_span": self.root_span.to_dict() if self.root_span else None,
            "spans": [span.to_dict() for span in self.spans],
            "metadata": self.metadata,
            "tags": self.tags,
        }


class TraceVisualizer:
    """Visualize execution traces in multiple formats."""
    
    def __init__(self, langsmith_enabled: bool = None):
        """Initialize trace visualizer.
        
        Args:
            langsmith_enabled: Whether LangSmith tracing is enabled (auto-detect if None)
        """
        if langsmith_enabled is None:
            langsmith_enabled = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
        self.langsmith_enabled = langsmith_enabled
        self.current_trace: Optional[ExecutionTrace] = None
    
    def start_trace(self, 
                   query: str, 
                   trace_id: Optional[str] = None,
                   mode: Optional[str] = None,
                   tools: Optional[List[str]] = None,
                   model: Optional[str] = None,
                   tags: Optional[List[str]] = None) -> ExecutionTrace:
        """Start a new execution trace.
        
        Args:
            query: The user query being traced
            trace_id: Optional trace ID (generated if not provided)
            mode: Execution mode (e.g., pipeline, agent, structured)
            tools: Tools used during the run
            model: Model name
            tags: Additional tags to help LangSmith grouping
            
        Returns:
            ExecutionTrace object
        """
        if trace_id is None:
            trace_id = f"trace_{datetime.now(timezone.utc).timestamp()}"
        
        trace_tags = tags or []
        if mode and f"mode:{mode}" not in trace_tags:
            trace_tags.append(f"mode:{mode}")
        if model and f"model:{model}" not in trace_tags:
            trace_tags.append(f"model:{model}")
        if tools:
            for tool in tools:
                tag = f"tool:{tool}"
                if tag not in trace_tags:
                    trace_tags.append(tag)

        self.current_trace = ExecutionTrace(
            trace_id=trace_id,
            query=query,
            start_time=datetime.now(timezone.utc),
            metadata={
                "langsmith_enabled": self.langsmith_enabled,
                "langchain_project": os.getenv("LANGCHAIN_PROJECT", "default"),
                "mode": mode,
                "tools": tools or [],
                "model": model,
            }
            ,
            tags=trace_tags,
        )
        return self.current_trace
    
    def end_trace(self, 
                 status: SpanStatus = SpanStatus.SUCCESS, 
                 error_type: Optional[str] = None,
                 feedback_score: Optional[float] = None,
                 feedback_notes: Optional[str] = None) -> Optional[ExecutionTrace]:
        """End the current trace.
        
        Args:
            status: Final status of the trace
            error_type: Optional error type/category for filtering
            feedback_score: Optional numeric feedback (e.g., 1-5) to push to LangSmith
            feedback_notes: Optional free-form feedback summary
            
        Returns:
            Completed ExecutionTrace object
        """
        if self.current_trace:
            self.current_trace.end_time = datetime.now(timezone.utc)
            if self.current_trace.start_time:
                delta = (self.current_trace.end_time - self.current_trace.start_time).total_seconds()
                self.current_trace.total_duration_ms = delta * 1000
            self.current_trace.status = status
            
            # Attach run-level KPI metadata used by dashboards
            self.current_trace.metadata["latency_ms"] = self.current_trace.total_duration_ms
            self.current_trace.metadata["success"] = status == SpanStatus.SUCCESS
            # Aggregate cost across spans if present
            cost_spans = [
                s.metadata.get("cost_usd")
                for s in self.current_trace.spans
                if isinstance(s.metadata, dict) and "cost_usd" in s.metadata
            ]
            if cost_spans:
                self.current_trace.metadata["cost_usd"] = sum(
                    c for c in cost_spans if c is not None
                )
            # Aggregate token usage across spans
            token_fields = ["input_tokens", "output_tokens", "total_tokens"]
            token_usage: Dict[str, float] = {}
            for span in self.current_trace.spans:
                tokens = None
                if isinstance(span.metadata, dict):
                    if isinstance(span.metadata.get("token_usage"), dict):
                        tokens = span.metadata["token_usage"]
                    else:
                        tokens = {k: span.metadata.get(k) for k in token_fields}
                if isinstance(tokens, dict):
                    for k, v in tokens.items():
                        if v is None:
                            continue
                        token_usage[k] = token_usage.get(k, 0) + float(v)
            if token_usage:
                self.current_trace.metadata["token_usage"] = token_usage
            # Optional feedback, surfaced to LangSmith as metadata + tag
            if feedback_score is not None:
                self.current_trace.metadata["feedback_score"] = feedback_score
                tag = f"feedback:{feedback_score}"
                if tag not in self.current_trace.tags:
                    self.current_trace.tags.append(tag)
            if feedback_notes:
                self.current_trace.metadata["feedback_notes"] = feedback_notes
            # If error type not provided, derive from the last error span if present
            if not error_type:
                error_spans = [s for s in self.current_trace.spans if s.status == SpanStatus.ERROR or s.error]
                if error_spans:
                    error_type = error_spans[-1].name
            if error_type:
                self.current_trace.metadata["error_type"] = error_type
            return self.current_trace
        return None
    
    def add_span(self, 
                 span_type: SpanType, 
                 name: str,
                 parent_id: Optional[str] = None,
                 inputs: Optional[Dict[str, Any]] = None,
                 metadata: Optional[Dict[str, Any]] = None) -> ExecutionSpan:
        """Add a span to the current trace.
        
        Args:
            span_type: Type of span
            name: Name/description of the span
            parent_id: ID of parent span (None for root)
            inputs: Input data for the span
            metadata: Additional metadata
            
        Returns:
            Created ExecutionSpan object
        """
        span_id = f"span_{len(self.current_trace.spans) if self.current_trace else 0}"
        span = ExecutionSpan(
            span_id=span_id,
            parent_id=parent_id,
            span_type=span_type,
            name=name,
            start_time=datetime.now(timezone.utc),
            inputs=inputs or {},
            metadata=metadata or {},
        )
        
        if self.current_trace:
            self.current_trace.spans.append(span)
            if parent_id is None and self.current_trace.root_span is None:
                self.current_trace.root_span = span
        
        return span
    
    def end_span(self, span: ExecutionSpan, 
                 status: SpanStatus = SpanStatus.SUCCESS,
                 outputs: Optional[Dict[str, Any]] = None,
                 error: Optional[str] = None) -> ExecutionSpan:
        """End a span and record its outputs/status.
        
        Args:
            span: The span to complete
            status: Final status
            outputs: Output data
            error: Error message if failed
            
        Returns:
            Updated span
        """
        span.end_time = datetime.now(timezone.utc)
        delta = (span.end_time - span.start_time).total_seconds()
        span.duration_ms = delta * 1000
        span.status = status
        if outputs:
            span.outputs = outputs
            # Surface common metrics on metadata for downstream aggregation
            if isinstance(outputs, dict):
                if "cost_usd" in outputs:
                    span.metadata["cost_usd"] = outputs.get("cost_usd")
                # Token usage keys (common LangChain/LangSmith patterns)
                token_usage = outputs.get("token_usage") or outputs.get("tokens")
                if isinstance(token_usage, dict):
                    span.metadata["token_usage"] = token_usage
                else:
                    tf = {}
                    for key in ("input_tokens", "output_tokens", "total_tokens"):
                        if key in outputs:
                            tf[key] = outputs[key]
                    if tf:
                        span.metadata["token_usage"] = tf
        if error:
            span.error = error
        return span
    
    def render_timeline(self, trace: Optional[ExecutionTrace] = None) -> str:
        """Render trace as a chronological timeline.
        
        Args:
            trace: Trace to render (uses current_trace if None)
            
        Returns:
            Human-readable timeline string
        """
        if trace is None:
            trace = self.current_trace
        if not trace:
            return "No trace available"
        
        lines = []
        lines.append("=" * 80)
        lines.append(f"EXECUTION TIMELINE: {trace.query}")
        lines.append(f"Trace ID: {trace.trace_id}")
        lines.append(f"Status: {trace.status.value.upper()}")
        if trace.total_duration_ms:
            lines.append(f"Total Duration: {trace.total_duration_ms:.2f}ms")
        lines.append("=" * 80)
        
        # Sort spans by start time
        sorted_spans = sorted(trace.spans, key=lambda s: s.start_time)
        
        for i, span in enumerate(sorted_spans, 1):
            status_icon = "✅" if span.status == SpanStatus.SUCCESS else "❌" if span.status == SpanStatus.ERROR else "⏳"
            indent = "  " * (self._get_depth(span, trace) - 1)
            
            lines.append(f"\n{i}. {indent}{status_icon} [{span.span_type.value.upper()}] {span.name}")
            
            if span.duration_ms is not None:
                lines.append(f"{indent}   Duration: {span.duration_ms:.2f}ms")
            
            if span.inputs:
                lines.append(f"{indent}   Inputs: {self._format_data(span.inputs, max_len=100)}")
            
            if span.outputs:
                lines.append(f"{indent}   Outputs: {self._format_data(span.outputs, max_len=100)}")
            
            if span.error:
                lines.append(f"{indent}   ⚠️  Error: {span.error}")
        
        lines.append("\n" + "=" * 80)
        return "\n".join(lines)
    
    def render_tree(self, trace: Optional[ExecutionTrace] = None) -> str:
        """Render trace as a hierarchical tree.
        
        Args:
            trace: Trace to render (uses current_trace if None)
            
        Returns:
            Human-readable tree string
        """
        if trace is None:
            trace = self.current_trace
        if not trace or not trace.root_span:
            return "No trace available"
        
        lines = []
        lines.append("=" * 80)
        lines.append(f"EXECUTION TREE: {trace.query}")
        lines.append(f"Trace ID: {trace.trace_id}")
        lines.append("=" * 80)
        
        # Build tree structure
        self._build_span_tree(trace)
        
        # Render tree
        self._render_span_tree(trace.root_span, lines, prefix="", is_last=True)
        
        lines.append("=" * 80)
        return "\n".join(lines)
    
    def render_summary(self, trace: Optional[ExecutionTrace] = None) -> str:
        """Render a concise summary of the trace.
        
        Args:
            trace: Trace to render (uses current_trace if None)
            
        Returns:
            Human-readable summary string
        """
        if trace is None:
            trace = self.current_trace
        if not trace:
            return "No trace available"
        
        # Count spans by type and status
        type_counts = {}
        status_counts = {}
        total_duration = 0.0
        
        for span in trace.spans:
            type_counts[span.span_type.value] = type_counts.get(span.span_type.value, 0) + 1
            status_counts[span.status.value] = status_counts.get(span.status.value, 0) + 1
            if span.duration_ms:
                total_duration += span.duration_ms
        
        lines = []
        lines.append("=" * 80)
        lines.append(f"TRACE SUMMARY: {trace.query}")
        lines.append("=" * 80)
        lines.append(f"Trace ID: {trace.trace_id}")
        lines.append(f"Status: {trace.status.value.upper()}")
        lines.append(f"Total Duration: {trace.total_duration_ms:.2f}ms" if trace.total_duration_ms else "Duration: N/A")
        lines.append(f"Total Spans: {len(trace.spans)}")
        lines.append("")
        
        lines.append("Spans by Type:")
        for span_type, count in sorted(type_counts.items()):
            lines.append(f"  - {span_type}: {count}")
        
        lines.append("")
        lines.append("Spans by Status:")
        for status, count in sorted(status_counts.items()):
            icon = "✅" if status == "success" else "❌" if status == "error" else "⏳"
            lines.append(f"  {icon} {status}: {count}")
        
        if self.langsmith_enabled:
            project = os.getenv("LANGCHAIN_PROJECT", "default")
            lines.append("")
            lines.append(f"🔍 LangSmith Project: {project}")
            lines.append(f"   View trace at: https://smith.langchain.com/o/{project}/traces/{trace.trace_id}")
        
        lines.append("=" * 80)
        return "\n".join(lines)
    
    def save_trace(self, filepath: str, trace: Optional[ExecutionTrace] = None) -> None:
        """Save trace to JSON file.
        
        Args:
            filepath: Path to save trace
            trace: Trace to save (uses current_trace if None)
        """
        if trace is None:
            trace = self.current_trace
        if not trace:
            raise ValueError("No trace to save")
        
        with open(filepath, 'w') as f:
            json.dump(trace.to_dict(), f, indent=2)
    
    def load_trace(self, filepath: str) -> ExecutionTrace:
        """Load trace from JSON file.
        
        Args:
            filepath: Path to load trace from
            
        Returns:
            Loaded ExecutionTrace object
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Reconstruct trace (simplified - full reconstruction would need more logic)
        trace = ExecutionTrace(
            trace_id=data["trace_id"],
            query=data["query"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            total_duration_ms=data.get("total_duration_ms"),
            status=SpanStatus(data["status"]),
            metadata=data.get("metadata", {}),
            tags=data.get("tags", []),
        )
        
        return trace
    
    def _build_span_tree(self, trace: ExecutionTrace) -> None:
        """Build parent-child relationships in spans."""
        span_map = {span.span_id: span for span in trace.spans}
        
        for span in trace.spans:
            if span.parent_id and span.parent_id in span_map:
                parent = span_map[span.parent_id]
                if span not in parent.children:
                    parent.children.append(span)
    
    def _render_span_tree(self, span: ExecutionSpan, lines: List[str], prefix: str, is_last: bool) -> None:
        """Recursively render span tree."""
        connector = "└── " if is_last else "├── "
        status_icon = "✅" if span.status == SpanStatus.SUCCESS else "❌" if span.status == SpanStatus.ERROR else "⏳"
        
        duration_str = f" ({span.duration_ms:.2f}ms)" if span.duration_ms else ""
        lines.append(f"{prefix}{connector}{status_icon} [{span.span_type.value}] {span.name}{duration_str}")
        
        if span.error:
            error_prefix = prefix + ("    " if is_last else "│   ")
            lines.append(f"{error_prefix}⚠️  {span.error}")
        
        # Render children
        child_prefix = prefix + ("    " if is_last else "│   ")
        for i, child in enumerate(span.children):
            self._render_span_tree(child, lines, child_prefix, i == len(span.children) - 1)
    
    def _get_depth(self, span: ExecutionSpan, trace: ExecutionTrace) -> int:
        """Get depth of span in tree."""
        depth = 1
        current_id = span.parent_id
        span_map = {s.span_id: s for s in trace.spans}
        
        while current_id:
            depth += 1
            if current_id in span_map:
                current_id = span_map[current_id].parent_id
            else:
                break
        
        return depth
    
    def _format_data(self, data: Any, max_len: int = 100) -> str:
        """Format data for display with length limit."""
        if isinstance(data, dict):
            items = []
            for k, v in list(data.items())[:3]:  # Show first 3 items
                v_str = str(v)
                if len(v_str) > 50:
                    v_str = v_str[:47] + "..."
                items.append(f"{k}={v_str}")
            result = "{" + ", ".join(items)
            if len(data) > 3:
                result += f", ... +{len(data)-3} more"
            result += "}"
            return result
        
        data_str = str(data)
        if len(data_str) > max_len:
            return data_str[:max_len-3] + "..."
        return data_str


# Global instance for easy access
_visualizer = TraceVisualizer()


def get_visualizer() -> TraceVisualizer:
    """Get the global trace visualizer instance."""
    return _visualizer


def start_trace(query: str, trace_id: Optional[str] = None) -> ExecutionTrace:
    """Start a new execution trace."""
    return _visualizer.start_trace(query, trace_id)


def end_trace(status: SpanStatus = SpanStatus.SUCCESS) -> Optional[ExecutionTrace]:
    """End the current trace."""
    return _visualizer.end_trace(status)


def add_span(span_type: SpanType, name: str, **kwargs) -> ExecutionSpan:
    """Add a span to the current trace."""
    return _visualizer.add_span(span_type, name, **kwargs)


def end_span(span: ExecutionSpan, **kwargs) -> ExecutionSpan:
    """End a span."""
    return _visualizer.end_span(span, **kwargs)


# Demo/test code
if __name__ == "__main__":
    print("=== Trace Visualization Demo ===\n")
    
    # Create a sample trace
    visualizer = TraceVisualizer(langsmith_enabled=True)
    trace = visualizer.start_trace("What are the latest developments in AI regulation?")
    
    # Simulate agent execution
    agent_span = visualizer.add_span(
        SpanType.AGENT, 
        "NewsAnalysisAgent",
        inputs={"query": "AI regulation"}
    )
    
    # Tool call 1
    search_span = visualizer.add_span(
        SpanType.TOOL,
        "ValyuSearch",
        parent_id=agent_span.span_id,
        inputs={"query": "AI regulation", "max_results": 5}
    )
    visualizer.end_span(
        search_span,
        outputs={"articles": 5, "cost_usd": 0.0075}
    )
    
    # LLM call
    llm_span = visualizer.add_span(
        SpanType.LLM,
        "Claude-3.5-Sonnet",
        parent_id=agent_span.span_id,
        inputs={"messages": "Analyze these articles..."}
    )
    visualizer.end_span(
        llm_span,
        outputs={"response": "Analysis of AI regulation coverage..."}
    )
    
    # Tool call 2 with error
    bias_span = visualizer.add_span(
        SpanType.TOOL,
        "BiasDetector",
        parent_id=agent_span.span_id,
        inputs={"articles": 5}
    )
    visualizer.end_span(
        bias_span,
        status=SpanStatus.ERROR,
        error="API timeout after 30s"
    )
    
    # Complete agent
    visualizer.end_span(
        agent_span,
        outputs={"analysis": "Comprehensive bias analysis..."}
    )
    
    # End trace
    visualizer.end_trace(status=SpanStatus.SUCCESS)
    
    # Render different views
    print("\n" + visualizer.render_summary())
    print("\n" + visualizer.render_timeline())
    print("\n" + visualizer.render_tree())
    
    # Save trace
    output_file = "demo_trace.json"
    visualizer.save_trace(output_file)
    print(f"\n✅ Trace saved to: {output_file}")
