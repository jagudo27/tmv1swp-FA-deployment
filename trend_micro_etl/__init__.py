"""
Azure Functions entry point for Trend Micro ETL function.
This module imports and exposes the main ETL function from shared_code.
"""

from shared_code.trend_micro_etl import main

# Export the main function for Azure Functions runtime
__all__ = ['main']
