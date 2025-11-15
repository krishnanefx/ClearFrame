# AWS Data Pipeline Deployment Guide

## Overview

This guide covers deploying the AWS-heavy, Valyu-powered data pipeline for news ingestion and processing.

## Architecture Components

### 1. Source Configuration (YAML/JSON)
- **Location**: `config/sources.yaml` or `config/sources.json`
- **Purpose**: Define news sources with tags (region, state_aligned, independent, diaspora, language)
- **Storage**: Git repository for version control

### 2. AWS Step Functions Orchestrator
- **Stages**:
  1. FetchArticles (Lambda)
  2. NormalizeContent (Lambda)
  3. EmbedAndCluster (ECS Fargate with GPU)
  4. BiasScoreAndExplain (ECS Fargate with GPU + Valyu API)
  5. StoreResults (Lambda)

### 3. AWS Lambda Functions
- **FetchArticles**: Scrape RSS, URLs, APIs with retry/backoff
- **NormalizeContent**: Language detection, HTML stripping
- **StoreResults**: Save to DynamoDB/S3

### 4. SQS Queues
- **Main Queue**: Primary processing queue
- **Retry Queue**: Failed sources with exponential backoff
- **Dead Letter Queue (DLQ)**: Failed after max retries
- **Circuit Breaker**: Prevents cascading failures

### 5. ECS Fargate Tasks
- **EmbedAndCluster**: GPU-accelerated embedding generation and clustering
- **BiasScore**: GPU-accelerated bias scoring with Valyu API

## Prerequisites

### AWS Services
- AWS CLI configured with appropriate credentials
- AWS Account with permissions for:
  - Step Functions
  - Lambda
  - ECS/Fargate
  - SQS
  - S3
  - DynamoDB
  - CloudWatch
  - ECR (for container images)
  - IAM (for roles and policies)

### API Keys
- OpenAI API key (for embeddings)
- Valyu API key (for bias scoring)
- NewsAPI key (optional, for API sources)

## Deployment Steps

### Step 1: Set Up Infrastructure

#### 1.1 Create S3 Bucket
```bash
aws s3 mb s3://news-pipeline-bucket --region us-east-1
```

#### 1.2 Create DynamoDB Table
```bash
aws dynamodb create-table \
  --table-name news-articles \
  --attribute-definitions \
    AttributeName=id,AttributeType=S \
    AttributeName=published_date,AttributeType=S \
  --key-schema \
    AttributeName=id,KeyType=HASH \
  --global-secondary-indexes \
    IndexName=DateIndex,KeySchema=[{AttributeName=published_date,KeyType=HASH}],Projection={ProjectionType=ALL},ProvisionedThroughput={ReadCapacityUnits=5,WriteCapacityUnits=5} \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
  --region us-east-1
```

#### 1.3 Create SQS Queues
```bash
# Main queue
aws sqs create-queue --queue-name news-pipeline-main-queue --region us-east-1

# Retry queue
aws sqs create-queue \
  --queue-name news-pipeline-retry-queue \
  --attributes VisibilityTimeout=900,MessageRetentionPeriod=1209600 \
  --region us-east-1

# Dead letter queue
aws sqs create-queue --queue-name news-pipeline-dlq --region us-east-1
```

#### 1.4 Deploy ECS Infrastructure
```bash
# Deploy CloudFormation stack
python -c "
from src.pipeline.ecs_config import generate_cloudformation_template
import json
template = generate_cloudformation_template()
with open('ecs-infrastructure.json', 'w') as f:
    json.dump(template, f, indent=2)
"

aws cloudformation create-stack \
  --stack-name news-pipeline-ecs \
  --template-body file://ecs-infrastructure.json \
  --parameters \
    ParameterKey=VpcId,ParameterValue=vpc-xxxxx \
    ParameterKey=SubnetIds,ParameterValue=subnet-xxxxx,subnet-yyyyy \
    ParameterKey=ECRRepositoryUri,ParameterValue=123456789.dkr.ecr.us-east-1.amazonaws.com/news-pipeline \
  --capabilities CAPABILITY_IAM \
  --region us-east-1
```

