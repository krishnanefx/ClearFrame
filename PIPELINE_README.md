# AWS Data Pipeline Integration

## Overview

The AWS data pipeline provides a scalable, production-ready infrastructure for news ingestion and processing with the following capabilities:

- **Source Management**: YAML/JSON configuration for RSS feeds, URLs, APIs, and diaspora blog lists
- **Orchestration**: AWS Step Functions for coordinating the multi-stage pipeline
- **Retry Logic**: SQS-based retry queues with exponential backoff and circuit breakers
- **GPU Acceleration**: ECS Fargate tasks for embedding generation and bias scoring
- **Valyu Integration**: Bias analysis powered by Valyu API

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Source Configuration                         │
│                  (YAML/JSON in Git Repository)                   │
│   Tags: region, state_aligned, independent, diaspora, language   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   AWS Step Functions Orchestrator                │
├─────────────────────────────────────────────────────────────────┤
│  Stage 1: FetchArticles (Lambda)                                 │
│    ├─ RSS Feed Parser                                            │
│    ├─ Web Scraper                                                │
│    ├─ API Client                                                 │
│    └─ Retry Logic → SQS Retry Queue                              │
│                                                                   │
│  Stage 2: NormalizeContent (Lambda)                              │
│    ├─ Language Detection                                         │
│    ├─ HTML Stripping                                             │
│    └─ Content Deduplication                                      │
│                                                                   │
│  Stage 3: EmbedAndCluster (ECS Fargate + GPU)                    │
│    ├─ Sentence Transformers                                      │
│    ├─ HDBSCAN Clustering                                         │
│    └─ S3 Storage                                                 │
│                                                                   │
│  Stage 4: BiasScoreAndExplain (ECS Fargate + GPU + Valyu)        │
│    ├─ Valyu API Integration                                      │
│    ├─ Bias Dimension Analysis                                    │
│    └─ Explanation Generation                                     │
│                                                                   │
│  Stage 5: StoreResults (Lambda)                                  │
│    ├─ DynamoDB Storage                                           │
│    └─ S3 Archive                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Source Configuration Loader (`src/pipeline/source_config_loader.py`)

Loads and manages source configurations with tag-based filtering:

```python
from src.pipeline.source_config_loader import SourceConfigLoader

loader = SourceConfigLoader('./config/sources.yaml')

# Get all diaspora sources
diaspora_sources = loader.get_diaspora_sources()

# Get sources by region
asia_sources = loader.get_sources_by_region('asia')

# Get independent sources in English
sources = loader.get_sources(tags={'independent': True, 'language': 'en'})
```

### 2. Pipeline Orchestrator (`src/pipeline/orchestrator.py`)

Manages Step Functions state machine execution:

```python
from src.pipeline.orchestrator import PipelineOrchestrator
import boto3

sfn_client = boto3.client('stepfunctions')
orchestrator = PipelineOrchestrator(
    step_functions_client=sfn_client,
    state_machine_arn='arn:aws:states:...'
)

# Start execution
execution = orchestrator.start_execution(sources)

# Monitor status
status = orchestrator.get_execution_status(execution['execution_arn'])
```

### 3. Lambda Handlers (`src/pipeline/lambda_handlers.py`)

Five Lambda handlers for pipeline stages:
- `fetch_articles_handler`: Scrape and fetch articles
- `normalize_content_handler`: Clean and normalize content
- `embed_and_cluster_handler`: Generate embeddings (ECS entry point)
- `bias_score_handler`: Score bias with Valyu (ECS entry point)
- `store_results_handler`: Store final results

### 4. SQS Retry Queue (`src/pipeline/sqs_retry_queue.py`)

Implements retry logic with circuit breaker pattern:

```python
from src.pipeline.sqs_retry_queue import SQSRetryQueue
import boto3

sqs_client = boto3.client('sqs')
retry_queue = SQSRetryQueue(
    sqs_client=sqs_client,
    retry_queue_url='https://sqs...',
    max_retries=3,
    base_delay=2
)

# Send failed source to retry queue
retry_queue.send_to_retry_queue(source, error='Timeout', retry_count=0)

# Check circuit breaker status
status = retry_queue.get_circuit_breaker_status()
```

### 5. ECS Task Configurator (`src/pipeline/ecs_config.py`)

Manages ECS Fargate task definitions for GPU workloads:

```python
from src.pipeline.ecs_config import ECSTaskConfigurator
import boto3

ecs_client = boto3.client('ecs')
configurator = ECSTaskConfigurator(ecs_client)

# Create task definitions
embed_task_def = configurator.create_embed_cluster_task_definition()
bias_task_def = configurator.create_bias_score_task_definition()

# Register with ECS
arn = configurator.register_task_definition(embed_task_def)
```

## Configuration

### Source Configuration (`config/sources.yaml`)

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

### AWS Configuration (`.env` or config)

```bash
AWS_REGION=us-east-1
STEP_FUNCTIONS_STATE_MACHINE_ARN=arn:aws:states:...
RETRY_QUEUE_URL=https://sqs.us-east-1...
PIPELINE_BUCKET=news-pipeline-bucket
VALYU_API_KEY=your-key
```

