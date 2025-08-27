"""
Log Analytics client for sending transformed events to Azure Monitor.
Handles the ingestion of events into Azure Log Analytics custom tables.
"""

import logging
from typing import List, Dict
from azure.monitor.ingestion import LogsIngestionClient
from azure.identity import DefaultAzureCredential


class LogAnalyticsIngestionClient:
    """Client for ingesting events into Azure Log Analytics custom tables."""
    
    DEFAULT_BATCH_SIZE = 100  # Maximum 1MB per request
    
    def __init__(self, endpoint_url: str, data_collection_rule_id: str, stream_name: str):
        """
        Initialize the Log Analytics ingestion client.
        
        Args:
            endpoint_url: Azure Monitor data collection endpoint URL
            data_collection_rule_id: Data Collection Rule ID for the target table
            stream_name: Name of the custom stream/table
        """
        self.endpoint_url = self._validate_and_clean_endpoint(endpoint_url)
        self.data_collection_rule_id = data_collection_rule_id
        self.stream_name = stream_name
        self.logger = logging.getLogger(__name__)
        
        self._validate_configuration()
    
    def send_events_to_log_analytics(self, events: List[Dict], batch_size: int = None) -> None:
        """
        Sends transformed events to Log Analytics custom table in batches.
        
        Args:
            events: List of transformed events to send
            batch_size: Size of batches to send (defaults to DEFAULT_BATCH_SIZE)
            
        Raises:
            Exception: If sending fails
        """
        if batch_size is None:
            batch_size = self.DEFAULT_BATCH_SIZE
            
        self.logger.info(f"Starting upload of {len(events)} events to Log Analytics")
        
        try:
            client = self._create_ingestion_client()
            total_sent = self._send_events_in_batches(client, events, batch_size)
            
            self.logger.info(f"Successfully uploaded {total_sent} events to {self.stream_name}")
            
        except Exception as e:
            error_msg = f"Failed to send data to Log Analytics: {str(e)}"
            self.logger.error(error_msg)
            raise
    
    def _validate_and_clean_endpoint(self, endpoint_url: str) -> str:
        """
        Validates and cleans the endpoint URL.
        
        Args:
            endpoint_url: Raw endpoint URL
            
        Returns:
            Cleaned and validated endpoint URL
            
        Raises:
            ValueError: If endpoint URL is invalid
        """
        if not endpoint_url:
            raise ValueError("DATA_COLLECTION_ENDPOINT is empty or None")
        
        cleaned_endpoint = endpoint_url.strip()
        
        self.logger.info(f"Raw endpoint received: '{cleaned_endpoint}'")
        self.logger.info(f"Raw endpoint repr: {repr(cleaned_endpoint)}")
        
        if not cleaned_endpoint:
            raise ValueError("DATA_COLLECTION_ENDPOINT is empty after strip()")
            
        if not cleaned_endpoint.startswith('https://'):
            raise ValueError(f"Invalid endpoint URL format: '{cleaned_endpoint}' (should start with https://)")
        
        # Remove any hidden whitespace characters
        if any(char in cleaned_endpoint for char in ['\n', '\r', '\t']):
            self.logger.warning(f"Endpoint contains whitespace characters: {repr(cleaned_endpoint)}")
            cleaned_endpoint = ''.join(cleaned_endpoint.split())
            self.logger.info(f"Cleaned endpoint: '{cleaned_endpoint}'")
        
        return cleaned_endpoint
    
    def _validate_configuration(self) -> None:
        """Validates that all required configuration is present."""
        if not self.data_collection_rule_id:
            raise ValueError("DATA_COLLECTION_RULE_ID is empty or None")
            
        if not self.stream_name:
            raise ValueError("STREAM_NAME is empty or None")
        
        self.logger.info(f"Connecting to Log Analytics: {self.endpoint_url}")
        self.logger.info(f"Using DCR: {self.data_collection_rule_id}")
        self.logger.info(f"Target stream: {self.stream_name}")
    
    def _create_ingestion_client(self) -> LogsIngestionClient:
        """Creates and returns a Log Analytics ingestion client."""
        credential = DefaultAzureCredential()
        
        return LogsIngestionClient(
            endpoint=self.endpoint_url,
            credential=credential,
            logging_enable=True
        )
    
    def _send_events_in_batches(self, client: LogsIngestionClient, 
                               events: List[Dict], batch_size: int) -> int:
        """
        Sends events to Log Analytics in batches.
        
        Args:
            client: Configured LogsIngestionClient
            events: List of events to send
            batch_size: Size of each batch
            
        Returns:
            Total number of events sent successfully
            
        Raises:
            Exception: If any batch fails to send
        """
        total_sent = 0
        
        for batch_index in range(0, len(events), batch_size):
            batch = events[batch_index:batch_index + batch_size]
            batch_number = batch_index // batch_size + 1
            
            try:
                self._send_single_batch(client, batch, batch_number)
                total_sent += len(batch)
                
            except Exception as batch_error:
                self._handle_batch_error(batch_error, batch_number)
                raise
        
        return total_sent
    
    def _send_single_batch(self, client: LogsIngestionClient, 
                          batch: List[Dict], batch_number: int) -> None:
        """
        Sends a single batch of events to Log Analytics.
        
        Args:
            client: Configured LogsIngestionClient
            batch: Batch of events to send
            batch_number: Batch number for logging
        """
        self.logger.info(f"Attempting upload with:")
        self.logger.info(f"  - rule_id: '{self.data_collection_rule_id}'")
        self.logger.info(f"  - stream_name: '{self.stream_name}'")
        self.logger.info(f"  - batch size: {len(batch)}")
        
        client.upload(
            rule_id=self.data_collection_rule_id,
            stream_name=self.stream_name,
            logs=batch
        )
        
        self.logger.info(f"Batch {batch_number}: Sent {len(batch)} events to Log Analytics")
    
    def _handle_batch_error(self, batch_error: Exception, batch_number: int) -> None:
        """
        Handles and logs batch upload errors with detailed information.
        
        Args:
            batch_error: The exception that occurred
            batch_number: Batch number that failed
        """
        error_msg = f"Error sending batch {batch_number}: {str(batch_error)}"
        self.logger.error(error_msg)
        self.logger.error(f"Batch error type: {type(batch_error)}")
        self.logger.error(f"Batch error details: {repr(batch_error)}")
        
        # Extract additional details if available
        if hasattr(batch_error, 'response'):
            response = batch_error.response
            self.logger.error(f"Response status: {getattr(response, 'status_code', 'unknown')}")
            self.logger.error(f"Response text: {getattr(response, 'text', 'no text')}")
