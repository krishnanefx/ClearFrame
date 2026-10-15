#!/usr/bin/env python3
"""
Reasoning Explainer for Track B (Glass Box - Observability)

This module translates complex agent reasoning chains into clear, natural language
explanations suitable for non-technical users (Grandma-friendly).

Key features:
- Converts agent thought process into step-by-step narrative
- Explains tool choices and their purposes
- Translates technical errors into plain English
- Provides context for why the agent made specific decisions
- Highlights confidence levels and uncertainties
"""

import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class ExplanationLevel(Enum):
    """Complexity level for explanations."""
    TECHNICAL = "technical"  # For developers/engineers
    SIMPLE = "simple"  # For general users
    GRANDMA = "grandma"  # For non-technical users (elderly, children)


@dataclass
class ReasoningStep:
    """A single step in the agent's reasoning process."""
    step_number: int
    action: str  # What the agent did
    purpose: str  # Why it did it
    tool_used: Optional[str] = None
    result_summary: Optional[str] = None
    confidence: Optional[str] = None  # "high", "medium", "low"
    explanation: str = ""  # Human-friendly explanation


@dataclass
class ReasoningChain:
    """Complete chain of reasoning for an agent execution."""
    query: str
    steps: List[ReasoningStep] = field(default_factory=list)
    final_answer: str = ""
    confidence_overall: str = "medium"
    explanation_level: ExplanationLevel = ExplanationLevel.SIMPLE


