"""AWS Step Functions orchestrator for news pipeline."""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """
    Orchestrates the AWS Step Functions pipeline for news ingestion.
    
    Pipeline stages:
    1. FetchArticles - Lambda + ECS tasks for scraping with retry/backoff
    2. NormalizeContent - Language detection, HTML stripping
    3. EmbedAndCluster - Generate embeddings and cluster articles
    4. BiasScoreAndExplain - Calculate bias scores with explanations
    5. StoreResults - Store processed articles
    """
    
    def __init__(self, 
                 step_functions_client=None,
                 state_machine_arn: Optional[str] = None):
        """
        Initialize the pipeline orchestrator.
        
        Args:
            step_functions_client: Boto3 Step Functions client
            state_machine_arn: ARN of the Step Functions state machine
        """
        self.sfn_client = step_functions_client
        self.state_machine_arn = state_machine_arn
        self.execution_history: List[Dict[str, Any]] = []
    
    def create_state_machine_definition(self) -> Dict[str, Any]:
        """
        Create the Step Functions state machine definition.
        
        Returns:
            State machine definition as a dictionary
        """
        return {
            "Comment": "News ingestion and processing pipeline",
            "StartAt": "FetchArticles",
            "States": {
                "FetchArticles": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::lambda:invoke",
                    "Parameters": {
                        "FunctionName": "${FetchArticlesLambdaArn}",
                        "Payload": {
                            "sources.$": "$.sources",
                            "execution_id.$": "$.execution_id",
                            "batch_size": 50
                        }
                    },
                    "ResultPath": "$.fetch_result",
                    "Retry": [
                        {
                            "ErrorEquals": ["States.TaskFailed", "Lambda.ServiceException"],
                            "IntervalSeconds": 2,
                            "MaxAttempts": 3,
                            "BackoffRate": 2.0
                        }
                    ],
                    "Catch": [
                        {
                            "ErrorEquals": ["States.ALL"],
                            "ResultPath": "$.error",
                            "Next": "HandleFetchError"
                        }
                    ],
                    "Next": "CheckFetchResults"
                },
                "CheckFetchResults": {
                    "Type": "Choice",
                    "Choices": [
                        {
                            "Variable": "$.fetch_result.Payload.article_count",
                            "NumericGreaterThan": 0,
                            "Next": "NormalizeContent"
                        }
                    ],
                    "Default": "NoArticlesFetched"
                },
                "NormalizeContent": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::lambda:invoke",
                    "Parameters": {
                        "FunctionName": "${NormalizeContentLambdaArn}",
                        "Payload": {
                            "articles.$": "$.fetch_result.Payload.articles",
                            "execution_id.$": "$.execution_id"
                        }
                    },
                    "ResultPath": "$.normalize_result",
                    "Retry": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "IntervalSeconds": 2,
                            "MaxAttempts": 3,
                            "BackoffRate": 2.0
                        }
                    ],
                    "Next": "EmbedAndCluster"
                },
                "EmbedAndCluster": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::ecs:runTask.sync",
                    "Parameters": {
                        "Cluster": "${ECSClusterArn}",
                        "TaskDefinition": "${EmbedClusterTaskDefinition}",
                        "LaunchType": "FARGATE",
                        "NetworkConfiguration": {
                            "AwsvpcConfiguration": {
                                "Subnets": ["${SubnetId}"],
                                "SecurityGroups": ["${SecurityGroupId}"],
                                "AssignPublicIp": "ENABLED"
                            }
                        },
                        "Overrides": {
                            "ContainerOverrides": [
                                {
                                    "Name": "embed-cluster-container",
                                    "Environment": [
                                        {
                                            "Name": "ARTICLES_S3_KEY",
                                            "Value.$": "$.normalize_result.Payload.s3_key"
                                        },
                                        {
                                            "Name": "EXECUTION_ID",
                                            "Value.$": "$.execution_id"
                                        }
                                    ]
                                }
                            ]
                        }
                    },
                    "ResultPath": "$.embed_result",
                    "Retry": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "IntervalSeconds": 5,
                            "MaxAttempts": 2,
                            "BackoffRate": 2.0
                        }
                    ],
                    "Next": "BiasScoreAndExplain"
                },
                "BiasScoreAndExplain": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::ecs:runTask.sync",
                    "Parameters": {
                        "Cluster": "${ECSClusterArn}",
                        "TaskDefinition": "${BiasScoreTaskDefinition}",
                        "LaunchType": "FARGATE",
                        "NetworkConfiguration": {
                            "AwsvpcConfiguration": {
                                "Subnets": ["${SubnetId}"],
                                "SecurityGroups": ["${SecurityGroupId}"],
                                "AssignPublicIp": "ENABLED"
                            }
                        },
                        "Overrides": {
                            "ContainerOverrides": [
                                {
                                    "Name": "bias-score-container",
                                    "Environment": [
                                        {
                                            "Name": "CLUSTERS_S3_KEY",
                                            "Value.$": "$.embed_result.Output.s3_key"
                                        },
                                        {
                                            "Name": "EXECUTION_ID",
                                            "Value.$": "$.execution_id"
                                        },
                                        {
                                            "Name": "VALYU_API_KEY",
                                            "Value": "${ValyuApiKey}"
                                        }
                                    ]
                                }
                            ]
                        }
                    },
                    "ResultPath": "$.bias_result",
                    "Retry": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "IntervalSeconds": 5,
                            "MaxAttempts": 2,
                            "BackoffRate": 2.0
                        }
                    ],
                    "Next": "StoreResults"
                },
                "StoreResults": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::lambda:invoke",
                    "Parameters": {
                        "FunctionName": "${StoreResultsLambdaArn}",
                        "Payload": {
                            "bias_scores_s3_key.$": "$.bias_result.Output.s3_key",
                            "execution_id.$": "$.execution_id",
                            "metadata.$": "$"
                        }
                    },
                    "ResultPath": "$.store_result",
                    "Retry": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "IntervalSeconds": 2,
                            "MaxAttempts": 3,
                            "BackoffRate": 2.0
                        }
                    ],
                    "Next": "PipelineSuccess"
                },
                "HandleFetchError": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::sns:publish",
                    "Parameters": {
                        "TopicArn": "${ErrorNotificationTopicArn}",
                        "Message": {
                            "error": "Failed to fetch articles",
                            "details.$": "$.error"
                        }
                    },
                    "Next": "PipelineFailed"
                },
                "NoArticlesFetched": {
                    "Type": "Succeed",
                    "Comment": "No articles to process"
                },
                "PipelineSuccess": {
                    "Type": "Succeed",
                    "Comment": "Pipeline completed successfully"
                },
                "PipelineFailed": {
                    "Type": "Fail",
                    "Error": "PipelineExecutionFailed",
                    "Cause": "One or more pipeline stages failed"
                }
            }
        }
    
    def start_execution(self, 
                       sources: List[Dict[str, Any]],
                       execution_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Start a pipeline execution.
        
        Args:
            sources: List of source configurations to process
            execution_name: Optional name for the execution
            
        Returns:
            Execution details including ARN and start time
        """
        if not self.sfn_client or not self.state_machine_arn:
            raise ValueError("Step Functions client and state machine ARN required")
        
        if not execution_name:
            execution_name = f"pipeline-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        
        execution_id = f"{execution_name}-{datetime.utcnow().timestamp()}"
        
        input_payload = {
            "sources": sources,
            "execution_id": execution_id,
            "start_time": datetime.utcnow().isoformat()
        }
        
        try:
            response = self.sfn_client.start_execution(
                stateMachineArn=self.state_machine_arn,
                name=execution_name,
                input=json.dumps(input_payload)
            )
            
            execution_info = {
                "execution_arn": response['executionArn'],
                "execution_id": execution_id,
                "start_date": response['startDate'].isoformat(),
                "status": "RUNNING"
            }
            
            self.execution_history.append(execution_info)
            logger.info(f"Started pipeline execution: {execution_name}")
            
            return execution_info
            
        except Exception as e:
            logger.error(f"Failed to start execution: {e}")
            raise
    
    def get_execution_status(self, execution_arn: str) -> Dict[str, Any]:
        """
        Get the status of a pipeline execution.
        
        Args:
            execution_arn: ARN of the execution
            
        Returns:
            Execution status and details
        """
        if not self.sfn_client:
            raise ValueError("Step Functions client required")
        
        try:
            response = self.sfn_client.describe_execution(
                executionArn=execution_arn
            )
            
            return {
                "execution_arn": response['executionArn'],
                "status": response['status'],
                "start_date": response['startDate'].isoformat(),
                "stop_date": response.get('stopDate', '').isoformat() if response.get('stopDate') else None,
                "input": json.loads(response.get('input', '{}')),
                "output": json.loads(response.get('output', '{}')) if response.get('output') else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get execution status: {e}")
            raise
    
    def stop_execution(self, execution_arn: str, error: str = "Manual stop") -> None:
        """
        Stop a running pipeline execution.
        
        Args:
            execution_arn: ARN of the execution to stop
            error: Error message for the stop
        """
        if not self.sfn_client:
            raise ValueError("Step Functions client required")
        
        try:
            self.sfn_client.stop_execution(
                executionArn=execution_arn,
                error="ExecutionStopped",
                cause=error
            )
            logger.info(f"Stopped execution: {execution_arn}")
            
        except Exception as e:
            logger.error(f"Failed to stop execution: {e}")
            raise
    
    def get_execution_history_details(self, execution_arn: str) -> List[Dict[str, Any]]:
        """
        Get detailed execution history.
        
        Args:
            execution_arn: ARN of the execution
            
        Returns:
            List of execution events
        """
        if not self.sfn_client:
            raise ValueError("Step Functions client required")
        
        try:
            events = []
            next_token = None
            
            while True:
                kwargs = {"executionArn": execution_arn}
                if next_token:
                    kwargs["nextToken"] = next_token
                
                response = self.sfn_client.get_execution_history(**kwargs)
                events.extend(response['events'])
                
                next_token = response.get('nextToken')
                if not next_token:
                    break
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to get execution history: {e}")
            raise
