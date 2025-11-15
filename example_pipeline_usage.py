"""
Example usage of the AWS data pipeline for news ingestion.
"""

import os
import boto3
from src.pipeline.source_config_loader import SourceConfigLoader
from src.pipeline.orchestrator import PipelineOrchestrator
from src.pipeline.sqs_retry_queue import SQSRetryQueue
from src.pipeline.ecs_config import ECSTaskConfigurator
from config.config import Config


def example_load_sources():
    """Example: Load sources from configuration."""
    print("=" * 60)
    print("Example 1: Loading Source Configurations")
    print("=" * 60)
    
    # Load sources from YAML
    loader = SourceConfigLoader('./config/sources.yaml')
    
    # Get all sources
    all_sources = loader.get_all_sources()
    print(f"\nTotal sources configured: {len(all_sources)}")
    
    # Get diaspora sources
    diaspora_sources = loader.get_diaspora_sources()
    print(f"Diaspora sources: {len(diaspora_sources)}")
    for source in diaspora_sources:
        print(f"  - {source['name']}")
    
    # Get independent sources
    independent_sources = loader.get_independent_sources()
    print(f"\nIndependent sources: {len(independent_sources)}")
    
    # Get sources by region
    asia_sources = loader.get_sources_by_region('asia')
    print(f"Asia region sources: {len(asia_sources)}")
    
    # Validate sources
    validation = loader.validate_sources()
    print(f"\nValidation results:")
    print(f"  Valid sources: {len(validation['valid'])}")
    print(f"  Invalid sources: {len(validation['invalid'])}")
    
    return loader


def example_start_pipeline():
    """Example: Start a pipeline execution."""
    print("\n" + "=" * 60)
    print("Example 2: Starting Pipeline Execution")
    print("=" * 60)
    
    # Load configuration
    config = Config()
    
    # Initialize AWS clients
    sfn_client = boto3.client('stepfunctions', region_name=config.get('aws.region'))
    
    # Load sources
    loader = SourceConfigLoader('./config/sources.yaml')
    sources = loader.get_all_sources()[:10]  # Limit to 10 for example
    
    # Initialize orchestrator
    orchestrator = PipelineOrchestrator(
        step_functions_client=sfn_client,
        state_machine_arn=config.get('aws.step_functions.state_machine_arn')
    )
    
    # Start execution
    print(f"\nStarting pipeline for {len(sources)} sources...")
    
    # Note: Uncomment to actually start execution
    # execution = orchestrator.start_execution(sources)
    # print(f"Execution ARN: {execution['execution_arn']}")
    # print(f"Status: {execution['status']}")
    
    print("(Skipped actual execution - uncomment to run)")
    
    return orchestrator


def example_retry_queue():
    """Example: Work with SQS retry queue."""
    print("\n" + "=" * 60)
    print("Example 3: SQS Retry Queue with Circuit Breaker")
    print("=" * 60)
    
    # Initialize SQS client
    sqs_client = boto3.client('sqs')
    
    # Create retry queue manager
    retry_queue = SQSRetryQueue(
        sqs_client=sqs_client,
        retry_queue_url=os.getenv('RETRY_QUEUE_URL'),
        dlq_url=os.getenv('DLQ_URL'),
        max_retries=3,
        base_delay=2
    )
    
    # Example: Send failed source to retry queue
    failed_source = {
        'type': 'rss',
        'url': 'https://example.com/rss',
        'name': 'Example Source',
        'tags': {'region': 'global', 'independent': True}
    }
    
    print("\nSimulating failed source...")
    print(f"Source: {failed_source['name']}")
    
    # Note: Uncomment to actually send to queue
    # retry_queue.send_to_retry_queue(
    #     source=failed_source,
    #     error="Connection timeout",
    #     retry_count=0
    # )
    
    print("(Skipped actual queue operation - uncomment to run)")
    
    # Check circuit breaker status
    print("\nCircuit breaker status:")
    status = retry_queue.get_circuit_breaker_status()
    if status:
        for source_name, info in status.items():
            print(f"  {source_name}: {info['state']}")
    else:
        print("  No circuit breakers active")
    
    return retry_queue