class ReasoningExplainer:
    """Translate agent reasoning into human-friendly explanations."""
    
    def __init__(self, level: ExplanationLevel = ExplanationLevel.SIMPLE):
        """Initialize explainer with specified complexity level.
        
        Args:
            level: Complexity level for explanations
        """
        self.level = level
        self._build_vocabulary()
    
    def _build_vocabulary(self) -> None:
        """Build vocabulary translations for different levels."""
        # Tool name translations
        self.tool_names = {
            "ValyuSearchTool": {
                ExplanationLevel.TECHNICAL: "Valyu Search API",
                ExplanationLevel.SIMPLE: "news search engine",
                ExplanationLevel.GRANDMA: "a tool to find news articles on the internet",
            },
            "calculate_bias_score": {
                ExplanationLevel.TECHNICAL: "bias scoring algorithm",
                ExplanationLevel.SIMPLE: "bias detector",
                ExplanationLevel.GRANDMA: "a checker to see if the article is fair or one-sided",
            },
            "check_source_credibility": {
                ExplanationLevel.TECHNICAL: "source credibility validator",
                ExplanationLevel.SIMPLE: "credibility checker",
                ExplanationLevel.GRANDMA: "a tool to check if the news source is trustworthy",
            },
            "detect_corruption_indicators": {
                ExplanationLevel.TECHNICAL: "corruption pattern detector",
                ExplanationLevel.SIMPLE: "corruption detector",
                ExplanationLevel.GRANDMA: "a tool to look for signs of dishonest behavior",
            },
            "fact_check_claim": {
                ExplanationLevel.TECHNICAL: "fact verification API",
                ExplanationLevel.SIMPLE: "fact checker",
                ExplanationLevel.GRANDMA: "a tool to verify if something is true or false",
            },
        }
        
        # Action translations
        self.action_templates = {
            "search": {
                ExplanationLevel.TECHNICAL: "Executed search query: {query}",
                ExplanationLevel.SIMPLE: "Searched for news about: {query}",
                ExplanationLevel.GRANDMA: "I looked for news articles about {query}",
            },
            "analyze": {
                ExplanationLevel.TECHNICAL: "Performed bias analysis on {count} articles",
                ExplanationLevel.SIMPLE: "Analyzed {count} articles for bias",
                ExplanationLevel.GRANDMA: "I checked {count} news stories to see if they were fair",
            },
            "compare": {
                ExplanationLevel.TECHNICAL: "Cross-referenced narratives across sources",
                ExplanationLevel.SIMPLE: "Compared how different sources tell the story",
                ExplanationLevel.GRANDMA: "I compared how different newspapers described what happened",
            },
            "verify": {
                ExplanationLevel.TECHNICAL: "Validated claims via fact-checking API",
                ExplanationLevel.SIMPLE: "Checked if the claims are true",
                ExplanationLevel.GRANDMA: "I checked if what they said was actually true",
            },
        }
        
        # Error translations
        self.error_explanations = {
            "rate_limit": {
                ExplanationLevel.TECHNICAL: "API rate limit exceeded - too many requests per minute",
                ExplanationLevel.SIMPLE: "Made too many requests too quickly - need to slow down",
                ExplanationLevel.GRANDMA: "I was asking for information too fast, so I need to wait a bit",
            },
            "timeout": {
                ExplanationLevel.TECHNICAL: "Request timeout - response took longer than 30s threshold",
                ExplanationLevel.SIMPLE: "The search took too long and timed out",
                ExplanationLevel.GRANDMA: "It took too long to find the information, so I had to stop waiting",
            },
            "authentication": {
                ExplanationLevel.TECHNICAL: "Authentication failure - invalid API credentials",
                ExplanationLevel.SIMPLE: "Couldn't log in - wrong password or key",
                ExplanationLevel.GRANDMA: "I couldn't get permission to use the tool because the password was wrong",
            },
            "parsing": {
                ExplanationLevel.TECHNICAL: "JSON parsing error - malformed response structure",
                ExplanationLevel.SIMPLE: "Received badly formatted data that couldn't be read",
                ExplanationLevel.GRANDMA: "The information came back in a confusing format that I couldn't understand",
            },
        }
    
    def explain_chain(self, 
                     query: str,
                     steps: List[Dict[str, Any]],
                     final_answer: str = "") -> ReasoningChain:
        """Create a human-friendly explanation of the reasoning chain.
        
        Args:
            query: The original user query
            steps: List of reasoning steps (dicts with action, tool, result, etc.)
            final_answer: The final answer/output
            
        Returns:
            ReasoningChain with human-friendly explanations
        """
        chain = ReasoningChain(
            query=query,
            final_answer=final_answer,
            explanation_level=self.level,
        )
        
        for i, step_data in enumerate(steps, 1):
            step = self._explain_step(i, step_data)
            chain.steps.append(step)
        
        # Calculate overall confidence
        chain.confidence_overall = self._calculate_overall_confidence(chain.steps)
        
        return chain
    
    def _explain_step(self, step_num: int, step_data: Dict[str, Any]) -> ReasoningStep:
        """Explain a single reasoning step.
        
        Args:
            step_num: Step number
            step_data: Dictionary containing step information
            
        Returns:
            ReasoningStep with human-friendly explanation
        """
        action = step_data.get("action", "unknown")
        tool_used = step_data.get("tool")
        result = step_data.get("result")
        error = step_data.get("error")
        
        # Determine purpose
        purpose = self._determine_purpose(action, tool_used, step_data)
        
        # Generate explanation
        explanation = self._generate_step_explanation(
            action, tool_used, result, error, step_data
        )
        
        # Estimate confidence
        confidence = self._estimate_confidence(result, error)
        
        # Result summary
        result_summary = self._summarize_result(result, error)
        
        return ReasoningStep(
            step_number=step_num,
            action=action,
            purpose=purpose,
            tool_used=tool_used,
            result_summary=result_summary,
            confidence=confidence,
            explanation=explanation,
        )
    
    def _determine_purpose(self, 
                          action: str,
                          tool: Optional[str],
                          step_data: Dict[str, Any]) -> str:
        """Determine the purpose of a step."""
        if self.level == ExplanationLevel.GRANDMA:
            purposes = {
                "search": "to find relevant news articles",
                "analyze": "to check if the news is fair and balanced",
                "compare": "to see if different sources agree",
                "verify": "to make sure the facts are correct",
                "summarize": "to put it all together in a simple way",
            }
        elif self.level == ExplanationLevel.SIMPLE:
            purposes = {
                "search": "to gather news articles",
                "analyze": "to detect bias and credibility",
                "compare": "to cross-reference sources",
                "verify": "to fact-check claims",
                "summarize": "to synthesize findings",
            }
        else:  # TECHNICAL
            purposes = {
                "search": "to retrieve relevant documents",
                "analyze": "to perform bias quantification",
                "compare": "to execute multi-source validation",
                "verify": "to validate factual accuracy",
                "summarize": "to aggregate analysis results",
            }
        
        # Match action to purpose
        for key in purposes:
            if key in action.lower():
                return purposes[key]
        
        # Fallback based on tool
        if tool:
            if "search" in tool.lower():
                return purposes["search"]
            elif "bias" in tool.lower() or "credibility" in tool.lower():
                return purposes["analyze"]
            elif "fact" in tool.lower():
                return purposes["verify"]
        
        return "to process the information"
    
    def _generate_step_explanation(self,
                                   action: str,
                                   tool: Optional[str],
                                   result: Any,
                                   error: Optional[str],
                                   step_data: Dict[str, Any]) -> str:
        """Generate human-friendly explanation for a step."""
        parts = []
        
        # Explain the action
        if self.level == ExplanationLevel.GRANDMA:
            if "search" in action.lower():
                parts.append("I went looking for news articles")
            elif "analyze" in action.lower():
                parts.append("I carefully read through the articles")
            elif "compare" in action.lower():
                parts.append("I compared what different sources said")
            elif "verify" in action.lower():
                parts.append("I checked if the facts were correct")
            else:
                parts.append("I processed the information")
        elif self.level == ExplanationLevel.SIMPLE:
            if "search" in action.lower():
                parts.append("Searched for relevant articles")
            elif "analyze" in action.lower():
                parts.append("Analyzed the articles for bias")
            elif "compare" in action.lower():
                parts.append("Compared narratives across sources")
            elif "verify" in action.lower():
                parts.append("Fact-checked the claims")
            else:
                parts.append(f"Performed {action}")
        else:  # TECHNICAL
            parts.append(f"Executed {action}")
        
        # Explain the tool used
        if tool and tool in self.tool_names:
            tool_explanation = self.tool_names[tool][self.level]
            if self.level == ExplanationLevel.GRANDMA:
                parts.append(f"using {tool_explanation}")
            else:
                parts.append(f"via {tool_explanation}")
        
        # Explain the result or error
        if error:
            error_type = self._categorize_error(error)
            if error_type in self.error_explanations:
                error_text = self.error_explanations[error_type][self.level]
                if self.level == ExplanationLevel.GRANDMA:
                    parts.append(f"but {error_text}")
                else:
                    parts.append(f"Error: {error_text}")
            else:
                if self.level == ExplanationLevel.GRANDMA:
                    parts.append("but something went wrong")
                else:
                    parts.append(f"Error: {error}")
        elif result:
            result_explanation = self._explain_result(result)
            parts.append(result_explanation)
        
        return " ".join(parts)
    
    def _explain_result(self, result: Any) -> str:
        """Explain the result of a step."""
        if isinstance(result, dict):
            if "articles" in result or "results" in result:
                count = len(result.get("articles", result.get("results", [])))
                if self.level == ExplanationLevel.GRANDMA:
                    return f"and found {count} articles"
                else:
                    return f"Retrieved {count} articles"
            
            if "bias_score" in result:
                score = result["bias_score"]
                if self.level == ExplanationLevel.GRANDMA:
                    if abs(score) < 10:
                        return "and it seems pretty fair"
                    elif score > 0:
                        return "and it leans a bit to one side"
                    else:
                        return "and it leans to the other side"
                else:
                    return f"Bias score: {score}"
            
            if "credibility" in result:
                cred = result["credibility"]
                if self.level == ExplanationLevel.GRANDMA:
                    if cred == "High":
                        return "and it's a trustworthy source"
                    elif cred == "Medium":
                        return "and it's somewhat trustworthy"
                    else:
                        return "and you should be careful about trusting it"
                else:
                    return f"Credibility: {cred}"
        
        # Fallback
        if self.level == ExplanationLevel.GRANDMA:
            return "and got some useful information"
        else:
            return "Completed successfully"
    
    def _categorize_error(self, error: str) -> str:
        """Categorize error type."""
        error_lower = error.lower()
        if "rate limit" in error_lower or "429" in error_lower:
            return "rate_limit"
        elif "timeout" in error_lower or "timed out" in error_lower:
            return "timeout"
        elif "auth" in error_lower or "unauthorized" in error_lower or "401" in error_lower:
            return "authentication"
        elif "json" in error_lower or "parse" in error_lower:
            return "parsing"
        return "unknown"
    
    def _summarize_result(self, result: Any, error: Optional[str]) -> Optional[str]:
        """Create a brief summary of the result."""
        if error:
            return f"Failed: {error[:100]}"
        
        if isinstance(result, dict):
            if "articles" in result:
                return f"{len(result['articles'])} articles found"
            elif "bias_score" in result:
                return f"Bias: {result['bias_score']}"
            elif "credibility" in result:
                return f"Credibility: {result['credibility']}"
        
        return "Success"
    
    def _estimate_confidence(self, result: Any, error: Optional[str]) -> str:
        """Estimate confidence level for a step."""
        if error:
            return "low"
        
        if isinstance(result, dict):
            # High confidence indicators
            if result.get("credibility") == "High":
                return "high"
            if result.get("fact_checked") is True:
                return "high"
            
            # Medium confidence indicators
            if "articles" in result and len(result["articles"]) >= 5:
                return "high"
            elif "articles" in result and len(result["articles"]) >= 2:
                return "medium"
        
        return "medium"
    
    def _calculate_overall_confidence(self, steps: List[ReasoningStep]) -> str:
        """Calculate overall confidence from step confidences."""
        if not steps:
            return "low"
        
        confidence_scores = {"high": 3, "medium": 2, "low": 1}
        scores = [confidence_scores.get(step.confidence, 2) for step in steps]
        avg_score = sum(scores) / len(scores)
        
        if avg_score >= 2.5:
            return "high"
        elif avg_score >= 1.5:
            return "medium"
        else:
            return "low"
    
    def render_explanation(self, chain: ReasoningChain) -> str:
        """Render the reasoning chain as human-friendly text.
        
        Args:
            chain: ReasoningChain to render
            
        Returns:
            Human-readable explanation string
        """
        lines = []
        
        # Header
        if self.level == ExplanationLevel.GRANDMA:
            lines.append("=" * 80)
            lines.append("📖 HOW I FOUND YOUR ANSWER")
            lines.append("=" * 80)
            lines.append(f"\nYou asked me: \"{chain.query}\"")
            lines.append(f"\nHere's what I did to find the answer:\n")
        else:
            lines.append("=" * 80)
            lines.append("REASONING CHAIN EXPLANATION")
            lines.append("=" * 80)
            lines.append(f"Query: {chain.query}")
            lines.append(f"Confidence: {chain.confidence_overall.upper()}\n")
        
        # Steps
        for step in chain.steps:
            if self.level == ExplanationLevel.GRANDMA:
                lines.append(f"Step {step.step_number}: {step.explanation}")
                if step.confidence == "low":
                    lines.append("   (I'm not very sure about this part)")
                lines.append("")
            else:
                confidence_icon = "✅" if step.confidence == "high" else "⚠️" if step.confidence == "low" else "ℹ️"
                lines.append(f"{step.step_number}. {confidence_icon} {step.explanation}")
                if step.result_summary:
                    lines.append(f"   → {step.result_summary}")
                lines.append("")
        
        # Final answer
        if chain.final_answer:
            if self.level == ExplanationLevel.GRANDMA:
                lines.append("=" * 80)
                lines.append("MY ANSWER:")
                lines.append("=" * 80)
                lines.append(chain.final_answer)
                lines.append("")
                
                # Confidence explanation
                if chain.confidence_overall == "high":
                    lines.append("I'm pretty confident about this answer! ✅")
                elif chain.confidence_overall == "medium":
                    lines.append("I'm reasonably sure about this, but there's some uncertainty. ⚠️")
                else:
                    lines.append("I'm not very confident - you might want to check other sources. ❓")
            else:
                lines.append("=" * 80)
                lines.append("FINAL ANSWER:")
                lines.append("=" * 80)
                lines.append(chain.final_answer)
        
        lines.append("\n" + "=" * 80)
        return "\n".join(lines)
    
    def render_simple_timeline(self, chain: ReasoningChain) -> str:
        """Render a simple timeline view of the reasoning.
        
        Args:
            chain: ReasoningChain to render
            
        Returns:
            Timeline string
        """
        lines = []
        lines.append("\n📅 TIMELINE OF REASONING:\n")
        
        for step in chain.steps:
            status = "✅" if step.confidence == "high" else "⚠️" if step.confidence == "low" else "→"
            lines.append(f"{status} Step {step.step_number}: {step.action}")
            lines.append(f"   {step.purpose}")
            if step.result_summary:
                lines.append(f"   Result: {step.result_summary}")
            lines.append("")
        
        return "\n".join(lines)