### Step 2: Build and Push Container Images

#### 2.1 Create ECR Repository
```bash
aws ecr create-repository \
  --repository-name news-pipeline/embed-cluster \
  --region us-east-1

aws ecr create-repository \
  --repository-name news-pipeline/bias-score \
  --region us-east-1
```

#### 2.2 Build and Push Images
```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com

# Build embed-cluster image
cd src/pipeline/docker
docker build -t news-pipeline/embed-cluster:latest -f Dockerfile.embed-cluster .
docker tag news-pipeline/embed-cluster:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/news-pipeline/embed-cluster:latest
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/news-pipeline/embed-cluster:latest

# Build bias-score image
docker build -t news-pipeline/bias-score:latest -f Dockerfile.bias-score .
docker tag news-pipeline/bias-score:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/news-pipeline/bias-score:latest
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/news-pipeline/bias-score:latest
```

### Step 3: Deploy Lambda Functions

#### 3.1 Package Lambda Functions
```bash
# Create deployment package
cd src/pipeline
pip install -r ../../requirements.txt -t ./package
cd package
zip -r ../lambda-deployment.zip .
cd ..
zip -g lambda-deployment.zip lambda_handlers.py
```

#### 3.2 Create Lambda Functions
```bash
# FetchArticles Lambda
aws lambda create-function \
  --function-name news-pipeline-fetch-articles \
  --runtime python3.11 \
  --handler lambda_handlers.fetch_articles_handler \
  --role arn:aws:iam::123456789:role/lambda-execution-role \
  --zip-file fileb://lambda-deployment.zip \
  --timeout 300 \
  --memory-size 512 \
  --environment Variables={PIPELINE_BUCKET=news-pipeline-bucket,RETRY_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/123456789/news-pipeline-retry-queue} \
  --region us-east-1

# NormalizeContent Lambda
aws lambda create-function \
  --function-name news-pipeline-normalize-content \
  --runtime python3.11 \
  --handler lambda_handlers.normalize_content_handler \
  --role arn:aws:iam::123456789:role/lambda-execution-role \
  --zip-file fileb://lambda-deployment.zip \
  --timeout 300 \
  --memory-size 1024 \
  --environment Variables={PIPELINE_BUCKET=news-pipeline-bucket} \
  --region us-east-1

# StoreResults Lambda
aws lambda create-function \
  --function-name news-pipeline-store-results \
  --runtime python3.11 \
  --handler lambda_handlers.store_results_handler \
  --role arn:aws:iam::123456789:role/lambda-execution-role \
  --zip-file fileb://lambda-deployment.zip \
  --timeout 300 \
  --memory-size 512 \
  --environment Variables={PIPELINE_BUCKET=news-pipeline-bucket,ARTICLES_TABLE=news-articles} \
  --region us-east-1
```

### Step 4: Register ECS Task Definitions

```bash
# Register embed-cluster task
python -c "
from src.pipeline.ecs_config import ECSTaskConfigurator
import boto3
import json
client = boto3.client('ecs', region_name='us-east-1')
config = ECSTaskConfigurator(client)
task_def = config.create_embed_cluster_task_definition()
# Substitute placeholders with actual values
with open('embed-task-def.json', 'w') as f:
    json.dump(task_def, f, indent=2)
"

# Edit embed-task-def.json to replace placeholders, then:
aws ecs register-task-definition --cli-input-json file://embed-task-def.json

# Repeat for bias-score task
```

### Step 5: Create Step Functions State Machine

```bash
# Generate state machine definition
python -c "
from src.pipeline.orchestrator import PipelineOrchestrator
import json
orchestrator = PipelineOrchestrator()
definition = orchestrator.create_state_machine_definition()
with open('state-machine.json', 'w') as f:
    json.dump(definition, f, indent=2)
"

# Edit state-machine.json to replace placeholders, then:
aws stepfunctions create-state-machine \
  --name news-pipeline \
  --definition file://state-machine.json \
  --role-arn arn:aws:iam::123456789:role/step-functions-execution-role \
  --region us-east-1
```

### Step 6: Configure Secrets

