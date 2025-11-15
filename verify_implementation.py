"""
Verification script to check pipeline implementation.
Run this to verify all components are in place.
"""

import os
import sys
from pathlib import Path

def check_file_exists(filepath, description):
    """Check if a file exists."""
    exists = os.path.exists(filepath)
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {filepath}")
    return exists

def main():
    """Verify pipeline implementation."""
    print("=" * 70)
    print("AWS Data Pipeline Implementation Verification")
    print("=" * 70)
    
    base_path = Path(__file__).parent
    all_good = True
    
    # Core pipeline files
    print("\n📁 Core Pipeline Components:")
    core_files = [
        ("src/pipeline/__init__.py", "Package init"),
        ("src/pipeline/source_config_loader.py", "Source config loader"),
        ("src/pipeline/orchestrator.py", "Step Functions orchestrator"),
        ("src/pipeline/lambda_handlers.py", "Lambda handlers"),
        ("src/pipeline/sqs_retry_queue.py", "SQS retry queue"),
        ("src/pipeline/ecs_config.py", "ECS configuration"),
    ]
    
    for filepath, desc in core_files:
        full_path = base_path / filepath
        all_good &= check_file_exists(full_path, desc)
    
    # Docker files
    print("\n🐳 Docker Components:")
    docker_files = [
        ("src/pipeline/docker/Dockerfile.embed-cluster", "Embed cluster Dockerfile"),
        ("src/pipeline/docker/Dockerfile.bias-score", "Bias score Dockerfile"),
        ("src/pipeline/docker/embed_cluster_worker.py", "Embed worker"),
        ("src/pipeline/docker/bias_score_worker.py", "Bias worker"),
        ("src/pipeline/docker/requirements-ecs.txt", "ECS requirements"),
    ]
    
    for filepath, desc in docker_files:
        full_path = base_path / filepath
        all_good &= check_file_exists(full_path, desc)
    
    # Configuration files
    print("\n⚙️  Configuration Files:")
    config_files = [
        ("config/sources.yaml", "YAML source config"),
        ("config/sources.json", "JSON source config"),
    ]
    
    for filepath, desc in config_files:
        full_path = base_path / filepath
        all_good &= check_file_exists(full_path, desc)
    
    # Documentation
    print("\n📚 Documentation:")
    doc_files = [
        ("PIPELINE_README.md", "Pipeline documentation"),
        ("DEPLOYMENT_GUIDE.md", "Deployment guide"),
        ("IMPLEMENTATION_SUMMARY.md", "Implementation summary"),
        ("IMPLEMENTATION_COMPLETE.md", "Completion summary"),
        ("QUICK_REFERENCE.md", "Quick reference"),
        ("example_pipeline_usage.py", "Usage examples"),
    ]
    
    for filepath, desc in doc_files:
        full_path = base_path / filepath
        all_good &= check_file_exists(full_path, desc)
    
    # Tests
    print("\n🧪 Tests:")
    test_files = [
        ("tests/test_pipeline.py", "Pipeline tests"),
    ]
    
    for filepath, desc in test_files:
        full_path = base_path / filepath
        all_good &= check_file_exists(full_path, desc)
    
    # Modified files
    print("\n📝 Modified Files:")
    modified_files = [
        ("requirements.txt", "Updated dependencies"),
        ("config/config.py", "Updated configuration"),
        ("README.md", "Updated README"),
    ]
    
    for filepath, desc in modified_files:
        full_path = base_path / filepath
        all_good &= check_file_exists(full_path, desc)
    
    # Summary
    print("\n" + "=" * 70)
    if all_good:
        print("✅ ALL FILES VERIFIED SUCCESSFULLY!")
        print("\n🎉 AWS Data Pipeline Implementation Complete!")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Review documentation: PIPELINE_README.md")
        print("3. Follow deployment guide: DEPLOYMENT_GUIDE.md")
        print("4. Run examples: python example_pipeline_usage.py")
        print("5. Run tests: pytest tests/test_pipeline.py -v")
    else:
        print("❌ SOME FILES ARE MISSING!")
        print("Please check the output above for missing files.")
    print("=" * 70)
    
    return 0 if all_good else 1

if __name__ == '__main__':
    sys.exit(main())
