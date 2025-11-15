# AWS Data Pipeline - Quick Reference

## File Locations

```
src/pipeline/
├── source_config_loader.py    # Load sources from YAML/JSON
├── orchestrator.py            # Step Functions orchestrator
├── lambda_handlers.py         # Lambda functions (5 handlers)
├── sqs_retry_queue.py        # Retry logic + circuit breaker
├── ecs_config.py             # ECS task definitions
└── docker/                   # ECS containers
    ├── Dockerfile.embed-cluster
    ├── Dockerfile.bias-score
    ├── embed_cluster_worker.py
    ├── bias_score_worker.py
    └── requirements-ecs.txt

config/
├── sources.yaml              # Source configuration (YAML)
└── sources.json              # Source configuration (JSON)

tests/
└── test_pipeline.py          # Pipeline tests
```

## Quick Commands

### Run Examples
```bash
python example_pipeline_usage.py
```

### Run Tests
```bash
pytest tests/test_pipeline.py -v
```

### Validate Sources
```python
from src.pipeline.source_config_loader import SourceConfigLoader
loader = SourceConfigLoader('./config/sources.yaml')
print(loader.validate_sources())
```

## Common Code Snippets

### Load Sources
```python
from src.pipeline.source_config_loader import SourceConfigLoader

loader = SourceConfigLoader('./config/sources.yaml')
all_sources = loader.get_all_sources()
diaspora = loader.get_diaspora_sources()
independent = loader.get_independent_sources()
en_sources = loader.get_sources_by_language('en')
```

### Start Pipeline
```python
from src.pipeline.orchestrator import PipelineOrchestrator
import boto3

sfn = boto3.client('stepfunctions', region_name='us-east-1')
orchestrator = PipelineOrchestrator(
    step_functions_client=sfn,
    state_machine_arn='arn:aws:states:us-east-1:123:stateMachine:news-pipeline'
)

execution = orchestrator.start_execution(sources, execution_name='my-run')
print(f"Started: {execution['execution_arn']}")
```

### Check Status
```python
status = orchestrator.get_execution_status(execution['execution_arn'])
print(f"Status: {status['status']}")
```

### Retry Queue
```python
from src.pipeline.sqs_retry_queue import SQSRetryQueue
import boto3

sqs = boto3.client('sqs')
retry_queue = SQSRetryQueue(
    sqs_client=sqs,
    retry_queue_url='https://sqs.us-east-1.amazonaws.com/123/retry',
    dlq_url='https://sqs.us-east-1.amazonaws.com/123/dlq',
    max_retries=3
)

# Send to retry
retry_queue.send_to_retry_queue(failed_source, error='Timeout', retry_count=0)

# Check circuit breakers
status = retry_queue.get_circuit_breaker_status()
```

### ECS Tasks
```python
from src.pipeline.ecs_config import ECSTaskConfigurator
import boto3

ecs = boto3.client('ecs')
configurator = ECSTaskConfigurator(ecs_client=ecs)

# Create definitions
embed_def = configurator.create_embed_cluster_task_definition()
bias_def = configurator.create_bias_score_task_definition()

# Register
embed_arn = configurator.register_task_definition(embed_def)
```

## Environment Variables

```bash
# AWS Configuration
AWS_REGION=us-east-1
STEP_FUNCTIONS_STATE_MACHINE_ARN=arn:aws:states:...
MAIN_QUEUE_URL=https://sqs...
RETRY_QUEUE_URL=https://sqs...
DLQ_URL=https://sqs...
PIPELINE_BUCKET=news-pipeline-bucket
ARTICLES_TABLE=news-articles

# ECS Configuration
ECS_CLUSTER_ARN=arn:aws:ecs:...
SUBNET_IDS=subnet-xxx,subnet-yyy
SECURITY_GROUP_IDS=sg-xxx

# API Keys
OPENAI_API_KEY=sk-...
VALYU_API_KEY=...
NEWS_API_KEY=...
```

## Source Configuration Template

```yaml
sources:
  - type: rss  # or 'url' or 'api'
    url: "https://example.com/rss"
    name: "Source Name"
    tags:
      region: "global"  # or asia, middle_east, north_america, etc.
      state_aligned: false
      independent: true
      diaspora: false
      language: "en"
    refresh_interval: 1800  # seconds
```