```bash
# Store API keys in Secrets Manager
aws secretsmanager create-secret \
  --name news-pipeline/openai-api-key \
  --secret-string "your-openai-api-key" \
  --region us-east-1

aws secretsmanager create-secret \
  --name news-pipeline/valyu-api-key \
  --secret-string "your-valyu-api-key" \
  --region us-east-1

aws secretsmanager create-secret \
  --name news-pipeline/news-api-key \
  --secret-string "your-news-api-key" \
  --region us-east-1
```

### Step 7: Configure Environment

Create `.env` file:
```bash
# AWS Configuration
AWS_REGION=us-east-1
STEP_FUNCTIONS_STATE_MACHINE_ARN=arn:aws:states:us-east-1:123456789:stateMachine:news-pipeline
MAIN_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/123456789/news-pipeline-main-queue
RETRY_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/123456789/news-pipeline-retry-queue
DLQ_URL=https://sqs.us-east-1.amazonaws.com/123456789/news-pipeline-dlq
PIPELINE_BUCKET=news-pipeline-bucket
ARTICLES_TABLE=news-articles

# ECS Configuration
ECS_CLUSTER_ARN=arn:aws:ecs:us-east-1:123456789:cluster/news-pipeline-cluster
SUBNET_IDS=subnet-xxxxx,subnet-yyyyy
SECURITY_GROUP_IDS=sg-xxxxx

# API Keys
OPENAI_API_KEY=your-openai-api-key
VALYU_API_KEY=your-valyu-api-key
NEWS_API_KEY=your-news-api-key
```

## Usage

### Start a Pipeline Execution

```python
from src.pipeline.source_config_loader import SourceConfigLoader
from src.pipeline.orchestrator import PipelineOrchestrator
import boto3

# Load sources
loader = SourceConfigLoader('./config/sources.yaml')
sources = loader.get_all_sources()

# Start pipeline
sfn_client = boto3.client('stepfunctions')
orchestrator = PipelineOrchestrator(
    step_functions_client=sfn_client,
    state_machine_arn='arn:aws:states:us-east-1:123456789:stateMachine:news-pipeline'
)

execution = orchestrator.start_execution(sources)
print(f"Started execution: {execution['execution_arn']}")
```

### Monitor Execution

```python
status = orchestrator.get_execution_status(execution['execution_arn'])
print(f"Status: {status['status']}")
```

## Monitoring and Logging

### CloudWatch Logs
- Lambda logs: `/aws/lambda/news-pipeline-*`
- ECS logs: `/ecs/news-pipeline-*`

### CloudWatch Metrics
- Step Functions execution count
- Lambda invocations and errors
- ECS task success/failure rates
- SQS queue depth

### Alarms
Set up CloudWatch alarms for:
- Failed Step Functions executions
- Lambda errors
- DLQ message count
- ECS task failures

## Cost Optimization

1. **Use Fargate Spot** for non-critical workloads
2. **Configure auto-scaling** for ECS tasks
3. **Set appropriate Lambda memory** to optimize cost/performance
4. **Use S3 lifecycle policies** to archive old data
5. **Monitor and adjust** DynamoDB capacity

## Troubleshooting

### Pipeline Failures
1. Check Step Functions execution history
2. Review CloudWatch logs
3. Check SQS DLQ for failed messages
4. Verify circuit breaker states

### ECS Task Failures
1. Check ECS task logs in CloudWatch
2. Verify GPU availability
3. Check API key validity
4. Ensure sufficient memory/CPU

### Lambda Timeouts
1. Increase Lambda timeout
2. Reduce batch size
3. Check external API response times

## Security Best Practices

1. **Use IAM roles** with least privilege
2. **Encrypt data** in S3 and DynamoDB
3. **Store secrets** in Secrets Manager
4. **Enable VPC** endpoints for AWS services
5. **Use private subnets** for ECS tasks
6. **Enable CloudTrail** for audit logging

## Next Steps

1. Set up CI/CD pipeline for automated deployments
2. Implement monitoring dashboards
3. Configure automated backups
4. Set up disaster recovery procedures
5. Implement cost allocation tags
