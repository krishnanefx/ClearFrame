#!/usr/bin/env python3
"""
Failure Attribution Analysis for Track B (Glass Box - Observability)

This module analyzes failed agent executions to identify root causes and provide
actionable debugging information. Categorizes failures by type:
- LLM errors (rate limits, token limits, parsing failures)
- API errors (timeouts, connection issues, authentication)
- Tool errors (invalid inputs, missing data, external service failures)
- Logic errors (infinite loops, stuck states, invalid reasoning)

Provides failure attribution with stack traces, error context, and remediation suggestions.
"""

import re
import json
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone


class FailureCategory(Enum):
    """Categories of agent failures."""
    LLM_ERROR = "llm_error"
    API_ERROR = "api_error"
    TOOL_ERROR = "tool_error"
    PARSING_ERROR = "parsing_error"
    AUTHENTICATION_ERROR = "authentication_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    TIMEOUT_ERROR = "timeout_error"
    VALIDATION_ERROR = "validation_error"
    LOGIC_ERROR = "logic_error"
    UNKNOWN_ERROR = "unknown"


class FailureSeverity(Enum):
    """Severity levels for failures."""
    CRITICAL = "critical"  # Complete agent failure, no output
    HIGH = "high"  # Major feature broken, degraded output
    MEDIUM = "medium"  # Minor issue, partial success
    LOW = "low"  # Recoverable error, minimal impact


@dataclass
class FailureContext:
    """Context information for a failure."""
    timestamp: datetime
    query: str
    step_name: str
    step_index: int
    inputs: Dict[str, Any] = field(default_factory=dict)
    partial_outputs: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    stack_trace: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FailureAnalysis:
    """Complete analysis of a failure."""
    failure_id: str
    category: FailureCategory
    severity: FailureSeverity
    context: FailureContext
    root_cause: str
    contributing_factors: List[str] = field(default_factory=list)
    impact_assessment: str = ""
    remediation_steps: List[str] = field(default_factory=list)
    similar_failures: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "failure_id": self.failure_id,
            "category": self.category.value,
            "severity": self.severity.value,
            "context": {
                "timestamp": self.context.timestamp.isoformat(),
                "query": self.context.query,
                "step_name": self.context.step_name,
                "step_index": self.context.step_index,
                "inputs": self.context.inputs,
                "partial_outputs": self.context.partial_outputs,
                "error_message": self.context.error_message,
                "stack_trace": self.context.stack_trace,
                "metadata": self.context.metadata,
            },
            "root_cause": self.root_cause,
            "contributing_factors": self.contributing_factors,
            "impact_assessment": self.impact_assessment,
            "remediation_steps": self.remediation_steps,
            "similar_failures": self.similar_failures,
        }


