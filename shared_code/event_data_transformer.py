"""
Event data transformer for Trend Micro OAT events.
Transforms raw events from Trend Micro API into the format required by Log Analytics.
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional


class TrendMicroEventTransformer:
    """Transforms Trend Micro OAT events for Log Analytics ingestion."""
    
    RISK_LEVEL_PRIORITY = {
        "critical": 4,
        "high": 3, 
        "medium": 2,
        "low": 1,
        "info": 0
    }
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def transform_events_for_log_analytics(self, raw_events: List[Dict]) -> List[Dict]:
        """
        Transforms raw Trend Micro events into Log Analytics custom table format.
        Extracts the 5 required fields: detectedDateTime, name, riskLevel, endpointHostName, endpointIp
        
        Args:
            raw_events: List of raw events from Trend Micro API
            
        Returns:
            List of transformed events ready for Log Analytics
        """
        self.logger.info(f"Starting transformation of {len(raw_events)} events")
        
        transformed_events = []
        
        for event in raw_events:
            try:
                transformed_event = self._transform_single_event(event)
                
                if self._is_valid_transformed_event(transformed_event, event):
                    transformed_events.append(transformed_event)
                else:
                    self.logger.warning(f"Skipping event {event.get('uuid', 'unknown')} - missing required fields")
                    
            except Exception as e:
                self.logger.error(f"Error transforming event {event.get('uuid', 'unknown')}: {str(e)}")
                continue
        
        self.logger.info(f"Transformation completed: {len(transformed_events)} events ready for Log Analytics")
        return transformed_events
    
    def _transform_single_event(self, raw_event: Dict) -> Dict:
        """
        Transforms a single raw event into Log Analytics format.
        
        Args:
            raw_event: Single raw event from Trend Micro API
            
        Returns:
            Transformed event dictionary
        """
        highest_risk_filter = self._find_highest_risk_filter(raw_event.get('filters', []))
        
        return {
            "TimeGenerated": datetime.now(timezone.utc).isoformat(),
            "detectedDateTime": raw_event.get('detectedDateTime', ''),
            "name": highest_risk_filter.get('name', '') if highest_risk_filter else '',
            "riskLevel": highest_risk_filter.get('riskLevel', '') if highest_risk_filter else '',
            "endpointHostName": self._extract_endpoint_hostname(raw_event),
            "endpointIp": self._extract_endpoint_ip_address(raw_event)
        }
    
    def _find_highest_risk_filter(self, filters: List[Dict]) -> Optional[Dict]:
        """
        Finds and returns the filter with the highest risk level.
        
        Args:
            filters: List of filter dictionaries from the event
            
        Returns:
            Filter with highest risk level or None if no filters
        """
        if not filters:
            return None
            
        highest_risk_value = -1
        selected_filter = None
        
        for filter_item in filters:
            risk_level = filter_item.get('riskLevel', 'info')
            risk_value = self.RISK_LEVEL_PRIORITY.get(risk_level, 0)
            
            if risk_value > highest_risk_value:
                highest_risk_value = risk_value
                selected_filter = filter_item
        
        return selected_filter
    
    def _extract_endpoint_hostname(self, event: Dict) -> str:
        """
        Extracts endpoint hostname from various possible locations in the event.
        
        Args:
            event: Raw event dictionary
            
        Returns:
            Extracted hostname or empty string
        """
        event_detail = event.get('detail', {})
        
        # Try different possible locations for hostname
        hostname = (
            event_detail.get('endpointHostName') or 
            self._extract_hostname_from_entity_name(event.get('entityName', '')) or
            event_detail.get('shost') or 
            ''
        )
        
        return hostname
    
    def _extract_endpoint_ip_address(self, event: Dict) -> str:
        """
        Extracts endpoint IP address from various possible locations in the event.
        
        Args:
            event: Raw event dictionary
            
        Returns:
            Extracted IP address or empty string
        """
        event_detail = event.get('detail', {})
        
        # Try to get IP from detail fields
        ip_list = event_detail.get('endpointIp') or event_detail.get('interestedIp') or []
        
        if isinstance(ip_list, list) and ip_list:
            return ip_list[0]
        elif isinstance(ip_list, str):
            return ip_list
        
        # Try to extract IP from entity name as fallback
        return self._extract_ip_from_entity_name(event.get('entityName', ''))
    
    def _extract_hostname_from_entity_name(self, entity_name: str) -> str:
        """Extracts hostname from entity name field."""
        if entity_name and '(' in entity_name:
            return entity_name.split('(')[0].strip()
        return ''
    
    def _extract_ip_from_entity_name(self, entity_name: str) -> str:
        """Extracts IP address from entity name field."""
        if '(' in entity_name and ')' in entity_name:
            ip_part = entity_name.split('(')[-1].split(')')[0]
            if '.' in ip_part:  # Basic IP validation
                return ip_part
        return ''
    
    def _is_valid_transformed_event(self, transformed_event: Dict, original_event: Dict) -> bool:
        """
        Validates that a transformed event has the minimum required fields.
        
        Args:
            transformed_event: The transformed event
            original_event: Original event for reference in logging
            
        Returns:
            True if event is valid, False otherwise
        """
        required_fields = ['detectedDateTime', 'name']
        return all(transformed_event.get(field) for field in required_fields)
