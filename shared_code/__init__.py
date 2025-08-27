"""
Shared code package for Trend Micro ETL Azure Function.
Contains modular components following Single Responsibility Principle.
"""

from .environment_validator import EnvironmentValidator, EnvironmentConfiguration
from .trend_micro_api_client import TrendMicroApiClient
from .event_data_transformer import TrendMicroEventTransformer
from .log_analytics_client import LogAnalyticsIngestionClient

__version__ = "2.0.0"
__author__ = "Trend Micro ETL Team"

__all__ = [
    'EnvironmentValidator',
    'EnvironmentConfiguration', 
    'TrendMicroApiClient',
    'TrendMicroEventTransformer',
    'LogAnalyticsIngestionClient'
]