class FailureAnalyzer:
    """Analyze agent failures and provide root cause analysis."""
    
    def __init__(self):
        """Initialize failure analyzer with pattern database."""
        self.failure_history: List[FailureAnalysis] = []
        self._build_pattern_database()
    
    def _build_pattern_database(self) -> None:
        """Build database of known failure patterns."""
        self.patterns = {
            # LLM Errors
            "rate_limit": {
                "regex": r"rate\s*limit|429|too\s*many\s*requests",
                "category": FailureCategory.RATE_LIMIT_ERROR,
                "severity": FailureSeverity.HIGH,
                "remediation": [
                    "Implement exponential backoff retry logic",
                    "Check API quota and limits",
                    "Reduce request frequency",
                    "Consider upgrading API tier",
                ]
            },
            "token_limit": {
                "regex": r"token\s*limit|context\s*length|maximum\s*context|too\s*long",
                "category": FailureCategory.LLM_ERROR,
                "severity": FailureSeverity.HIGH,
                "remediation": [
                    "Reduce input text length (truncate articles)",
                    "Use text summarization before analysis",
                    "Switch to model with larger context window",
                    "Implement chunking strategy for long inputs",
                ]
            },
            "parsing_error": {
                "regex": r"json.*error|parse.*error|invalid.*json|expected.*{|}",
                "category": FailureCategory.PARSING_ERROR,
                "severity": FailureSeverity.MEDIUM,
                "remediation": [
                    "Add JSON validation before parsing",
                    "Implement retry with clearer instructions",
                    "Use structured output schemas (Pydantic)",
                    "Add example JSON in prompt",
                ]
            },
            
            # API Errors
            "timeout": {
                "regex": r"timeout|timed\s*out|deadline\s*exceeded",
                "category": FailureCategory.TIMEOUT_ERROR,
                "severity": FailureSeverity.HIGH,
                "remediation": [
                    "Increase timeout threshold",
                    "Implement request chunking",
                    "Check network connectivity",
                    "Use faster model variant (e.g., Haiku)",
                ]
            },
            "authentication": {
                "regex": r"auth.*failed|unauthorized|401|403|invalid.*key|api.*key",
                "category": FailureCategory.AUTHENTICATION_ERROR,
                "severity": FailureSeverity.CRITICAL,
                "remediation": [
                    "Verify API key is correct",
                    "Check environment variables loaded",
                    "Confirm API key has required permissions",
                    "Regenerate API key if expired",
                ]
            },
            "connection": {
                "regex": r"connection.*error|network.*error|host.*unreachable|dns",
                "category": FailureCategory.API_ERROR,
                "severity": FailureSeverity.HIGH,
                "remediation": [
                    "Check internet connectivity",
                    "Verify API endpoint URL",
                    "Check firewall/proxy settings",
                    "Implement retry with exponential backoff",
                ]
            },
            
            # Tool Errors
            "invalid_input": {
                "regex": r"invalid.*input|validation.*error|missing.*required|field.*required",
                "category": FailureCategory.VALIDATION_ERROR,
                "severity": FailureSeverity.MEDIUM,
                "remediation": [
                    "Add input validation before tool call",
                    "Provide clearer tool descriptions",
                    "Use Pydantic schemas for type safety",
                    "Add examples in tool documentation",
                ]
            },
            "tool_not_found": {
                "regex": r"tool.*not.*found|unknown.*tool|no.*such.*tool",
                "category": FailureCategory.TOOL_ERROR,
                "severity": FailureSeverity.HIGH,
                "remediation": [
                    "Verify tool is registered with agent",
                    "Check tool name spelling",
                    "Confirm tool import succeeded",
                    "Review agent tool list configuration",
                ]
            },
        }
    
    def analyze_failure(self, 
                       error: Exception,
                       query: str,
                       step_name: str = "unknown",
                       step_index: int = 0,
                       inputs: Optional[Dict[str, Any]] = None,
                       partial_outputs: Optional[Dict[str, Any]] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> FailureAnalysis:
        """Analyze a failure and determine root cause.
        
        Args:
            error: The exception that occurred
            query: User query being processed
            step_name: Name of the step that failed
            step_index: Index of the step in execution
            inputs: Inputs to the failing step
            partial_outputs: Any partial outputs before failure
            metadata: Additional context
            
        Returns:
            FailureAnalysis object with root cause and remediation
        """
        # Build context
        context = FailureContext(
            timestamp=datetime.now(timezone.utc),
            query=query,
            step_name=step_name,
            step_index=step_index,
            inputs=inputs or {},
            partial_outputs=partial_outputs or {},
            error_message=str(error),
            stack_trace=self._get_stack_trace(error),
            metadata=metadata or {},
        )
        
        # Categorize failure
        category, severity, matched_pattern = self._categorize_failure(error)
        
        # Generate root cause analysis
        root_cause = self._determine_root_cause(error, context, matched_pattern)
        
        # Get contributing factors
        contributing_factors = self._identify_contributing_factors(error, context)
        
        # Assess impact
        impact = self._assess_impact(category, severity, context)
        
        # Get remediation steps
        remediation = self._get_remediation_steps(matched_pattern, category)
        
        # Find similar failures
        similar = self._find_similar_failures(category, error)
        
        # Create analysis
        failure_id = f"failure_{datetime.now(timezone.utc).timestamp()}"
        analysis = FailureAnalysis(
            failure_id=failure_id,
            category=category,
            severity=severity,
            context=context,
            root_cause=root_cause,
            contributing_factors=contributing_factors,
            impact_assessment=impact,
            remediation_steps=remediation,
            similar_failures=similar,
        )
        
        # Store in history
        self.failure_history.append(analysis)
        
        return analysis
    
    def _categorize_failure(self, error: Exception) -> Tuple[FailureCategory, FailureSeverity, Optional[str]]:
        """Categorize failure by matching error patterns.
        
        Returns:
            Tuple of (category, severity, matched_pattern_name)
        """
        error_text = str(error).lower()
        error_type = type(error).__name__.lower()
        
        # Match against known patterns
        for pattern_name, pattern_data in self.patterns.items():
            if re.search(pattern_data["regex"], error_text, re.IGNORECASE):
                return (
                    pattern_data["category"],
                    pattern_data["severity"],
                    pattern_name
                )
        
        # Fallback based on exception type
        if "timeout" in error_type:
            return FailureCategory.TIMEOUT_ERROR, FailureSeverity.HIGH, None
        elif "auth" in error_type or "permission" in error_type:
            return FailureCategory.AUTHENTICATION_ERROR, FailureSeverity.CRITICAL, None
        elif "parse" in error_type or "json" in error_type:
            return FailureCategory.PARSING_ERROR, FailureSeverity.MEDIUM, None
        
        return FailureCategory.UNKNOWN_ERROR, FailureSeverity.MEDIUM, None
    
    def _determine_root_cause(self, 
                             error: Exception, 
                             context: FailureContext,
                             matched_pattern: Optional[str]) -> str:
        """Determine root cause explanation."""
        if matched_pattern and matched_pattern in self.patterns:
            pattern = self.patterns[matched_pattern]
            base_cause = f"{pattern['category'].value.replace('_', ' ').title()}"
        else:
            base_cause = f"{type(error).__name__}"
        
        # Add context-specific details
        details = []
        if "rate limit" in context.error_message.lower():
            details.append("API rate limit exceeded")
        if "token" in context.error_message.lower() and "limit" in context.error_message.lower():
            details.append("LLM context window exceeded")
        if "timeout" in context.error_message.lower():
            details.append(f"Request timeout in step '{context.step_name}'")
        if "key" in context.error_message.lower() and "invalid" in context.error_message.lower():
            details.append("Invalid or missing API credentials")
        
        if details:
            return f"{base_cause}: {'; '.join(details)}"
        else:
            return f"{base_cause} in {context.step_name}"
    
    def _identify_contributing_factors(self, 
                                      error: Exception,
                                      context: FailureContext) -> List[str]:
        """Identify factors that may have contributed to failure."""
        factors = []
        
        # Check input size
        if context.inputs:
            input_str = json.dumps(context.inputs)
            if len(input_str) > 10000:
                factors.append(f"Large input size ({len(input_str)} chars) may cause slowness or failures")
        
        # Check for missing required fields
        error_msg_lower = context.error_message.lower()
        if "missing" in error_msg_lower or "required" in error_msg_lower:
            factors.append("Missing required input fields or parameters")
        
        # Check step position
        if context.step_index > 10:
            factors.append(f"Late failure (step {context.step_index}) suggests cumulative issue")
        
        # Check for nested errors
        if "caused by" in error_msg_lower or "due to" in error_msg_lower:
            factors.append("Cascading failure from earlier error")
        
        return factors
    
    def _assess_impact(self, 
                      category: FailureCategory,
                      severity: FailureSeverity,
                      context: FailureContext) -> str:
        """Assess the impact of the failure."""
        impacts = []
        
        # Severity-based impact
        if severity == FailureSeverity.CRITICAL:
            impacts.append("Complete agent failure - no results returned to user")
        elif severity == FailureSeverity.HIGH:
            impacts.append("Major functionality broken - significant degradation")
        elif severity == FailureSeverity.MEDIUM:
            impacts.append("Partial success - some features unavailable")
        else:
            impacts.append("Minor impact - most functionality intact")
        
        # Category-specific impacts
        if category == FailureCategory.RATE_LIMIT_ERROR:
            impacts.append("Temporary issue - may self-resolve after cooldown period")
        elif category == FailureCategory.AUTHENTICATION_ERROR:
            impacts.append("Permanent issue - requires configuration fix")
        elif category == FailureCategory.PARSING_ERROR:
            impacts.append("Intermittent issue - may succeed on retry")
        
        # Check for partial outputs
        if context.partial_outputs:
            impacts.append(f"Partial data available: {list(context.partial_outputs.keys())}")
        
        return " | ".join(impacts)
    
    def _get_remediation_steps(self, 
                               matched_pattern: Optional[str],
                               category: FailureCategory) -> List[str]:
        """Get remediation steps for the failure."""
        # Use pattern-specific remediation if available
        if matched_pattern and matched_pattern in self.patterns:
            return self.patterns[matched_pattern]["remediation"]
        
        # Fallback to category-based remediation
        generic_remediation = {
            FailureCategory.LLM_ERROR: [
                "Check LLM service status",
                "Verify model name and parameters",
                "Review prompt complexity",
                "Consider using different model",
            ],
            FailureCategory.API_ERROR: [
                "Verify network connectivity",
                "Check API endpoint availability",
                "Review firewall/proxy settings",
                "Implement retry logic with backoff",
            ],
            FailureCategory.TOOL_ERROR: [
                "Verify tool configuration",
                "Check tool input validation",
                "Review tool dependencies",
                "Test tool in isolation",
            ],
            FailureCategory.PARSING_ERROR: [
                "Add strict JSON validation",
                "Use structured output schemas",
                "Provide clearer format examples",
                "Implement fallback parsers",
            ],
            FailureCategory.AUTHENTICATION_ERROR: [
                "Verify API credentials",
                "Check environment variable loading",
                "Confirm API key permissions",
                "Test authentication separately",
            ],
        }
        
        return generic_remediation.get(category, [
            "Review error logs carefully",
            "Check system configuration",
            "Test with minimal example",
            "Contact support if issue persists",
        ])
    
    def _find_similar_failures(self, 
                              category: FailureCategory,
                              error: Exception) -> List[str]:
        """Find similar historical failures."""
        similar = []
        error_text = str(error).lower()
        
        for past_failure in self.failure_history[-10:]:  # Check last 10
            if past_failure.category == category:
                # Calculate similarity score
                past_error = past_failure.context.error_message.lower()
                common_words = set(error_text.split()) & set(past_error.split())
                if len(common_words) > 3:
                    similar.append(past_failure.failure_id)
        
        return similar
    
    def _get_stack_trace(self, error: Exception) -> str:
        """Extract stack trace from exception."""
        import traceback
        return ''.join(traceback.format_exception(type(error), error, error.__traceback__))
    
    def render_failure_report(self, analysis: FailureAnalysis) -> str:
        """Render human-readable failure report.
        
        Args:
            analysis: FailureAnalysis object
            
        Returns:
            Formatted report string
        """
        lines = []
        lines.append("=" * 80)
        lines.append("🚨 FAILURE ANALYSIS REPORT")
        lines.append("=" * 80)
        lines.append(f"Failure ID: {analysis.failure_id}")
        lines.append(f"Timestamp: {analysis.context.timestamp.isoformat()}")
        lines.append(f"Query: {analysis.context.query}")
        lines.append(f"Failed Step: {analysis.context.step_name} (step {analysis.context.step_index})")
        lines.append("")
        
        # Category and Severity
        severity_icon = {
            FailureSeverity.CRITICAL: "🔴",
            FailureSeverity.HIGH: "🟠",
            FailureSeverity.MEDIUM: "🟡",
            FailureSeverity.LOW: "🟢",
        }
        lines.append(f"Category: {analysis.category.value.upper()}")
        lines.append(f"Severity: {severity_icon.get(analysis.severity, '⚪')} {analysis.severity.value.upper()}")
        lines.append("")
        
        # Root Cause
        lines.append("ROOT CAUSE:")
        lines.append(f"  {analysis.root_cause}")
        lines.append("")
        
        # Contributing Factors
        if analysis.contributing_factors:
            lines.append("CONTRIBUTING FACTORS:")
            for factor in analysis.contributing_factors:
                lines.append(f"  - {factor}")
            lines.append("")
        
        # Impact
        lines.append("IMPACT:")
        lines.append(f"  {analysis.impact_assessment}")
        lines.append("")
        
        # Error Details
        lines.append("ERROR MESSAGE:")
        lines.append(f"  {analysis.context.error_message}")
        lines.append("")
        
        # Remediation
        lines.append("RECOMMENDED ACTIONS:")
        for i, step in enumerate(analysis.remediation_steps, 1):
            lines.append(f"  {i}. {step}")
        lines.append("")
        
        # Similar Failures
        if analysis.similar_failures:
            lines.append("SIMILAR PAST FAILURES:")
            for failure_id in analysis.similar_failures:
                lines.append(f"  - {failure_id}")
            lines.append("")
        
        lines.append("=" * 80)
        return "\n".join(lines)
    
    def get_failure_statistics(self) -> Dict[str, Any]:
        """Get statistics about failure history."""
        if not self.failure_history:
            return {"total_failures": 0}
        
        category_counts = {}
        severity_counts = {}
        
        for failure in self.failure_history:
            cat = failure.category.value
            sev = failure.severity.value
            category_counts[cat] = category_counts.get(cat, 0) + 1
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        
        return {
            "total_failures": len(self.failure_history),
            "by_category": category_counts,
            "by_severity": severity_counts,
            "most_common_category": max(category_counts.items(), key=lambda x: x[1])[0],
            "most_common_severity": max(severity_counts.items(), key=lambda x: x[1])[0],
        }


# Global instance
_analyzer = FailureAnalyzer()


def get_analyzer() -> FailureAnalyzer:
    """Get the global failure analyzer instance."""
    return _analyzer


def analyze_failure(error: Exception, query: str, **kwargs) -> FailureAnalysis:
    """Analyze a failure (convenience function)."""
    return _analyzer.analyze_failure(error, query, **kwargs)


# Demo/test code
if __name__ == "__main__":
    print("=== Failure Analysis Demo ===\n")
    
    analyzer = FailureAnalyzer()
    
    # Simulate different failure types
    failures = [
        (ValueError("Rate limit exceeded: 429 Too Many Requests"), "AI regulation news"),
        (RuntimeError("Token limit exceeded: context length 8192 > 4096"), "Sudan war analysis"),
        (ConnectionError("Timeout after 30s waiting for API response"), "Climate change"),
        (KeyError("API key invalid or missing"), "Tech industry news"),
        (json.JSONDecodeError("Expecting property name", "", 0), "Corruption scandal"),
    ]
    
    for i, (error, query) in enumerate(failures, 1):
        print(f"\n{'='*80}")
        print(f"Failure {i}: {type(error).__name__}")
        print(f"{'='*80}")
        
        analysis = analyzer.analyze_failure(
            error=error,
            query=query,
            step_name=f"AnalysisStep{i}",
            step_index=i,
            inputs={"query": query, "max_results": 10},
            metadata={"model": "claude-sonnet", "version": "3.5"}
        )
        
        print(analyzer.render_failure_report(analysis))
    
    # Show statistics
    print("\n" + "="*80)
    print("FAILURE STATISTICS")
    print("="*80)
    stats = analyzer.get_failure_statistics()
    print(json.dumps(stats, indent=2))