## Deployment

See [`DEPLOYMENT_GUIDE.md`](./DEPLOYMENT_GUIDE.md) for complete deployment instructions.

### Quick Start

1. **Configure Sources**:
   ```bash
   cp config/sources.json config/sources.yaml
   # Edit sources.yaml with your sources
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set Up AWS Infrastructure**:
   ```bash
   # Follow DEPLOYMENT_GUIDE.md steps 1-6
   ```

4. **Run Example**:
   ```bash
   python example_pipeline_usage.py
   ```

## Pipeline Stages

### Stage 1: FetchArticles (Lambda)

- Fetches from RSS feeds, URLs, and APIs
- Supports multiple authentication methods
- Implements retry logic with SQS
- Handles circuit breaker for failing sources

**Retry Behavior**:
- Initial delay: 2 seconds
- Exponential backoff: 2^retry_count
- Max retries: 3
- After max retries → Dead Letter Queue

### Stage 2: NormalizeContent (Lambda)

- Strips HTML tags
- Detects language using langdetect
- Generates content hashes for deduplication
- Extracts structured data

### Stage 3: EmbedAndCluster (ECS Fargate + GPU)

- Runs on ECS Fargate with GPU support
- Uses Sentence Transformers for embeddings
- HDBSCAN clustering algorithm
- Stores results in S3

**Configuration**:
- CPU: 4 vCPU
- Memory: 16 GB
- GPU: 1 (Tesla T4 or similar)
- Model: sentence-transformers/all-mpnet-base-v2

### Stage 4: BiasScoreAndExplain (ECS Fargate + GPU + Valyu)

- Runs on ECS Fargate with GPU support
- Integrates with Valyu API
- Parallel processing with ThreadPoolExecutor
- Generates bias explanations

**Bias Dimensions**:
- Political bias
- Emotional bias
- Framing bias
- Source credibility

### Stage 5: StoreResults (Lambda)

- Stores to DynamoDB
- Archives to S3
- Maintains pipeline metadata

## Circuit Breaker

Prevents cascading failures by tracking source reliability:

- **CLOSED**: Normal operation
- **OPEN**: Source failing, reject requests
- **HALF_OPEN**: Testing if service recovered

**Thresholds**:
- Failure threshold: 5 consecutive failures
- Success threshold: 2 consecutive successes
- Timeout: 60 seconds before retry

## Monitoring

### CloudWatch Logs
- `/aws/lambda/news-pipeline-fetch-articles`
- `/aws/lambda/news-pipeline-normalize-content`
- `/aws/lambda/news-pipeline-store-results`
- `/ecs/news-pipeline-embed-cluster`
- `/ecs/news-pipeline-bias-score`

### Metrics to Monitor
- Step Functions execution count/success rate
- Lambda invocation count/errors
- SQS queue depth
- DLQ message count
- ECS task success rate
- Circuit breaker states

## Cost Considerations

**Estimated Monthly Costs** (1000 articles/day):

- Lambda: ~$50
- ECS Fargate (GPU): ~$200-400
- Step Functions: ~$5
- S3: ~$10
- DynamoDB: ~$25
- SQS: Negligible

**Total**: ~$290-490/month

## Integration with Existing Code

The pipeline integrates seamlessly with existing agent infrastructure:

```python
from src.pipeline.source_config_loader import SourceConfigLoader
from src.pipeline.orchestrator import PipelineOrchestrator
from src.integration.agent_coordinator import AgentCoordinator

# Load sources
loader = SourceConfigLoader('./config/sources.yaml')
sources = loader.get_all_sources()

# Start pipeline
orchestrator = PipelineOrchestrator(...)
execution = orchestrator.start_execution(sources)

# Use processed articles with agent coordinator
coordinator = AgentCoordinator()
# ... integrate with agent workflow
```

## Testing

```bash
# Run unit tests
pytest tests/test_pipeline.py

# Run integration tests
pytest tests/test_integration_pipeline.py

# Test source configuration
python -c "
from src.pipeline.source_config_loader import SourceConfigLoader
loader = SourceConfigLoader('./config/sources.yaml')
print(loader.validate_sources())
"
```

## Troubleshooting

### Common Issues

1. **Lambda Timeout**: Increase timeout or reduce batch size
2. **ECS Task Failures**: Check GPU availability and memory limits
3. **Valyu API Errors**: Verify API key and rate limits
4. **Circuit Breaker Open**: Check source availability and logs

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

- [ ] Add support for more source types (Twitter, Reddit, etc.)
- [ ] Implement streaming ingestion with Kinesis
- [ ] Add real-time bias detection
- [ ] Create web dashboard for monitoring
- [ ] Add A/B testing for different embedding models
- [ ] Implement federated learning for privacy-preserving bias detection

## License

See main project LICENSE file.

## Support

For issues or questions:
1. Check DEPLOYMENT_GUIDE.md
2. Review CloudWatch logs
3. Check circuit breaker states
4. Open an issue on GitHub
