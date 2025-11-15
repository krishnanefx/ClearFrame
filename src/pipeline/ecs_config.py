"""ECS/Fargate task definitions and configurations for GPU workloads."""

import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ECSTaskConfigurator:
    """
    Manages ECS/Fargate task definitions for GPU-accelerated workloads.
    Used for embedding generation and bias scoring stages.
    """
    
    def __init__(self, ecs_client=None):
        """
        Initialize ECS task configurator.
        
        Args:
            ecs_client: Boto3 ECS client
        """
        self.ecs_client = ecs_client
    
    def create_embed_cluster_task_definition(self) -> Dict[str, Any]:
        """
        Create ECS task definition for embedding and clustering.
        Requires GPU support for efficient embedding generation.
        
        Returns:
            Task definition configuration
        """
        task_definition = {
            "family": "news-pipeline-embed-cluster",
            "networkMode": "awsvpc",
            "requiresCompatibilities": ["FARGATE"],
            "cpu": "4096",  # 4 vCPU
            "memory": "16384",  # 16 GB
            "executionRoleArn": "${ECSTaskExecutionRoleArn}",
            "taskRoleArn": "${ECSTaskRoleArn}",
            "containerDefinitions": [
                {
                    "name": "embed-cluster-container",
                    "image": "${ECRRepositoryUri}/embed-cluster:latest",
                    "cpu": 4096,
                    "memory": 16384,
                    "essential": True,
                    "environment": [
                        {
                            "name": "PIPELINE_BUCKET",
                            "value": "${PipelineBucket}"
                        },
                        {
                            "name": "AWS_REGION",
                            "value": "${AWS::Region}"
                        },
                        {
                            "name": "MODEL_NAME",
                            "value": "sentence-transformers/all-mpnet-base-v2"
                        },
                        {
                            "name": "BATCH_SIZE",
                            "value": "32"
                        },
                        {
                            "name": "CLUSTERING_METHOD",
                            "value": "hdbscan"
                        }
                    ],
                    "secrets": [
                        {
                            "name": "OPENAI_API_KEY",
                            "valueFrom": "${OpenAIApiKeySecretArn}"
                        }
                    ],
                    "logConfiguration": {
                        "logDriver": "awslogs",
                        "options": {
                            "awslogs-group": "/ecs/news-pipeline-embed-cluster",
                            "awslogs-region": "${AWS::Region}",
                            "awslogs-stream-prefix": "embed-cluster"
                        }
                    },
                    "resourceRequirements": [
                        {
                            "type": "GPU",
                            "value": "1"  # Request 1 GPU
                        }
                    ]
                }
            ]
        }
        
        return task_definition
    
    def create_bias_score_task_definition(self) -> Dict[str, Any]:
        """
        Create ECS task definition for bias scoring with Valyu API.
        Uses GPU for faster inference.
        
        Returns:
            Task definition configuration
        """
        task_definition = {
            "family": "news-pipeline-bias-score",
            "networkMode": "awsvpc",
            "requiresCompatibilities": ["FARGATE"],
            "cpu": "4096",  # 4 vCPU
            "memory": "16384",  # 16 GB
            "executionRoleArn": "${ECSTaskExecutionRoleArn}",
            "taskRoleArn": "${ECSTaskRoleArn}",
            "containerDefinitions": [
                {
                    "name": "bias-score-container",
                    "image": "${ECRRepositoryUri}/bias-score:latest",
                    "cpu": 4096,
                    "memory": 16384,
                    "essential": True,
                    "environment": [
                        {
                            "name": "PIPELINE_BUCKET",
                            "value": "${PipelineBucket}"
                        },
                        {
                            "name": "AWS_REGION",
                            "value": "${AWS::Region}"
                        },
                        {
                            "name": "VALYU_API_ENDPOINT",
                            "value": "https://api.valyu.ai/v1"
                        },
                        {
                            "name": "BATCH_SIZE",
                            "value": "16"
                        },
                        {
                            "name": "MAX_CONCURRENT_REQUESTS",
                            "value": "5"
                        }
                    ],
                    "secrets": [
                        {
                            "name": "VALYU_API_KEY",
                            "valueFrom": "${ValyuApiKeySecretArn}"
                        }
                    ],
                    "logConfiguration": {
                        "logDriver": "awslogs",
                        "options": {
                            "awslogs-group": "/ecs/news-pipeline-bias-score",
                            "awslogs-region": "${AWS::Region}",
                            "awslogs-stream-prefix": "bias-score"
                        }
                    },
                    "resourceRequirements": [
                        {
                            "type": "GPU",
                            "value": "1"  # Request 1 GPU
                        }
                    ]
                }
            ]
        }
        
        return task_definition
    
    def register_task_definition(self, task_definition: Dict[str, Any]) -> str:
        """
        Register a task definition with ECS.
        
        Args:
            task_definition: Task definition configuration
            
        Returns:
            Task definition ARN
        """
        if not self.ecs_client:
            raise ValueError("ECS client required")
        
        try:
            response = self.ecs_client.register_task_definition(**task_definition)
            task_def_arn = response['taskDefinition']['taskDefinitionArn']
            logger.info(f"Registered task definition: {task_def_arn}")
            return task_def_arn
        except Exception as e:
            logger.error(f"Failed to register task definition: {e}")
            raise
    
    def run_task(self,
                cluster: str,
                task_definition: str,
                subnets: List[str],
                security_groups: List[str],
                container_overrides: Optional[List[Dict[str, Any]]] = None,
                launch_type: str = "FARGATE") -> Dict[str, Any]:
        """
        Run an ECS task.
        
        Args:
            cluster: ECS cluster name or ARN
            task_definition: Task definition name or ARN
            subnets: List of subnet IDs
            security_groups: List of security group IDs
            container_overrides: Optional container overrides
            launch_type: FARGATE or EC2
            
        Returns:
            Task run response
        """
        if not self.ecs_client:
            raise ValueError("ECS client required")
        
        kwargs = {
            "cluster": cluster,
            "taskDefinition": task_definition,
            "launchType": launch_type,
            "networkConfiguration": {
                "awsvpcConfiguration": {
                    "subnets": subnets,
                    "securityGroups": security_groups,
                    "assignPublicIp": "ENABLED"
                }
            }
        }
        
        if container_overrides:
            kwargs["overrides"] = {
                "containerOverrides": container_overrides
            }
        
        try:
            response = self.ecs_client.run_task(**kwargs)
            
            if response.get('failures'):
                logger.error(f"Task run failures: {response['failures']}")
            
            tasks = response.get('tasks', [])
            if tasks:
                task_arn = tasks[0]['taskArn']
                logger.info(f"Started ECS task: {task_arn}")
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to run task: {e}")
            raise
    
    def wait_for_task_completion(self,
                                 cluster: str,
                                 task_arn: str,
                                 timeout_seconds: int = 3600) -> Dict[str, Any]:
        """
        Wait for an ECS task to complete.
        
        Args:
            cluster: ECS cluster name or ARN
            task_arn: Task ARN
            timeout_seconds: Maximum wait time
            
        Returns:
            Task details
        """
        if not self.ecs_client:
            raise ValueError("ECS client required")
        
        try:
            waiter = self.ecs_client.get_waiter('tasks_stopped')
            waiter.wait(
                cluster=cluster,
                tasks=[task_arn],
                WaiterConfig={
                    'Delay': 15,
                    'MaxAttempts': timeout_seconds // 15
                }
            )
            
            # Get task details
            response = self.ecs_client.describe_tasks(
                cluster=cluster,
                tasks=[task_arn]
            )
            
            task = response['tasks'][0] if response.get('tasks') else {}
            logger.info(f"Task completed: {task_arn}")
            
            return task
            
        except Exception as e:
            logger.error(f"Error waiting for task: {e}")
            raise
    
    def get_task_logs(self,
                     log_group: str,
                     log_stream: str,
                     start_time: Optional[int] = None) -> List[str]:
        """
        Get logs from CloudWatch for an ECS task.
        
        Args:
            log_group: CloudWatch log group
            log_stream: CloudWatch log stream
            start_time: Optional start time (Unix timestamp in ms)
            
        Returns:
            List of log messages
        """
        try:
            import boto3
            logs_client = boto3.client('logs')
            
            kwargs = {
                'logGroupName': log_group,
                'logStreamName': log_stream
            }
            
            if start_time:
                kwargs['startTime'] = start_time
            
            response = logs_client.get_log_events(**kwargs)
            
            messages = [event['message'] for event in response.get('events', [])]
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get task logs: {e}")
            return []


