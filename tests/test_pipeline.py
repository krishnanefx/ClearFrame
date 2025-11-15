"""
Integration tests for AWS data pipeline.
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from src.pipeline.source_config_loader import SourceConfigLoader
from src.pipeline.orchestrator import PipelineOrchestrator
from src.pipeline.sqs_retry_queue import SQSRetryQueue, CircuitState
from src.pipeline.ecs_config import ECSTaskConfigurator
from src.pipeline.lambda_handlers import (
    _fetch_from_rss,
    _normalize_article,
    _simple_bias_score
)


class TestSourceConfigLoader:
    """Test source configuration loading."""
    
    def test_load_yaml_config(self):
        """Test loading YAML configuration."""
        loader = SourceConfigLoader('./config/sources.yaml')
        sources = loader.get_all_sources()
        
        assert len(sources) > 0
        assert all('type' in s for s in sources)
        assert all('tags' in s for s in sources)
    
    def test_load_json_config(self):
        """Test loading JSON configuration."""
        loader = SourceConfigLoader('./config/sources.json')
        sources = loader.get_all_sources()
        
        assert len(sources) > 0
        assert all('type' in s for s in sources)
    
    def test_filter_by_tags(self):
        """Test filtering sources by tags."""
        loader = SourceConfigLoader('./config/sources.yaml')
        
        # Filter by language
        en_sources = loader.get_sources_by_language('en')
        assert all(s['tags']['language'] == 'en' for s in en_sources)
        
        # Filter by independent
        independent = loader.get_independent_sources()
        assert all(s['tags']['independent'] for s in independent)
    
    def test_get_diaspora_sources(self):
        """Test getting diaspora sources."""
        loader = SourceConfigLoader('./config/sources.yaml')
        diaspora = loader.get_diaspora_sources()
        
        # Should have at least one diaspora source in config
        assert len(diaspora) >= 1
        assert all(s['tags']['diaspora'] for s in diaspora)
    
    def test_validate_sources(self):
        """Test source validation."""
        loader = SourceConfigLoader('./config/sources.yaml')
        validation = loader.validate_sources()
        
        assert 'valid' in validation
        assert 'invalid' in validation
        assert isinstance(validation['valid'], list)
        assert isinstance(validation['invalid'], list)


class TestPipelineOrchestrator:
    """Test pipeline orchestration."""
    
    def test_create_state_machine_definition(self):
        """Test Step Functions state machine definition."""
        orchestrator = PipelineOrchestrator()
        definition = orchestrator.create_state_machine_definition()
        
        assert 'StartAt' in definition
        assert 'States' in definition
        assert definition['StartAt'] == 'FetchArticles'
        
        # Check all stages present
        stages = ['FetchArticles', 'NormalizeContent', 'EmbedAndCluster', 
                 'BiasScoreAndExplain', 'StoreResults']
        for stage in stages:
            assert stage in definition['States']
    
    @patch('boto3.client')
    def test_start_execution(self, mock_boto_client):
        """Test starting a pipeline execution."""
        mock_sfn = MagicMock()
        mock_sfn.start_execution.return_value = {
            'executionArn': 'arn:aws:states:us-east-1:123:execution:test',
            'startDate': '2024-01-01T00:00:00Z'
        }
        
        orchestrator = PipelineOrchestrator(
            step_functions_client=mock_sfn,
            state_machine_arn='arn:aws:states:us-east-1:123:stateMachine:test'
        )
        
        sources = [{'type': 'rss', 'url': 'https://example.com/rss'}]
        execution = orchestrator.start_execution(sources)
        
        assert 'execution_arn' in execution
        assert execution['status'] == 'RUNNING'
        mock_sfn.start_execution.assert_called_once()
    
    @patch('boto3.client')
    def test_get_execution_status(self, mock_boto_client):
        """Test getting execution status."""
        mock_sfn = MagicMock()
        mock_sfn.describe_execution.return_value = {
            'executionArn': 'arn:aws:states:us-east-1:123:execution:test',
            'status': 'SUCCEEDED',
            'startDate': '2024-01-01T00:00:00Z',
            'stopDate': '2024-01-01T00:05:00Z',
            'input': '{}',
            'output': '{"result": "success"}'
        }
        
        orchestrator = PipelineOrchestrator(step_functions_client=mock_sfn)
        status = orchestrator.get_execution_status('arn:...')
        
        assert status['status'] == 'SUCCEEDED'
        assert 'start_date' in status
        assert 'stop_date' in status


class TestSQSRetryQueue:
    """Test SQS retry queue with circuit breaker."""
    
    def test_calculate_backoff_delay(self):
        """Test exponential backoff calculation."""
        retry_queue = SQSRetryQueue(max_retries=3, base_delay=2)
        
        assert retry_queue._calculate_backoff_delay(0) == 2
        assert retry_queue._calculate_backoff_delay(1) == 4
        assert retry_queue._calculate_backoff_delay(2) == 8
        assert retry_queue._calculate_backoff_delay(10) == 900  # Capped at 15 min
    
    def test_circuit_breaker_closed(self):
        """Test circuit breaker in CLOSED state."""
        retry_queue = SQSRetryQueue()
        
        # New source should have closed circuit
        assert retry_queue._check_circuit_breaker('test-source')
    
    def test_circuit_breaker_opens_on_failures(self):
        """Test circuit breaker opens after threshold failures."""
        retry_queue = SQSRetryQueue()
        source_name = 'failing-source'
        
        # Record failures up to threshold
        for _ in range(5):
            retry_queue._record_failure(source_name)
        
        breaker = retry_queue.circuit_breakers[source_name]
        assert breaker['state'] == CircuitState.OPEN
    
    def test_circuit_breaker_closes_on_success(self):
        """Test circuit breaker closes after success in HALF_OPEN."""
        retry_queue = SQSRetryQueue()
        source_name = 'recovering-source'
        
        # Initialize and set to HALF_OPEN
        retry_queue._init_circuit_breaker(source_name)
        retry_queue.circuit_breakers[source_name]['state'] = CircuitState.HALF_OPEN
        
        # Record successes
        retry_queue._record_success(source_name)
        retry_queue._record_success(source_name)
        
        breaker = retry_queue.circuit_breakers[source_name]
        assert breaker['state'] == CircuitState.CLOSED
    
    @patch('boto3.client')
    def test_send_to_retry_queue(self, mock_boto_client):
        """Test sending message to retry queue."""
        mock_sqs = MagicMock()
        mock_sqs.send_message.return_value = {'MessageId': '123'}
        
        retry_queue = SQSRetryQueue(
            sqs_client=mock_sqs,
            retry_queue_url='https://sqs.us-east-1.amazonaws.com/123/retry',
            max_retries=3
        )
        
        source = {'name': 'test', 'type': 'rss', 'url': 'https://example.com'}
        retry_queue.send_to_retry_queue(source, 'Timeout', retry_count=0)
        
        mock_sqs.send_message.assert_called_once()
        call_args = mock_sqs.send_message.call_args[1]
        assert 'MessageBody' in call_args
        
        body = json.loads(call_args['MessageBody'])
        assert body['retry_count'] == 1
        assert body['error'] == 'Timeout'


class TestECSTaskConfigurator:
    """Test ECS task configuration."""
    
    def test_create_embed_cluster_task_definition(self):
        """Test creating embed & cluster task definition."""
        configurator = ECSTaskConfigurator()
        task_def = configurator.create_embed_cluster_task_definition()
        
        assert task_def['family'] == 'news-pipeline-embed-cluster'
        assert task_def['cpu'] == '4096'
        assert task_def['memory'] == '16384'
        assert len(task_def['containerDefinitions']) == 1
        
        container = task_def['containerDefinitions'][0]
        assert container['name'] == 'embed-cluster-container'
        
        # Check GPU requirement
        gpu_reqs = [r for r in container['resourceRequirements'] if r['type'] == 'GPU']
        assert len(gpu_reqs) == 1
        assert gpu_reqs[0]['value'] == '1'
    
    def test_create_bias_score_task_definition(self):
        """Test creating bias score task definition."""
        configurator = ECSTaskConfigurator()
        task_def = configurator.create_bias_score_task_definition()
        
        assert task_def['family'] == 'news-pipeline-bias-score'
        assert task_def['cpu'] == '4096'
        assert task_def['memory'] == '16384'
        
        container = task_def['containerDefinitions'][0]
        assert container['name'] == 'bias-score-container'
        
        # Check for Valyu API key in secrets
        secrets = container['secrets']
        valyu_secret = [s for s in secrets if s['name'] == 'VALYU_API_KEY']
        assert len(valyu_secret) == 1


class TestLambdaHandlers:
    """Test Lambda handler functions."""
    
    @patch('feedparser.parse')
    def test_fetch_from_rss(self, mock_feedparser):
        """Test fetching articles from RSS feed."""
        mock_feedparser.return_value = {
            'entries': [
                {
                    'title': 'Test Article',
                    'link': 'https://example.com/article',
                    'summary': 'Test summary',
                    'published': '2024-01-01'
                }
            ]
        }
        
        source = {
            'type': 'rss',
            'url': 'https://example.com/rss',
            'name': 'Test Source',
            'tags': {'region': 'global', 'language': 'en'}
        }
        
        articles = _fetch_from_rss(source)
        
        assert len(articles) == 1
        assert articles[0]['title'] == 'Test Article'
        assert articles[0]['source'] == 'Test Source'
    
    def test_normalize_article(self):
        """Test article normalization."""
        article = {
            'title': '  Test Article  ',
            'content': 'Test content',
            'raw_html': '<p>Test <b>content</b></p>',
            'source': 'Test Source',
            'source_tags': {'region': 'global'}
        }
        
        normalized = _normalize_article(article)
        
        assert normalized['title'] == 'Test Article'
        assert 'id' in normalized
        assert 'content_hash' in normalized
        assert 'detected_language' in normalized
        assert normalized['word_count'] > 0
    
    def test_simple_bias_score(self):
        """Test simple bias scoring."""
        # State-aligned source
        article1 = {
            'source_tags': {'state_aligned': True, 'independent': False}
        }
        score1 = _simple_bias_score(article1)
        assert 0.5 < score1 <= 1.0
        
        # Independent source
        article2 = {
            'source_tags': {'state_aligned': False, 'independent': True}
        }
        score2 = _simple_bias_score(article2)
        assert 0.0 <= score2 < 0.5


class TestEndToEndPipeline:
    """End-to-end pipeline integration tests."""
    
    def test_complete_pipeline_workflow(self):
        """Test complete pipeline workflow without AWS."""
        # Step 1: Load sources
        loader = SourceConfigLoader('./config/sources.yaml')
        sources = loader.get_sources_by_language('en')[:5]  # Limit to 5
        
        assert len(sources) > 0
        
        # Step 2: Validate sources
        validation = loader.validate_sources()
        assert len(validation['valid']) > 0
        
        # Step 3: Create state machine definition
        orchestrator = PipelineOrchestrator()
        definition = orchestrator.create_state_machine_definition()
        
        assert 'FetchArticles' in definition['States']
        assert 'StoreResults' in definition['States']
        
        # Step 4: Initialize retry queue (without AWS)
        retry_queue = SQSRetryQueue(max_retries=3)
        
        # Step 5: Simulate circuit breaker
        retry_queue._init_circuit_breaker('test-source')
        assert retry_queue._check_circuit_breaker('test-source')
        
        # Step 6: Create ECS task definitions
        configurator = ECSTaskConfigurator()
        embed_task = configurator.create_embed_cluster_task_definition()
        bias_task = configurator.create_bias_score_task_definition()
        
        assert embed_task['family'] == 'news-pipeline-embed-cluster'
        assert bias_task['family'] == 'news-pipeline-bias-score'
    
    def test_pipeline_with_mock_aws(self):
        """Test pipeline with mocked AWS services."""
        with patch('boto3.client') as mock_boto:
            # Mock Step Functions
            mock_sfn = MagicMock()
            mock_sfn.start_execution.return_value = {
                'executionArn': 'arn:aws:states:us-east-1:123:execution:test',
                'startDate': '2024-01-01T00:00:00Z'
            }
            
            # Mock SQS
            mock_sqs = MagicMock()
            mock_sqs.send_message.return_value = {'MessageId': '123'}
            
            # Mock ECS
            mock_ecs = MagicMock()
            mock_ecs.register_task_definition.return_value = {
                'taskDefinition': {
                    'taskDefinitionArn': 'arn:aws:ecs:us-east-1:123:task-definition/test:1'
                }
            }
            
            mock_boto.side_effect = lambda service, **kwargs: {
                'stepfunctions': mock_sfn,
                'sqs': mock_sqs,
                'ecs': mock_ecs
            }.get(service)
            
            # Load sources
            loader = SourceConfigLoader('./config/sources.yaml')
            sources = loader.get_all_sources()[:3]
            
            # Start pipeline
            sfn = mock_boto('stepfunctions')
            orchestrator = PipelineOrchestrator(
                step_functions_client=sfn,
                state_machine_arn='arn:aws:states:us-east-1:123:stateMachine:test'
            )
            
            execution = orchestrator.start_execution(sources)
            
            assert execution['status'] == 'RUNNING'
            assert 'execution_arn' in execution


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