def example_ecs_tasks():
    """Example: Configure ECS tasks."""
    print("\n" + "=" * 60)
    print("Example 4: ECS Task Configuration")
    print("=" * 60)
    
    # Initialize ECS client
    ecs_client = boto3.client('ecs')
    
    # Create task configurator
    configurator = ECSTaskConfigurator(ecs_client=ecs_client)
    
    # Get task definitions
    embed_task_def = configurator.create_embed_cluster_task_definition()
    bias_task_def = configurator.create_bias_score_task_definition()
    
    print("\nEmbed & Cluster Task Definition:")
    print(f"  Family: {embed_task_def['family']}")
    print(f"  CPU: {embed_task_def['cpu']}")
    print(f"  Memory: {embed_task_def['memory']}")
    print(f"  GPU Required: Yes")
    
    print("\nBias Score Task Definition:")
    print(f"  Family: {bias_task_def['family']}")
    print(f"  CPU: {bias_task_def['cpu']}")
    print(f"  Memory: {bias_task_def['memory']}")
    print(f"  GPU Required: Yes")
    
    # Note: Uncomment to actually register
    # embed_arn = configurator.register_task_definition(embed_task_def)
    # print(f"\nRegistered embed task: {embed_arn}")
    
    print("\n(Skipped actual registration - uncomment to run)")
    
    return configurator


def example_monitor_execution():
    """Example: Monitor a pipeline execution."""
    print("\n" + "=" * 60)
    print("Example 5: Monitoring Pipeline Execution")
    print("=" * 60)
    
    # Initialize clients
    sfn_client = boto3.client('stepfunctions')
    
    # Initialize orchestrator
    config = Config()
    orchestrator = PipelineOrchestrator(
        step_functions_client=sfn_client,
        state_machine_arn=config.get('aws.step_functions.state_machine_arn')
    )
    
    # Example execution ARN (replace with actual)
    execution_arn = "arn:aws:states:us-east-1:123456789:execution:news-pipeline:example"
    
    print(f"\nMonitoring execution: {execution_arn}")
    
    # Note: Uncomment to actually check status
    # status = orchestrator.get_execution_status(execution_arn)
    # print(f"Status: {status['status']}")
    # print(f"Start Date: {status['start_date']}")
    # if status['stop_date']:
    #     print(f"Stop Date: {status['stop_date']}")
    
    print("(Skipped actual status check - uncomment to run)")


def example_end_to_end():
    """Example: Complete end-to-end pipeline workflow."""
    print("\n" + "=" * 60)
    print("Example 6: End-to-End Pipeline Workflow")
    print("=" * 60)
    
    print("\nStep 1: Load source configurations")
    loader = SourceConfigLoader('./config/sources.yaml')
    sources = loader.get_sources(tags={'language': 'en'})
    print(f"  Loaded {len(sources)} English sources")
    
    print("\nStep 2: Validate sources")
    validation = loader.validate_sources()
    if validation['invalid']:
        print(f"  Warning: {len(validation['invalid'])} invalid sources")
    
    print("\nStep 3: Initialize AWS components")
    print("  - Step Functions orchestrator")
    print("  - SQS retry queues")
    print("  - ECS task definitions")
    
    print("\nStep 4: Start pipeline execution")
    print("  - FetchArticles stage")
    print("  - NormalizeContent stage")
    print("  - EmbedAndCluster stage (ECS Fargate)")
    print("  - BiasScoreAndExplain stage (ECS Fargate + Valyu)")
    print("  - StoreResults stage")
    
    print("\nStep 5: Monitor execution")
    print("  - Check Step Functions status")
    print("  - Review CloudWatch logs")
    print("  - Track circuit breaker states")
    
    print("\nStep 6: Handle failures")
    print("  - Automatic retry with exponential backoff")
    print("  - Circuit breaker prevents cascading failures")
    print("  - Failed sources sent to DLQ for investigation")
    
    print("\n" + "=" * 60)
    print("Pipeline workflow overview complete")
    print("=" * 60)


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("AWS Data Pipeline Examples")
    print("=" * 60)
    
    # Run examples
    try:
        example_load_sources()
        example_start_pipeline()
        example_retry_queue()
        example_ecs_tasks()
        example_monitor_execution()
        example_end_to_end()
        
        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        print("Note: Some examples require AWS credentials and resources")
