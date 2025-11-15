"""SQS queue integration for retry logic and circuit breakers."""

import json
import logging
import time
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class SQSRetryQueue:
    """
    Manages SQS queues for retry logic with exponential backoff.
    Implements circuit breaker pattern for failing sources.
    """
    
    def __init__(self, 
                 sqs_client=None,
                 main_queue_url: Optional[str] = None,
                 retry_queue_url: Optional[str] = None,
                 dlq_url: Optional[str] = None,
                 max_retries: int = 3,
                 base_delay: int = 2):
        """
        Initialize SQS retry queue manager.
        
        Args:
            sqs_client: Boto3 SQS client
            main_queue_url: URL of the main processing queue
            retry_queue_url: URL of the retry queue
            dlq_url: URL of the dead letter queue
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds for exponential backoff
        """
        self.sqs_client = sqs_client
        self.main_queue_url = main_queue_url
        self.retry_queue_url = retry_queue_url
        self.dlq_url = dlq_url
        self.max_retries = max_retries
        self.base_delay = base_delay
        
        # Circuit breaker state per source
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
    
    def send_message(self, 
                    queue_url: str,
                    message_body: Dict[str, Any],
                    delay_seconds: int = 0,
                    message_attributes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a message to an SQS queue.
        
        Args:
            queue_url: URL of the queue
            message_body: Message payload as dictionary
            delay_seconds: Delay before message becomes visible
            message_attributes: Optional message attributes
            
        Returns:
            SQS send_message response
        """
        if not self.sqs_client:
            raise ValueError("SQS client required")
        
        kwargs = {
            'QueueUrl': queue_url,
            'MessageBody': json.dumps(message_body),
            'DelaySeconds': min(delay_seconds, 900)  # Max 15 minutes
        }
        
        if message_attributes:
            kwargs['MessageAttributes'] = message_attributes
        
        try:
            response = self.sqs_client.send_message(**kwargs)
            logger.info(f"Sent message to queue: {queue_url}")
            return response
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            raise
    
    def send_to_retry_queue(self, 
                           source: Dict[str, Any],
                           error: str,
                           retry_count: int = 0) -> None:
        """
        Send a failed source to the retry queue with exponential backoff.
        
        Args:
            source: Source configuration that failed
            error: Error message
            retry_count: Current retry attempt number
        """
        if not self.retry_queue_url:
            logger.warning("Retry queue URL not configured")
            return
        
        if retry_count >= self.max_retries:
            logger.warning(f"Max retries exceeded for {source.get('name')}, sending to DLQ")
            self.send_to_dlq(source, error, retry_count)
            return
        
        # Calculate exponential backoff delay
        delay = self._calculate_backoff_delay(retry_count)
        
        message = {
            'source': source,
            'error': error,
            'retry_count': retry_count + 1,
            'timestamp': datetime.utcnow().isoformat(),
            'next_retry_after': (datetime.utcnow() + timedelta(seconds=delay)).isoformat()
        }
        
        message_attributes = {
            'RetryCount': {
                'StringValue': str(retry_count + 1),
                'DataType': 'Number'
            },
            'SourceName': {
                'StringValue': source.get('name', 'Unknown'),
                'DataType': 'String'
            }
        }
        
        try:
            self.send_message(
                self.retry_queue_url,
                message,
                delay_seconds=delay,
                message_attributes=message_attributes
            )
            logger.info(f"Sent {source.get('name')} to retry queue (attempt {retry_count + 1})")
        except Exception as e:
            logger.error(f"Failed to send to retry queue: {e}")
            # Try DLQ as fallback
            self.send_to_dlq(source, f"Retry queue failed: {str(e)}", retry_count)
    
    def send_to_dlq(self, 
                   source: Dict[str, Any],
                   error: str,
                   retry_count: int) -> None:
        """
        Send a message to the dead letter queue.
        
        Args:
            source: Source configuration that failed
            error: Error message
            retry_count: Number of retry attempts made
        """
        if not self.dlq_url:
            logger.warning("DLQ URL not configured")
            return
        
        message = {
            'source': source,
            'error': error,
            'retry_count': retry_count,
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'failed'
        }
        
        message_attributes = {
            'FinalRetryCount': {
                'StringValue': str(retry_count),
                'DataType': 'Number'
            },
            'SourceName': {
                'StringValue': source.get('name', 'Unknown'),
                'DataType': 'String'
            }
        }
        
        try:
            self.send_message(
                self.dlq_url,
                message,
                message_attributes=message_attributes
            )
            logger.info(f"Sent {source.get('name')} to DLQ after {retry_count} retries")
        except Exception as e:
            logger.error(f"Failed to send to DLQ: {e}")
    
    def receive_messages(self, 
                        queue_url: str,
                        max_messages: int = 10,
                        wait_time_seconds: int = 20) -> List[Dict[str, Any]]:
        """
        Receive messages from a queue with long polling.
        
        Args:
            queue_url: URL of the queue
            max_messages: Maximum number of messages to receive (1-10)
            wait_time_seconds: Long polling wait time
            
        Returns:
            List of messages
        """
        if not self.sqs_client:
            raise ValueError("SQS client required")
        
        try:
            response = self.sqs_client.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=min(max_messages, 10),
                WaitTimeSeconds=wait_time_seconds,
                MessageAttributeNames=['All'],
                AttributeNames=['All']
            )
            
            messages = response.get('Messages', [])
            logger.info(f"Received {len(messages)} messages from queue")
            return messages
            
        except Exception as e:
            logger.error(f"Failed to receive messages: {e}")
            raise
    
    def delete_message(self, queue_url: str, receipt_handle: str) -> None:
        """
        Delete a message from the queue after successful processing.
        
        Args:
            queue_url: URL of the queue
            receipt_handle: Receipt handle of the message
        """
        if not self.sqs_client:
            raise ValueError("SQS client required")
        
        try:
            self.sqs_client.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=receipt_handle
            )
            logger.debug("Deleted message from queue")
        except Exception as e:
            logger.error(f"Failed to delete message: {e}")
    
    def _calculate_backoff_delay(self, retry_count: int) -> int:
        """
        Calculate exponential backoff delay.
        
        Args:
            retry_count: Current retry attempt
            
        Returns:
            Delay in seconds (capped at 900 seconds / 15 minutes)
        """
        delay = self.base_delay * (2 ** retry_count)
        return min(delay, 900)  # SQS max delay is 15 minutes
    
    def process_retry_queue(self, 
                           processor_func: Callable[[Dict[str, Any]], bool],
                           batch_size: int = 10) -> Dict[str, int]:
        """
        Process messages from the retry queue.
        
        Args:
            processor_func: Function to process each message, returns True if successful
            batch_size: Number of messages to process in one batch
            
        Returns:
            Dictionary with processing statistics
        """
        if not self.retry_queue_url:
            raise ValueError("Retry queue URL required")
        
        stats = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'requeued': 0
        }
        
        messages = self.receive_messages(self.retry_queue_url, max_messages=batch_size)
        
        for message in messages:
            stats['processed'] += 1
            
            try:
                body = json.loads(message['Body'])
                source = body['source']
                retry_count = body.get('retry_count', 0)
                
                # Check circuit breaker
                if not self._check_circuit_breaker(source.get('name', '')):
                    logger.info(f"Circuit breaker open for {source.get('name')}, skipping")
                    continue
                
                # Process the message
                if processor_func(source):
                    # Success - delete from queue
                    self.delete_message(self.retry_queue_url, message['ReceiptHandle'])
                    stats['successful'] += 1
                    self._record_success(source.get('name', ''))
                else:
                    # Failed - retry or send to DLQ
                    stats['failed'] += 1
                    self._record_failure(source.get('name', ''))
                    
                    error = "Processing failed"
                    self.send_to_retry_queue(source, error, retry_count)
                    self.delete_message(self.retry_queue_url, message['ReceiptHandle'])
                    stats['requeued'] += 1
                    
            except Exception as e:
                logger.error(f"Error processing retry message: {e}")
                stats['failed'] += 1
        
        return stats
    
    # ========================================================================
    # Circuit Breaker Implementation
    # ========================================================================
    
    def _check_circuit_breaker(self, source_name: str) -> bool:
        """
        Check if circuit breaker allows processing.
        
        Args:
            source_name: Name of the source
            
        Returns:
            True if processing is allowed, False otherwise
        """
        if source_name not in self.circuit_breakers:
            self._init_circuit_breaker(source_name)
        
        breaker = self.circuit_breakers[source_name]
        state = breaker['state']
        
        if state == CircuitState.CLOSED:
            return True
        
        elif state == CircuitState.OPEN:
            # Check if timeout has elapsed to try half-open
            if datetime.utcnow() >= breaker['next_attempt']:
                breaker['state'] = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker for {source_name} moving to HALF_OPEN")
                return True
            return False
        
        elif state == CircuitState.HALF_OPEN:
            # Allow one request to test
            return True
        
        return False
    
    def _init_circuit_breaker(self, source_name: str) -> None:
        """Initialize circuit breaker for a source."""
        self.circuit_breakers[source_name] = {
            'state': CircuitState.CLOSED,
            'failure_count': 0,
            'success_count': 0,
            'last_failure': None,
            'next_attempt': None,
            'failure_threshold': 5,
            'success_threshold': 2,
            'timeout': 60  # seconds
        }
    
    def _record_failure(self, source_name: str) -> None:
        """Record a failure for circuit breaker."""
        if source_name not in self.circuit_breakers:
            self._init_circuit_breaker(source_name)
        
        breaker = self.circuit_breakers[source_name]
        breaker['failure_count'] += 1
        breaker['last_failure'] = datetime.utcnow()
        
        if breaker['state'] == CircuitState.HALF_OPEN:
            # Failed during test, back to OPEN
            breaker['state'] = CircuitState.OPEN
            breaker['next_attempt'] = datetime.utcnow() + timedelta(seconds=breaker['timeout'])
            logger.warning(f"Circuit breaker for {source_name} reopened")
        
        elif breaker['failure_count'] >= breaker['failure_threshold']:
            # Too many failures, open circuit
            breaker['state'] = CircuitState.OPEN
            breaker['next_attempt'] = datetime.utcnow() + timedelta(seconds=breaker['timeout'])
            logger.warning(f"Circuit breaker for {source_name} opened after {breaker['failure_count']} failures")
    
    def _record_success(self, source_name: str) -> None:
        """Record a success for circuit breaker."""
        if source_name not in self.circuit_breakers:
            self._init_circuit_breaker(source_name)
        
        breaker = self.circuit_breakers[source_name]
        breaker['success_count'] += 1
        breaker['failure_count'] = max(0, breaker['failure_count'] - 1)
        
        if breaker['state'] == CircuitState.HALF_OPEN:
            if breaker['success_count'] >= breaker['success_threshold']:
                # Enough successes, close circuit
                breaker['state'] = CircuitState.CLOSED
                breaker['success_count'] = 0
                breaker['failure_count'] = 0
                logger.info(f"Circuit breaker for {source_name} closed")
    
    def get_circuit_breaker_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers."""
        status = {}
        for source_name, breaker in self.circuit_breakers.items():
            status[source_name] = {
                'state': breaker['state'].value,
                'failure_count': breaker['failure_count'],
                'success_count': breaker['success_count'],
                'last_failure': breaker['last_failure'].isoformat() if breaker['last_failure'] else None,
                'next_attempt': breaker['next_attempt'].isoformat() if breaker['next_attempt'] else None
            }
        return status
