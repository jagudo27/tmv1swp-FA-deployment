import azure.functions as func
import logging
from datetime import datetime

# Import our custom modules following SRP
from .environment_validator import EnvironmentValidator
from .trend_micro_api_client import TrendMicroApiClient
from .event_data_transformer import TrendMicroEventTransformer
from .log_analytics_client import LogAnalyticsIngestionClient

# Configure logging for Azure
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main(mytimer: func.TimerRequest) -> None:
    """
    Azure Function that extracts OAT events from Trend Micro and sends them to Log Analytics.
    Executes every 5 minutes: 0 */5 * * * *
    """
    logger = logging.getLogger(__name__)
    logger.info("TREND MICRO ETL FUNCTION STARTED")
    
    if mytimer.past_due:
        logger.warning('The timer is past due!')

    try:
        # Step 1: Validate environment and load configuration
        environment_validator = EnvironmentValidator()
        config = environment_validator.validate_and_load_configuration()
        
        logger.info("=== TREND MICRO OAT ETL STARTED ===")
        
        # Step 2: Extract events from Trend Micro API
        trend_micro_client = TrendMicroApiClient(config.trend_micro_token)
        api_response = trend_micro_client.fetch_security_events_from_last_hours()
        
        if not api_response or not api_response.get('items'):
            logger.info("No events found in Trend Micro API")
            return
        
        events = api_response['items']
        total_available = api_response.get('totalCount', 0)
        
        logger.info(f"Total events available in API: {total_available}")
        logger.info(f"Events extracted: {len(events)}")
        
        # Step 3: Transform events for Log Analytics
        transformer = TrendMicroEventTransformer()
        transformed_events = transformer.transform_events_for_log_analytics(events)
        
        if not transformed_events:
            logger.warning("No events to send after transformation")
            return
        
        logger.info(f"Events transformed: {len(transformed_events)}")
        
        # Log field coverage statistics for debugging
        if len(events) > 0:
            coverage_stats = transformer.validate_raw_event_coverage(events[:min(10, len(events))])  # Sample first 10 events
            populated_fields = [(field, count) for field, count in coverage_stats.items() if count > 0]
            logger.info(f"Field coverage analysis (first {min(10, len(events))} events):")
            logger.info(f"Populated fields: {len(populated_fields)}/{len(coverage_stats)}")
            if populated_fields:
                logger.debug(f"Most common fields: {sorted(populated_fields, key=lambda x: x[1], reverse=True)[:10]}")
        
        # Step 4: Send to Log Analytics
        log_analytics_client = LogAnalyticsIngestionClient(
            config.data_collection_endpoint,
            config.data_collection_rule_id,
            config.stream_name
        )
        
        log_analytics_client.send_events_to_log_analytics(transformed_events)
        logger.info(f"SUCCESS: {len(transformed_events)} events sent to Log Analytics")
        
        logger.info("=== TREND MICRO OAT ETL COMPLETED ===")
            
    except Exception as e:
        error_msg = f"ERROR in ETL process: {str(e)}"
        logger.error(error_msg)
        raise

