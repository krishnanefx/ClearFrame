"""
Load Testing Suite for Track A: Iron Man

Tests agent performance under concurrent load to prove production readiness.
Uses locust for load testing with realistic user scenarios.

Installation:
    pip install locust

Usage:
    # Web UI mode (recommended):
    locust -f tests/test_load.py --host=http://localhost:8000
    # Then open http://localhost:8089 and configure test
    
    # Headless mode:
    locust -f tests/test_load.py --host=http://localhost:8000 \
           --users 50 --spawn-rate 5 --run-time 60s --headless

    # Test the CLI directly (bypass API):
    python tests/test_load.py --direct-cli --users 10 --duration 30
"""

from locust import HttpUser, task, between, events
import subprocess
import json
import time
import random
import sys
from pathlib import Path
from typing import List, Dict, Any
import statistics

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"

# Sample queries for load testing
TEST_QUERIES = [
    "Sudan war humanitarian crisis",
    "Climate change policy debate",
    "AI regulation developments",
    "Ukraine conflict updates",
    "US election coverage",
    "China-Taiwan tensions",
    "Middle East peace talks",
    "Global economic outlook",
    "Cybersecurity threats",
    "Space exploration news"
]


class NewsAnalysisUser(HttpUser):
    """
    Simulated user performing news analysis queries.
    
    This simulates realistic user behavior patterns.
    """
    
    # Wait 1-5 seconds between tasks (realistic user behavior)
    wait_time = between(1, 5)
    
    @task(3)  # Weight: 3x more likely than other tasks
    def analyze_news_pipeline(self):
        """
        Test the pipeline mode (most common use case).
        """
        query = random.choice(TEST_QUERIES)
        
        response = self.client.post("/api/analyze", json={
            "query": query,
            "mode": "pipeline",
            "max_results": 5
        })
        
        if response.status_code != 200:
            response.failure(f"Pipeline analysis failed: {response.status_code}")
    
    @task(2)
    def analyze_news_agent(self):
        """
        Test agent mode with tools.
        """
        query = random.choice(TEST_QUERIES)
        
        response = self.client.post("/api/analyze", json={
            "query": query,
            "mode": "agent",
            "max_results": 5,
            "tools": ["bias", "credibility"]
        })
        
        if response.status_code != 200:
            response.failure(f"Agent analysis failed: {response.status_code}")
    
    @task(1)
    def analyze_structured(self):
        """
        Test structured output mode.
        """
        query = random.choice(TEST_QUERIES)
        
        response = self.client.post("/api/analyze", json={
            "query": query,
            "mode": "structured",
            "max_results": 5
        })
        
        if response.status_code != 200:
            response.failure(f"Structured analysis failed: {response.status_code}")