def generate_cloudformation_template() -> Dict[str, Any]:
    """
    Generate CloudFormation template for ECS infrastructure.
    
    Returns:
        CloudFormation template as dictionary
    """
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "ECS infrastructure for news pipeline GPU workloads",
        "Parameters": {
            "VpcId": {
                "Type": "AWS::EC2::VPC::Id",
                "Description": "VPC for ECS cluster"
            },
            "SubnetIds": {
                "Type": "List<AWS::EC2::Subnet::Id>",
                "Description": "Subnets for ECS tasks"
            },
            "ECRRepositoryUri": {
                "Type": "String",
                "Description": "ECR repository URI for container images"
            }
        },
        "Resources": {
            "ECSCluster": {
                "Type": "AWS::ECS::Cluster",
                "Properties": {
                    "ClusterName": "news-pipeline-cluster",
                    "CapacityProviders": ["FARGATE", "FARGATE_SPOT"],
                    "DefaultCapacityProviderStrategy": [
                        {
                            "CapacityProvider": "FARGATE",
                            "Weight": 1
                        }
                    ],
                    "ClusterSettings": [
                        {
                            "Name": "containerInsights",
                            "Value": "enabled"
                        }
                    ]
                }
            },
            "ECSTaskExecutionRole": {
                "Type": "AWS::IAM::Role",
                "Properties": {
                    "AssumeRolePolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Principal": {
                                    "Service": "ecs-tasks.amazonaws.com"
                                },
                                "Action": "sts:AssumeRole"
                            }
                        ]
                    },
                    "ManagedPolicyArns": [
                        "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
                    ],
                    "Policies": [
                        {
                            "PolicyName": "SecretsManagerAccess",
                            "PolicyDocument": {
                                "Version": "2012-10-17",
                                "Statement": [
                                    {
                                        "Effect": "Allow",
                                        "Action": [
                                            "secretsmanager:GetSecretValue"
                                        ],
                                        "Resource": "*"
                                    }
                                ]
                            }
                        }
                    ]
                }
            },
            "ECSTaskRole": {
                "Type": "AWS::IAM::Role",
                "Properties": {
                    "AssumeRolePolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Principal": {
                                    "Service": "ecs-tasks.amazonaws.com"
                                },
                                "Action": "sts:AssumeRole"
                            }
                        ]
                    },
                    "Policies": [
                        {
                            "PolicyName": "S3Access",
                            "PolicyDocument": {
                                "Version": "2012-10-17",
                                "Statement": [
                                    {
                                        "Effect": "Allow",
                                        "Action": [
                                            "s3:GetObject",
                                            "s3:PutObject",
                                            "s3:ListBucket"
                                        ],
                                        "Resource": "*"
                                    }
                                ]
                            }
                        }
                    ]
                }
            },
            "SecurityGroup": {
                "Type": "AWS::EC2::SecurityGroup",
                "Properties": {
                    "GroupDescription": "Security group for ECS tasks",
                    "VpcId": {"Ref": "VpcId"},
                    "SecurityGroupEgress": [
                        {
                            "IpProtocol": "-1",
                            "CidrIp": "0.0.0.0/0"
                        }
                    ]
                }
            },
            "EmbedClusterLogGroup": {
                "Type": "AWS::Logs::LogGroup",
                "Properties": {
                    "LogGroupName": "/ecs/news-pipeline-embed-cluster",
                    "RetentionInDays": 7
                }
            },
            "BiasScoreLogGroup": {
                "Type": "AWS::Logs::LogGroup",
                "Properties": {
                    "LogGroupName": "/ecs/news-pipeline-bias-score",
                    "RetentionInDays": 7
                }
            }
        },
        "Outputs": {
            "ClusterArn": {
                "Description": "ECS Cluster ARN",
                "Value": {"Fn::GetAtt": ["ECSCluster", "Arn"]}
            },
            "TaskExecutionRoleArn": {
                "Description": "ECS Task Execution Role ARN",
                "Value": {"Fn::GetAtt": ["ECSTaskExecutionRole", "Arn"]}
            },
            "TaskRoleArn": {
                "Description": "ECS Task Role ARN",
                "Value": {"Fn::GetAtt": ["ECSTaskRole", "Arn"]}
            },
            "SecurityGroupId": {
                "Description": "Security Group ID",
                "Value": {"Ref": "SecurityGroup"}
            }
        }
    }
    
    return template
