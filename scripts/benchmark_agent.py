import os
import time
import json
import random
from pathlib import Path
from dotenv import load_dotenv
import numpy as np
from tqdm import tqdm
from pydantic import BaseModel, Field
from typing import Dict, Any
from datasets import load_dataset, Dataset

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print("📄 Loaded configuration from .env file")
else:
    print("⚠️ No .env file found - using environment variables")

# Setup paths to import project modules
import sys
# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.utils.model_helper import get_chat_model
from src.agents.news_agent import NewsAgent

# Define response format for evaluation
class HLEResponse(BaseModel):
    """Structured response for HLE questions."""
    explanation: str = Field(description="Your reasoning")
    answer: str = Field(description="Your final answer")
    confidence: int = Field(description="Confidence 0-100", ge=0, le=100)

def simple_judge(model_answer: str, correct_answer: str) -> bool:
    """Simple exact match judge."""
    # Normalize answers
    model_ans = model_answer.strip().lower()
    correct_ans = correct_answer.strip().lower()
    
    # Check exact match
    if model_ans == correct_ans:
        return True
    
    # Check if model answer contains correct answer
    if correct_ans in model_ans:
        return True
    
    # For single letter answers (multiple choice)
    if len(correct_ans) == 1 and correct_ans in model_ans:
        return True
    
    return False

def llm_judge(
    question: str,
    model_answer: str,
    correct_answer: str,
    judge_model: str = 'claude-3-5-sonnet'
) -> tuple[bool, str, float]:
    """
    Use LLM as judge to evaluate answer correctness.
    
    Returns:
        (is_correct, explanation, confidence)
    """
    judge_llm = get_chat_model(judge_model)
    
    judge_prompt = f"""You are an expert judge evaluating AI answers on challenging academic questions.

Question: {question}

Correct Answer: {correct_answer}

Model's Answer: {model_answer}

Evaluate if the model's answer is semantically equivalent to the correct answer.
Consider:
1. Mathematical/logical equivalence
2. Semantic meaning (not just exact wording)
3. Partial credit for close answers

Respond in JSON format:
{{
    "is_correct": true/false,
    "explanation": "Brief explanation of your judgment",
    "confidence": 0-100 (how certain you are)
}}"""

    try:
        response = judge_llm.invoke(judge_prompt)
        if isinstance(response.content, str):
            judgment = json.loads(response.content)
        else:
            # Handle cases where content is not a simple string
            # This is a fallback, might need adjustment based on actual content
            judgment = {}
        
        return (
            judgment.get('is_correct', False),
            judgment.get('explanation', ''),
            judgment.get('confidence', 0)
        )
    except Exception as e:
        print(f"  Judge error: {e}")
        # Fallback to simple judge
        return (simple_judge(model_answer, correct_answer), "Fallback to exact match", 50)

