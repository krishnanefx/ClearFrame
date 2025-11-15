import argparse
from src.agents.news_agent import NewsAgent

def main():
    parser = argparse.ArgumentParser(description="Compare narratives on a given topic.")
    parser.add_argument("topic", type=str, help="The topic to compare narratives on.")
    args = parser.parse_args()

    agent = NewsAgent()
    comparisons = agent.compare_narratives(args.topic)

    for i, comparison in enumerate(comparisons):
        print(f"--- Cluster {i+1} ---")
        print(f"State-Aligned Summary: {comparison.state_aligned_summary}")
        print(f"Independent Summary: {comparison.independent_summary}")
        print(f"Bias Score: {comparison.bias_score}")
        print("\n")

if __name__ == "__main__":
    main()
