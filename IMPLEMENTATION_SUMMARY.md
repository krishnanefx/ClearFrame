# AWS Data Pipeline Implementation Summary

## What Was Implemented

This document summarizes the AWS-heavy, Valyu-powered data pipeline implementation added to the news agent codebase.

## Files Created/Modified

### New Files Created

#### Pipeline Core Components
1. **`src/pipeline/__init__.py`** - Package initialization
2. **`src/pipeline/source_config_loader.py`** - Loads and manages source configurations from YAML/JSON
3. **`src/pipeline/orchestrator.py`** - AWS Step Functions orchestrator for pipeline coordination
4. **`src/pipeline/lambda_handlers.py`** - Lambda function handlers for all pipeline stages
5. **`src/pipeline/sqs_retry_queue.py`** - SQS retry logic with circuit breaker pattern
6. **`src/pipeline/ecs_config.py`** - ECS/Fargate task configuration for GPU workloads

#### Docker Components for ECS
7. **`src/pipeline/docker/Dockerfile.embed-cluster`** - Container for embedding/clustering
8. **`src/pipeline/docker/Dockerfile.bias-score`** - Container for bias scoring
9. **`src/pipeline/docker/embed_cluster_worker.py`** - ECS worker for embeddings
10. **`src/pipeline/docker/bias_score_worker.py`** - ECS worker for bias scoring
11. **`src/pipeline/docker/requirements-ecs.txt`** - Dependencies for ECS containers

#### Configuration Files
12. **`config/sources.yaml`** - YAML source configuration with tags
13. **`config/sources.json`** - JSON alternative for source configuration

#### Documentation
14. **`PIPELINE_README.md`** - Complete pipeline documentation
15. **`DEPLOYMENT_GUIDE.md`** - Step-by-step AWS deployment guide
16. **`example_pipeline_usage.py`** - Comprehensive usage examples

#### Tests
17. **`tests/test_pipeline.py`** - Unit and integration tests for pipeline

### Modified Files
18. **`requirements.txt`** - Added AWS SDK, ML, and scraping dependencies
19. **`config/config.py`** - Added AWS and pipeline configuration sections
20. **`README.md`** - Updated with pipeline overview

## Architecture Overview

### Pipeline Flow

```
Sources (YAML/JSON) 
    ↓
AWS Step Functions Orchestrator
    ↓
┌─────────────────────────────────────────┐
│ Stage 1: FetchArticles (Lambda)         │
│  - RSS feed parsing                     │
│  - Web scraping                         │
│  - API integration                      │
│  - Retry logic → SQS                    │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ Stage 2: NormalizeContent (Lambda)      │
│  - Language detection                   │
│  - HTML stripping                       │
│  - Deduplication                        │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ Stage 3: EmbedAndCluster (ECS+GPU)      │
│  - Sentence Transformers                │
│  - HDBSCAN clustering                   │
│  - S3 storage                           │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ Stage 4: BiasScore (ECS+GPU+Valyu)      │
│  - Valyu API integration                │
│  - Parallel processing                  │
│  - Bias dimension analysis              │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ Stage 5: StoreResults (Lambda)          │
│  - DynamoDB storage                     │
│  - S3 archival                          │
└─────────────────────────────────────────┘
```

## Key Features Implemented

### 1. Source Configuration System
- **File**: `source_config_loader.py`
- **Features**:
  - YAML and JSON support
  - Tag-based filtering (region, state_aligned, independent, diaspora, language)
  - Environment variable substitution
  - Source validation
  - Flexible querying

### 2. Step Functions Orchestrator
- **File**: `orchestrator.py`
- **Features**:
  - Complete state machine definition
  - Execution management (start, stop, status)
  - Retry logic with exponential backoff
  - Error handling with catch blocks
  - ECS task integration

### 3. Lambda Handlers
- **File**: `lambda_handlers.py`
- **Handlers**:
  - `fetch_articles_handler`: Multi-source fetching (RSS, URL, API)
  - `normalize_content_handler`: Content cleaning and language detection
  - `store_results_handler`: Multi-storage backend support

### 4. SQS Retry System
- **File**: `sqs_retry_queue.py`
- **Features**:
  - Exponential backoff (2^retry_count)
  - Circuit breaker pattern (CLOSED, OPEN, HALF_OPEN)
  - Dead Letter Queue (DLQ) for max failures
  - Per-source failure tracking
  - Configurable retry thresholds

### 5. ECS Task Configuration
- **File**: `ecs_config.py`
- **Features**:
  - GPU-enabled task definitions
  - CloudFormation template generation
  - Task execution and monitoring
  - CloudWatch logs integration

### 6. ECS Workers
- **Files**: `embed_cluster_worker.py`, `bias_score_worker.py`
- **Features**:
  - Sentence Transformers for embeddings
  - HDBSCAN clustering algorithm
  - Valyu API integration
  - Parallel bias scoring
  - S3 input/output handling

## Source Configuration Tags

Each source is tagged with:
- **region**: Geographic region (global, asia, middle_east, north_america, etc.)
- **state_aligned**: Boolean - government-aligned media
- **independent**: Boolean - independent media
- **diaspora**: Boolean - diaspora community sources
- **language**: Language code (en, ar, zh, etc.)