# Demo/test code
if __name__ == "__main__":
    print("=== Reasoning Explainer Demo ===\n")
    
    # Sample reasoning chain
    steps = [
        {
            "action": "search",
            "tool": "ValyuSearchTool",
            "result": {"articles": [{"title": "Article 1"}, {"title": "Article 2"}, {"title": "Article 3"}]},
        },
        {
            "action": "analyze",
            "tool": "calculate_bias_score",
            "result": {"bias_score": 15, "credibility": "High"},
        },
        {
            "action": "compare",
            "tool": None,
            "result": {"narratives": 3, "agreement": "high"},
        },
        {
            "action": "verify",
            "tool": "fact_check_claim",
            "error": "Rate limit exceeded: 429 Too Many Requests",
        },
    ]
    
    query = "What are the latest developments in AI regulation?"
    final_answer = "Recent AI regulation efforts show increased focus on transparency and safety standards."
    
    # Test each explanation level
    for level in [ExplanationLevel.GRANDMA, ExplanationLevel.SIMPLE, ExplanationLevel.TECHNICAL]:
        print(f"\n{'='*80}")
        print(f"EXPLANATION LEVEL: {level.value.upper()}")
        print(f"{'='*80}")
        
        explainer = ReasoningExplainer(level=level)
        chain = explainer.explain_chain(query, steps, final_answer)
        
        print(explainer.render_explanation(chain))
        
        if level == ExplanationLevel.SIMPLE:
            print(explainer.render_simple_timeline(chain))
