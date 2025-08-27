"""
Environment configuration validator for Trend Micro ETL Azure Function.
Handles validation and loading of environment variables required for the ETL process.
"""

import os
import logging
from typing import Dict, List


class EnvironmentConfiguration:
    """Configuration object containing all required environment variables."""
    
    def __init__(self):
        self.trend_micro_token: str = ""
        self.data_collection_endpoint: str = ""
        self.data_collection_rule_id: str = ""
        self.stream_name: str = "Custom-TrendMicroOATEvents_CL"
    

class EnvironmentValidator:
    """Validates and loads environment variables for the Trend Micro ETL process."""
    
    REQUIRED_VARIABLES = [
        "TREND_MICRO_TOKEN",
        "DATA_COLLECTION_ENDPOINT", 
        "DATA_COLLECTION_RULE_ID"
    ]
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def validate_and_load_configuration(self) -> EnvironmentConfiguration:
        """
        Validates all required environment variables and returns configuration object.
        
        Returns:
            EnvironmentConfiguration: Object with validated configuration
            
        Raises:
            ValueError: If any required environment variable is missing or invalid
        """
        self._log_environment_variables()
        self._validate_required_variables_exist()
        
        config = EnvironmentConfiguration()
        config.trend_micro_token = self._get_and_validate_token()
        config.data_collection_endpoint = self._get_and_validate_endpoint()
        config.data_collection_rule_id = self._get_and_validate_rule_id()
        config.stream_name = self._get_stream_name()
        
        self._log_configuration_summary(config)
        return config
    
    def _log_environment_variables(self) -> None:
        """Logs all relevant environment variables for debugging."""
        self.logger.info("Checking environment variables...")
        
        all_env_vars = dict(os.environ)
        relevant_vars = {
            k: v for k, v in all_env_vars.items() 
            if any(keyword in k.upper() for keyword in ['TREND', 'DATA_COLLECTION', 'STREAM'])
        }
        
        self.logger.info("=== ENVIRONMENT VARIABLES ===")
        for key, value in relevant_vars.items():
            if 'TOKEN' in key.upper():
                self.logger.info(f"{key}: {'*' * 20}")
            else:
                self.logger.info(f"{key}: {value}")
        self.logger.info("=== END ENVIRONMENT VARIABLES ===")
    
    def _validate_required_variables_exist(self) -> None:
        """Validates that all required environment variables are present."""
        missing_vars = [var for var in self.REQUIRED_VARIABLES if not os.environ.get(var)]
        
        if missing_vars:
            error_msg = f"Missing required environment variables: {missing_vars}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
    
    def _get_and_validate_token(self) -> str:
        """Gets and validates the Trend Micro API token."""
        token = os.environ["TREND_MICRO_TOKEN"].strip()
        if not token:
            raise ValueError("TREND_MICRO_TOKEN is empty after stripping whitespace")
        return token
    
    def _get_and_validate_endpoint(self) -> str:
        """Gets and validates the data collection endpoint URL."""
        endpoint = os.environ["DATA_COLLECTION_ENDPOINT"].strip()
        
        self.logger.info(f"DATA_COLLECTION_ENDPOINT: '{endpoint}'")
        self.logger.info(f"DATA_COLLECTION_ENDPOINT length: {len(endpoint)}")
        self.logger.info(f"DATA_COLLECTION_ENDPOINT repr: {repr(endpoint)}")
        
        if not endpoint:
            raise ValueError("DATA_COLLECTION_ENDPOINT is empty after stripping whitespace")
            
        if not endpoint.startswith('https://'):
            raise ValueError(f"Invalid DATA_COLLECTION_ENDPOINT format: '{endpoint}' (should start with https://)")
        
        # Clean up any hidden whitespace characters
        if any(char in endpoint for char in ['\n', '\r', '\t']):
            self.logger.warning(f"Endpoint contains whitespace characters: {repr(endpoint)}")
            endpoint = ''.join(endpoint.split())
            self.logger.info(f"Cleaned endpoint: '{endpoint}'")
        
        return endpoint
    
    def _get_and_validate_rule_id(self) -> str:
        """Gets and validates the data collection rule ID."""
        rule_id = os.environ["DATA_COLLECTION_RULE_ID"].strip()
        
        self.logger.info(f"DATA_COLLECTION_RULE_ID: '{rule_id}'")
        
        if not rule_id:
            raise ValueError("DATA_COLLECTION_RULE_ID is empty after stripping whitespace")
        
        return rule_id
    
    def _get_stream_name(self) -> str:
        """Gets the stream name with default fallback."""
        return os.environ.get("STREAM_NAME", "Custom-TrendMicroOATEvents_CL").strip()
    
    def _log_configuration_summary(self, config: EnvironmentConfiguration) -> None:
        """Logs a summary of the loaded configuration."""
        self.logger.info(f"STREAM_NAME: '{config.stream_name}'")
        self.logger.info(f"Final endpoint URL: '{config.data_collection_endpoint}'")
        self.logger.info("Environment validation completed successfully")