if __name__ == '__main__':
    print("Benchmark script initialized.")
    print("Loading HLE dataset from Hugging Face...")
    dataset: Dataset = load_dataset('cais/hle', split='test') # type: ignore
    print(f"Loaded {len(dataset)} questions.")

    # The agent to benchmark
    agent_to_test = NewsAgent()
    # We need a structured output LLM for the benchmark
    structured_llm = agent_to_test.llm.with_structured_output(HLEResponse)

    # Select 5 random questions
    n_questions = 5
    test_questions = random.sample(list(dataset), n_questions)

    print(f"Running mini benchmark on {n_questions} questions...")
    print("Using both Simple Judge and LLM Judge (claude-3-5-sonnet)")
    print("="*70)

    results = []

    for i, q in enumerate(tqdm(test_questions, desc="Evaluating")):
        try:
            # Create prompt with instructions from the tutorial
            prompt = f"""You are answering a question from Humanity's Last Exam (HLE), a PhD-level academic benchmark.

Instructions:
- Provide your best answer based on the information given
- Do not ask for clarification or additional information
- If you're unsure, make your best educated guess
- Answer in the required format with explanation, answer, and confidence

Question:
{q['question']}""" # type: ignore
            
            # Ask the structured LLM from our agent
            response: HLEResponse = structured_llm.invoke(prompt) # type: ignore
            
            # Simple judge
            simple_correct = simple_judge(response.answer, q['answer']) # type: ignore
            
            # LLM judge
            llm_correct, judge_explanation, judge_conf = llm_judge(
                q['question'], # type: ignore
                response.answer,
                q['answer'] # type: ignore
            )
            
            results.append({
                'subject': q.get('raw_subject', 'Unknown'), # type: ignore
                'question': q['question'][:100], # type: ignore
                'model_answer': response.answer,
                'correct_answer': q['answer'], # type: ignore
                'confidence': response.confidence,
                'simple_correct': simple_correct,
                'llm_correct': llm_correct,
                'judge_explanation': judge_explanation,
                'judge_confidence': judge_conf
            })
            
        except Exception as e:
            print(f"\n  Error on question {i+1}: {e}")
            continue

    print("\nBenchmark complete!")

    # Calculate and print metrics
    simple_correct_count = sum(1 for r in results if r['simple_correct'])
    llm_correct_count = sum(1 for r in results if r['llm_correct'])

    simple_accuracy = (simple_correct_count / len(results)) * 100 if results else 0
    llm_accuracy = (llm_correct_count / len(results)) * 100 if results else 0

    avg_model_confidence = np.mean([r['confidence'] for r in results]) if results else 0
    avg_judge_confidence = np.mean([r['judge_confidence'] for r in results]) if results else 0

    by_subject: Dict[str, Dict[str, Any]] = {}
    for r in results:
        subj = r['subject']
        if subj not in by_subject:
            by_subject[subj] = {'simple': 0, 'llm': 0, 'total': 0}
        by_subject[subj]['total'] += 1
        if r['simple_correct']:
            by_subject[subj]['simple'] += 1
        if r['llm_correct']:
            by_subject[subj]['llm'] += 1

    print("="*70)
    print(" BENCHMARK RESULTS - DUAL JUDGE COMPARISON")
    print("="*70)

    print(f"\n Simple Exact Match Judge:")
    print(f"    Correct: {simple_correct_count}/{len(results)}")
    print(f"    Accuracy: {simple_accuracy:.1f}%")

    print(f"\n LLM Judge (claude-3-5-sonnet):")
    print(f"    Correct: {llm_correct_count}/{len(results)}")
    print(f"    Accuracy: {llm_accuracy:.1f}%")
    print(f"    Avg Judge Confidence: {avg_judge_confidence:.1f}%")

    print(f"\n Model Avg Confidence: {avg_model_confidence:.1f}%")

    if llm_correct_count != simple_correct_count:
        diff = llm_correct_count - simple_correct_count
        print(f"\n LLM Judge found {abs(diff)} additional correct answer(s)!" if diff > 0 else f"\n LLM Judge was stricter by {abs(diff)} answer(s)")
    
    print(f"\n By Subject:")
    for subj, stats in by_subject.items():
        simple_acc = (stats['simple'] / stats['total']) * 100 if stats['total'] > 0 else 0
        llm_acc = (stats['llm'] / stats['total']) * 100 if stats['total'] > 0 else 0
        print(f"   {subj[:30]:30s}: Simple {simple_acc:.0f}% | LLM {llm_acc:.0f}%")
    print("="*70)

    print("\n Detailed Results:\n")
    print("="*70)

    for i, r in enumerate(results, 1):
        simple_icon = "✅" if r['simple_correct'] else "❌"
        llm_icon = "✅" if r['llm_correct'] else "❌"
        
        print(f"\n{i}. Simple: {simple_icon} | LLM Judge: {llm_icon} | [{r['subject']}]")
        print(f"   Q: {r['question'][:70]}...")
        print(f"   Model:   {r['model_answer'][:60]}")
        print(f"   Correct: {r['correct_answer'][:60]}")
        print(f"   Model Confidence: {r['confidence']}%")
        
        if r['simple_correct'] != r['llm_correct']:
            print(f"    Judge: {r['judge_explanation'][:100]}...")
            print(f"    Judge Confidence: {r['judge_confidence']}%")

    print("\n" + "="*70)