class DirectCLILoadTest:
    """
    Direct CLI load testing (no HTTP API required).
    
    This tests the basic_cli.py script directly with concurrent processes.
    """
    
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.start_time = None
        self.end_time = None
    
    def run_single_query(self, query: str) -> Dict[str, Any]:
        """Run a single CLI query and measure performance."""
        start = time.time()
        
        try:
            # Run basic_cli.py with the query
            result = subprocess.run([
                sys.executable,
                str(BACKEND_ROOT / "basic_cli.py"),
                "--query", query,
                "--max-results", "5",
                "--json-only"
            ], 
            capture_output=True, 
            text=True, 
            timeout=30  # 30 second timeout
            )
            
            duration = time.time() - start
            
            success = result.returncode == 0
            
            return {
                "query": query,
                "duration": duration,
                "success": success,
                "output_size": len(result.stdout) if success else 0,
                "error": result.stderr if not success else None
            }
        
        except subprocess.TimeoutExpired:
            duration = time.time() - start
            return {
                "query": query,
                "duration": duration,
                "success": False,
                "error": "Timeout (>30s)"
            }
        except Exception as e:
            duration = time.time() - start
            return {
                "query": query,
                "duration": duration,
                "success": False,
                "error": str(e)
            }
    
    def run_concurrent_test(self, num_users: int, duration_seconds: int):
        """
        Run concurrent CLI tests.
        
        Args:
            num_users: Number of concurrent "users" (processes)
            duration_seconds: How long to run the test
        """
        import concurrent.futures
        
        print(f"\n{'='*60}")
        print(f"Load Test: {num_users} concurrent users for {duration_seconds}s")
        print(f"{'='*60}\n")
        
        self.start_time = time.time()
        end_time = self.start_time + duration_seconds
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = []
            
            while time.time() < end_time:
                # Submit queries from multiple "users"
                for _ in range(num_users):
                    query = random.choice(TEST_QUERIES)
                    future = executor.submit(self.run_single_query, query)
                    futures.append(future)
                
                # Wait a bit before next batch
                time.sleep(1)
            
            # Collect results
            print("Waiting for all queries to complete...")
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                self.results.append(result)
                
                status = "✓" if result['success'] else "✗"
                print(f"{status} {result['query'][:50]:50s} {result['duration']:.2f}s")
        
        self.end_time = time.time()
        self.print_report()
    
    def print_report(self):
        """Print load test report."""
        if not self.results:
            print("No results to report")
            return
        
        total_time = self.end_time - self.start_time
        successful = [r for r in self.results if r['success']]
        failed = [r for r in self.results if not r['success']]
        
        durations = [r['duration'] for r in successful]
        
        print(f"\n{'='*60}")
        print("Load Test Report")
        print(f"{'='*60}")
        
        print(f"\n📊 Summary:")
        print(f"  Total Queries:    {len(self.results)}")
        print(f"  Successful:       {len(successful)} ({len(successful)/len(self.results)*100:.1f}%)")
        print(f"  Failed:           {len(failed)} ({len(failed)/len(self.results)*100:.1f}%)")
        print(f"  Total Time:       {total_time:.2f}s")
        print(f"  Throughput:       {len(self.results)/total_time:.2f} queries/sec")
        
        if durations:
            print(f"\n⏱️  Latency Statistics:")
            print(f"  Min:              {min(durations):.2f}s")
            print(f"  Max:              {max(durations):.2f}s")
            print(f"  Mean:             {statistics.mean(durations):.2f}s")
            print(f"  Median:           {statistics.median(durations):.2f}s")
            print(f"  95th percentile:  {statistics.quantiles(durations, n=20)[18]:.2f}s")
        
        if failed:
            print(f"\n❌ Failures:")
            error_counts = {}
            for f in failed:
                error = f.get('error', 'Unknown error')
                error_counts[error] = error_counts.get(error, 0) + 1
            
            for error, count in sorted(error_counts.items(), key=lambda x: -x[1]):
                print(f"  {count}x: {error}")
        
        # Save detailed results to JSON
        output_file = "load_test_results.json"
        with open(output_file, 'w') as f:
            json.dump({
                "summary": {
                    "total_queries": len(self.results),
                    "successful": len(successful),
                    "failed": len(failed),
                    "success_rate": len(successful)/len(self.results)*100,
                    "total_time": total_time,
                    "throughput": len(self.results)/total_time,
                },
                "latency": {
                    "min": min(durations) if durations else 0,
                    "max": max(durations) if durations else 0,
                    "mean": statistics.mean(durations) if durations else 0,
                    "median": statistics.median(durations) if durations else 0,
                },
                "details": self.results
            }, f, indent=2)
        
        print(f"\n✅ Detailed results saved to: {output_file}")
        print(f"{'='*60}\n")


def main():
    """Run direct CLI load test."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Load test for news analysis agent")
    parser.add_argument("--direct-cli", action="store_true", 
                       help="Test CLI directly (no API server)")
    parser.add_argument("--users", type=int, default=10,
                       help="Number of concurrent users")
    parser.add_argument("--duration", type=int, default=30,
                       help="Test duration in seconds")
    
    args = parser.parse_args()
    
    if args.direct_cli:
        tester = DirectCLILoadTest()
        tester.run_concurrent_test(args.users, args.duration)
    else:
        print("To run HTTP load test:")
        print("  locust -f tests/test_load.py --host=http://localhost:8000")
        print("\nTo run direct CLI test:")
        print(f"  python tests/test_load.py --direct-cli --users {args.users} --duration {args.duration}")


if __name__ == "__main__":
    main()