## AWS Resources Required

### Compute
- **Lambda Functions**: 3 functions (fetch, normalize, store)
- **ECS Cluster**: Fargate cluster for GPU tasks
- **ECS Task Definitions**: 2 definitions (embed-cluster, bias-score)

### Storage
- **S3 Bucket**: Pipeline data storage
- **DynamoDB Table**: Article storage
- **ECR Repositories**: 2 repos for container images

### Integration
- **Step Functions**: 1 state machine
- **SQS Queues**: 3 queues (main, retry, DLQ)
- **CloudWatch**: Logs and metrics

### Security
- **IAM Roles**: Execution roles for Lambda, ECS, Step Functions
- **Secrets Manager**: API keys (OpenAI, Valyu, NewsAPI)

## Circuit Breaker Implementation

Prevents cascading failures by tracking source reliability:

### States
- **CLOSED**: Normal operation, requests allowed
- **OPEN**: Too many failures, reject requests
- **HALF_OPEN**: Testing recovery, limited requests

### Thresholds
- Failure threshold: 5 consecutive failures → OPEN
- Success threshold: 2 consecutive successes → CLOSED
- Timeout: 60 seconds before retry from OPEN → HALF_OPEN

## Testing Coverage

### Unit Tests
- Source configuration loading
- State machine definition
- Circuit breaker logic
- Lambda handler functions
- ECS task definition creation

### Integration Tests
- End-to-end pipeline workflow
- Mocked AWS service interactions
- Retry queue processing
- Circuit breaker state transitions

### Test Command
```bash
pytest tests/test_pipeline.py -v
```

## Configuration Example

### Environment Variables
```bash
AWS_REGION=us-east-1
STEP_FUNCTIONS_STATE_MACHINE_ARN=arn:aws:states:...
RETRY_QUEUE_URL=https://sqs...
PIPELINE_BUCKET=news-pipeline-bucket
VALYU_API_KEY=your-key
```

### Source Configuration
```yaml
sources:
  - type: rss
    url: "https://example.com/rss"
    name: "Example News"
    tags:
      region: "global"
      state_aligned: false
      independent: true
      diaspora: false
      language: "en"
    refresh_interval: 1800
```

## Usage Examples

### Load and Filter Sources
```python
from src.pipeline.source_config_loader import SourceConfigLoader

loader = SourceConfigLoader('./config/sources.yaml')
diaspora_sources = loader.get_diaspora_sources()
```

### Start Pipeline Execution
```python
from src.pipeline.orchestrator import PipelineOrchestrator
import boto3

orchestrator = PipelineOrchestrator(
    step_functions_client=boto3.client('stepfunctions'),
    state_machine_arn='arn:aws:states:...'
)

execution = orchestrator.start_execution(sources)
```

### Monitor Execution
```python
status = orchestrator.get_execution_status(execution['execution_arn'])
print(f"Status: {status['status']}")
```

## Cost Estimates

For processing 1,000 articles per day:

- **Lambda**: ~$50/month
- **ECS Fargate (GPU)**: ~$200-400/month
- **Step Functions**: ~$5/month
- **S3**: ~$10/month
- **DynamoDB**: ~$25/month
- **SQS**: Negligible

**Total**: ~$290-490/month

## Next Steps for Deployment

1. **Review** `DEPLOYMENT_GUIDE.md`
2. **Set up** AWS infrastructure (VPC, subnets, security groups)
3. **Create** S3 bucket and DynamoDB table
4. **Deploy** Lambda functions
5. **Build and push** Docker images to ECR
6. **Register** ECS task definitions
7. **Create** Step Functions state machine
8. **Configure** environment variables and secrets
9. **Test** with example sources
10. **Monitor** CloudWatch logs and metrics

## Integration with Existing Code

The pipeline integrates seamlessly with existing components:

```python
from src.pipeline.orchestrator import PipelineOrchestrator
from src.integration.agent_coordinator import AgentCoordinator
from src.state.state_manager import StateManager

# Start pipeline to ingest news
orchestrator = PipelineOrchestrator(...)
execution = orchestrator.start_execution(sources)

# Wait for completion and use results with existing agents
# ... pipeline processing ...

# Use processed articles with agent coordinator
coordinator = AgentCoordinator(state_manager=StateManager())
# ... agent workflow ...
```

## Documentation

- **PIPELINE_README.md**: Complete pipeline documentation
- **DEPLOYMENT_GUIDE.md**: AWS deployment instructions
- **example_pipeline_usage.py**: Code examples
- **Inline comments**: Comprehensive code documentation

## Conclusion

This implementation provides a production-ready, scalable AWS data pipeline for news ingestion that:

✅ Supports multiple source types (RSS, URL, API)  
✅ Includes comprehensive tagging system  
✅ Implements retry logic with circuit breakers  
✅ Uses GPU acceleration for ML workloads  
✅ Integrates with Valyu for bias analysis  
✅ Provides monitoring and logging  
✅ Includes complete testing suite  
✅ Offers detailed documentation  

The pipeline is ready for AWS deployment following the DEPLOYMENT_GUIDE.md instructions.