## Pipeline Stages

1. **FetchArticles** (Lambda) - Fetch from sources
2. **NormalizeContent** (Lambda) - Clean and normalize
3. **EmbedAndCluster** (ECS+GPU) - Generate embeddings
4. **BiasScoreAndExplain** (ECS+GPU+Valyu) - Score bias
5. **StoreResults** (Lambda) - Save to DB/S3

## Circuit Breaker States

- **CLOSED**: Normal operation
- **OPEN**: Failing, reject requests
- **HALF_OPEN**: Testing recovery

## AWS Resources Checklist

- [ ] S3 bucket created
- [ ] DynamoDB table created
- [ ] SQS queues created (main, retry, DLQ)
- [ ] ECR repositories created
- [ ] ECS cluster created
- [ ] Lambda functions deployed
- [ ] ECS task definitions registered
- [ ] Step Functions state machine created
- [ ] IAM roles configured
- [ ] Secrets stored in Secrets Manager
- [ ] CloudWatch log groups created

## Monitoring

### CloudWatch Logs
```
/aws/lambda/news-pipeline-fetch-articles
/aws/lambda/news-pipeline-normalize-content
/aws/lambda/news-pipeline-store-results
/ecs/news-pipeline-embed-cluster
/ecs/news-pipeline-bias-score
```

### Key Metrics
- Step Functions execution success rate
- Lambda invocation count/errors
- SQS queue depth
- DLQ message count
- ECS task success/failure
- Circuit breaker states

## Troubleshooting

### Pipeline Not Starting
1. Check Step Functions state machine ARN
2. Verify IAM permissions
3. Check Lambda function deployments

### Lambda Timeout
1. Increase timeout (max 900s)
2. Reduce batch size
3. Check external API response times

### ECS Task Failures
1. Check CloudWatch logs
2. Verify GPU availability
3. Check memory/CPU limits
4. Validate API keys

### Circuit Breaker Open
1. Check source availability
2. Review error logs
3. Adjust failure threshold if needed
4. Manually reset if required

## Cost Optimization Tips

1. Use Fargate Spot for non-critical workloads
2. Configure auto-scaling for ECS tasks
3. Set appropriate Lambda memory sizes
4. Use S3 lifecycle policies
5. Monitor and adjust DynamoDB capacity
6. Use reserved capacity where applicable

## Documentation Links

- **Complete Guide**: `PIPELINE_README.md`
- **Deployment**: `DEPLOYMENT_GUIDE.md`
- **Implementation**: `IMPLEMENTATION_SUMMARY.md`
- **Examples**: `example_pipeline_usage.py`
- **Tests**: `tests/test_pipeline.py`

## Support

1. Check documentation files
2. Review CloudWatch logs
3. Inspect circuit breaker states
4. Run test suite
5. Validate source configurations

## Key Classes

| Class | File | Purpose |
|-------|------|---------|
| `SourceConfigLoader` | `source_config_loader.py` | Load/filter sources |
| `PipelineOrchestrator` | `orchestrator.py` | Manage Step Functions |
| `SQSRetryQueue` | `sqs_retry_queue.py` | Retry + circuit breaker |
| `ECSTaskConfigurator` | `ecs_config.py` | ECS task management |

## Lambda Handlers

| Handler | Purpose |
|---------|---------|
| `fetch_articles_handler` | Fetch from sources |
| `normalize_content_handler` | Clean content |
| `embed_and_cluster_handler` | Entry for ECS |
| `bias_score_handler` | Entry for ECS |
| `store_results_handler` | Save results |

## Quick Deploy Checklist

1. ✅ Install dependencies: `pip install -r requirements.txt`
2. ✅ Configure sources: Edit `config/sources.yaml`
3. ✅ Set environment variables in `.env`
4. ✅ Create AWS infrastructure (see DEPLOYMENT_GUIDE.md)
5. ✅ Deploy Lambda functions
6. ✅ Build and push Docker images
7. ✅ Register ECS task definitions
8. ✅ Create Step Functions state machine
9. ✅ Store secrets in Secrets Manager
10. ✅ Test with example: `python example_pipeline_usage.py`
