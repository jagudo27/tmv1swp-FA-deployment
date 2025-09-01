"""
Event data transformer for Trend Micro OAT events.
Transforms raw events from Trend Micro API into the format required by Log Analytics.
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Set


class TrendMicroEventTransformer:
    """Transforms Trend Micro OAT events for Log Analytics ingestion."""
    
    RISK_LEVEL_PRIORITY = {
        "critical": 4,
        "high": 3, 
        "medium": 2,
        "low": 1,
        "info": 0
    }
    
    # Schema de campos definidos en la DCR - solo estos campos se incluirán en el output
    DCR_SCHEMA_FIELDS = {
        # Identificadores y metadatos
        "uuid",
        "eventId", 
        "eventTime",
        "name",  # Nombre del filtro/detección que identifica el evento
        "pname",
        "filterRiskLevel",
        "tags",
        
        # Información del endpoint
        "endpointHostName",
        "endpointIp",
        "endpointMacAddress",
        "osName",
        "timezone",
        
        # Usuario y sesión
        "logonUser",
        "userDomain", 
        "sessionId",
        
        # Proceso principal
        "processCmd",
        "processFilePath",
        "processName",
        "processPid",
        "processUser",
        "processUserDomain",
        
        # Proceso padre
        "parentCmd",
        "parentFilePath",
        "parentName",
        "parentPid",
        "parentUser",
        "parentUserDomain",
        
        # Archivo u objeto involucrado
        "objectFilePath",
        "objectName",
        "objectUser",
        "objectUserDomain",
        "objectLaunchTime",
        
        # Conexiones de red
        "src",
        "spt",
        "dst", 
        "dpt",
        "proto",
        
        # Campos requeridos por Log Analytics
        "TimeGenerated"
    }
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"DCR Schema initialized with {len(self.DCR_SCHEMA_FIELDS)} fields")
        self.logger.debug(f"DCR Fields: {sorted(self.DCR_SCHEMA_FIELDS)}")
    
    def transform_events_for_log_analytics(self, raw_events: List[Dict]) -> List[Dict]:
        """
        Transforms raw Trend Micro events into Log Analytics custom table format.
        Maps only fields defined in DCR_SCHEMA_FIELDS, discards extra fields,
        and sets missing expected fields to null.
        
        Args:
            raw_events: List of raw events from Trend Micro API
            
        Returns:
            List of transformed events ready for Log Analytics
        """
        self.logger.info(f"Starting transformation of {len(raw_events)} events")
        
        transformed_events = []
        
        for i, event in enumerate(raw_events):
            try:
                transformed_event = self._transform_single_event(event)
                
                if self._is_valid_transformed_event(transformed_event, event):
                    transformed_events.append(transformed_event)
                else:
                    self.logger.warning(f"Skipping event {i+1}/{len(raw_events)} (uuid: {event.get('uuid', 'unknown')}) - validation failed")
                    
            except Exception as e:
                self.logger.error(f"Error transforming event {i+1}/{len(raw_events)} (uuid: {event.get('uuid', 'unknown')}): {str(e)}")
                continue
        
        self.logger.info(f"Transformation completed: {len(transformed_events)}/{len(raw_events)} events ready for Log Analytics")
        return transformed_events
    
    def _transform_single_event(self, raw_event: Dict) -> Dict:
        """
        Transforms a single raw event into Log Analytics format.
        Maps all available fields from the raw event to DCR schema fields,
        sets missing fields to null, and discards unmapped fields.
        
        Args:
            raw_event: Single raw event from Trend Micro API
            
        Returns:
            Transformed event dictionary with only DCR schema fields
        """
        # Initialize with all DCR fields set to null
        transformed_event = {field: None for field in self.DCR_SCHEMA_FIELDS}
        
        # Set TimeGenerated (required by Log Analytics)
        transformed_event["TimeGenerated"] = datetime.now(timezone.utc).isoformat()
        
        # Map fields from raw event to DCR schema
        self._map_identifiers_and_metadata(raw_event, transformed_event)
        self._map_endpoint_information(raw_event, transformed_event)
        self._map_user_and_session_info(raw_event, transformed_event)
        self._map_process_information(raw_event, transformed_event)
        self._map_parent_process_information(raw_event, transformed_event)
        self._map_object_information(raw_event, transformed_event)
        self._map_network_connections(raw_event, transformed_event)
        
        # Log mapping statistics for debugging
        filled_fields = [k for k, v in transformed_event.items() if v is not None]
        null_fields = [k for k, v in transformed_event.items() if v is None]
        
        self.logger.debug(f"Event {raw_event.get('uuid', 'unknown')}: {len(filled_fields)} fields mapped, {len(null_fields)} fields null")
        
        return transformed_event
    
    def _map_identifiers_and_metadata(self, raw_event: Dict, transformed_event: Dict) -> None:
        """Maps identifier and metadata fields."""
        transformed_event["uuid"] = raw_event.get("uuid")
        
        # Map eventId from detail section
        event_detail = raw_event.get('detail', {})
        transformed_event["eventId"] = event_detail.get("eventId")
        
        # Map eventTime - prioritize detectedDateTime, then detail.eventTime converted from timestamp
        transformed_event["eventTime"] = raw_event.get("detectedDateTime")
        if not transformed_event["eventTime"] and event_detail.get("eventTime"):
            # Convert from timestamp if needed
            event_time = event_detail.get("eventTime")
            if isinstance(event_time, str) and event_time.isdigit():
                # Convert from milliseconds timestamp
                from datetime import datetime, timezone
                timestamp_ms = int(event_time)
                dt = datetime.fromtimestamp(timestamp_ms / 1000, timezone.utc)
                transformed_event["eventTime"] = dt.isoformat()
        
        # Map name from filter name (highest priority filter)
        highest_risk_filter = self._find_highest_risk_filter(raw_event.get('filters', []))
        transformed_event["name"] = highest_risk_filter.get('name') if highest_risk_filter else None
        
        # Map pname from detail section
        transformed_event["pname"] = event_detail.get("pname") or raw_event.get("productCode")
        
        # Get filter risk level from highest priority filter
        transformed_event["filterRiskLevel"] = highest_risk_filter.get('riskLevel') if highest_risk_filter else event_detail.get("filterRiskLevel")
        
        # Map tags - could be in various formats
        tags = event_detail.get("tags") or raw_event.get("tags")
        if isinstance(tags, list):
            transformed_event["tags"] = ",".join(str(tag) for tag in tags)
        elif tags:
            transformed_event["tags"] = str(tags)
    
    def _map_endpoint_information(self, raw_event: Dict, transformed_event: Dict) -> None:
        """Maps endpoint information fields."""
        event_detail = raw_event.get('detail', {})
        
        # Map endpointHostName - clean up the name format
        hostname = event_detail.get("endpointHostName") or raw_event.get("entityName", "")
        if hostname:
            # Extract clean hostname from formats like "HOSTNAME ([IT][ES][TR1][PRO])"
            if "(" in hostname:
                hostname = hostname.split("(")[0].strip()
        transformed_event["endpointHostName"] = hostname
        
        # Map endpointIp - handle arrays
        ip_list = event_detail.get("endpointIp") or event_detail.get("interestedIp") or []
        if isinstance(ip_list, list) and ip_list:
            transformed_event["endpointIp"] = ip_list[0]
        elif isinstance(ip_list, str):
            transformed_event["endpointIp"] = ip_list
        else:
            # Try to extract from entityName as fallback
            entity_name = raw_event.get("entityName", "")
            if "(" in entity_name and ")" in entity_name:
                ip_part = entity_name.split("(")[-1].split(")")[0]
                if "." in ip_part and not "[" in ip_part:  # Basic IP validation, exclude tags
                    transformed_event["endpointIp"] = ip_part
        
        # Map other endpoint fields
        transformed_event["endpointMacAddress"] = event_detail.get("endpointMacAddress") or event_detail.get("macAddress")
        transformed_event["osName"] = event_detail.get("osName") or event_detail.get("os")
        transformed_event["timezone"] = event_detail.get("timezone") or event_detail.get("tz")
    
    def _map_user_and_session_info(self, raw_event: Dict, transformed_event: Dict) -> None:
        """Maps user and session information fields."""
        event_detail = raw_event.get('detail', {})
        
        transformed_event["logonUser"] = event_detail.get("logonUser") or event_detail.get("user") or event_detail.get("username")
        transformed_event["userDomain"] = event_detail.get("userDomain") or event_detail.get("domain")
        transformed_event["sessionId"] = event_detail.get("sessionId") or event_detail.get("session")
    
    def _map_process_information(self, raw_event: Dict, transformed_event: Dict) -> None:
        """Maps main process information fields."""
        event_detail = raw_event.get('detail', {})
        
        # For file/directory monitoring events, process info might not be available
        # But map what's available from various possible locations
        transformed_event["processCmd"] = (
            event_detail.get("processCmd") or 
            event_detail.get("cmd") or 
            event_detail.get("commandLine") or
            event_detail.get("command")
        )
        
        transformed_event["processFilePath"] = (
            event_detail.get("processFilePath") or 
            event_detail.get("filePath") or 
            event_detail.get("processPath") or
            event_detail.get("executablePath")
        )
        
        transformed_event["processName"] = (
            event_detail.get("processName") or 
            event_detail.get("process") or 
            event_detail.get("fname") or
            event_detail.get("executableName")
        )
        
        # Handle PID - could be string or int
        pid = (
            event_detail.get("processPid") or 
            event_detail.get("pid") or
            event_detail.get("processId")
        )
        if pid is not None:
            transformed_event["processPid"] = str(pid)
            
        transformed_event["processUser"] = (
            event_detail.get("processUser") or 
            event_detail.get("user") or
            event_detail.get("username") or
            event_detail.get("executableUser")
        )
        
        transformed_event["processUserDomain"] = (
            event_detail.get("processUserDomain") or 
            event_detail.get("userDomain") or
            event_detail.get("domain")
        )
    
    def _map_parent_process_information(self, raw_event: Dict, transformed_event: Dict) -> None:
        """Maps parent process information fields."""
        event_detail = raw_event.get('detail', {})
        
        transformed_event["parentCmd"] = event_detail.get("parentCmd") or event_detail.get("parentCommandLine")
        transformed_event["parentFilePath"] = event_detail.get("parentFilePath") or event_detail.get("parentPath")
        transformed_event["parentName"] = event_detail.get("parentName") or event_detail.get("parentProcess")
        
        # Handle parent PID - could be string or int
        parent_pid = event_detail.get("parentPid") or event_detail.get("ppid")
        if parent_pid is not None:
            transformed_event["parentPid"] = str(parent_pid)
            
        transformed_event["parentUser"] = event_detail.get("parentUser")
        transformed_event["parentUserDomain"] = event_detail.get("parentUserDomain")
    
    def _map_object_information(self, raw_event: Dict, transformed_event: Dict) -> None:
        """Maps file/object information fields."""
        event_detail = raw_event.get('detail', {})
        
        # For integrity monitoring events, the main object is often in filePathName or fullPath
        transformed_event["objectFilePath"] = (
            event_detail.get("filePathName") or 
            event_detail.get("fullPath") or 
            event_detail.get("objectFilePath") or 
            event_detail.get("objectPath") or 
            event_detail.get("targetFilePath")
        )
        
        # Extract object name from path if available
        file_path = transformed_event["objectFilePath"]
        if file_path:
            if "/" in file_path:
                transformed_event["objectName"] = file_path.split("/")[-1]
            elif "\\" in file_path:
                transformed_event["objectName"] = file_path.split("\\")[-1]
            else:
                transformed_event["objectName"] = file_path
        else:
            transformed_event["objectName"] = (
                event_detail.get("objectName") or 
                event_detail.get("objectFile") or 
                event_detail.get("targetFileName")
            )
        
        transformed_event["objectUser"] = event_detail.get("objectUser") or event_detail.get("fileOwner")
        transformed_event["objectUserDomain"] = event_detail.get("objectUserDomain") or event_detail.get("fileOwnerDomain")
        
        # Map file operation time - could be in different formats
        transformed_event["objectLaunchTime"] = (
            event_detail.get("objectLaunchTime") or 
            event_detail.get("accessTime") or 
            event_detail.get("execTime") or
            event_detail.get("fileCreation") or
            event_detail.get("objectFileCreation")
        )
    
    def _map_network_connections(self, raw_event: Dict, transformed_event: Dict) -> None:
        """Maps network connection information fields."""
        event_detail = raw_event.get('detail', {})
        
        transformed_event["src"] = event_detail.get("src") or event_detail.get("sourceIp") or event_detail.get("shost")
        transformed_event["spt"] = event_detail.get("spt") or event_detail.get("sourcePort") or event_detail.get("sport")
        transformed_event["dst"] = event_detail.get("dst") or event_detail.get("destinationIp") or event_detail.get("dhost")
        transformed_event["dpt"] = event_detail.get("dpt") or event_detail.get("destinationPort") or event_detail.get("dport")
        transformed_event["proto"] = event_detail.get("proto") or event_detail.get("protocol")
        
        # Convert port numbers to strings if they're integers
        for port_field in ["spt", "dpt"]:
            if transformed_event[port_field] is not None:
                transformed_event[port_field] = str(transformed_event[port_field])
    
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
        For OAT events, we require at least uuid and eventTime to be present.
        Name is also highly recommended for identification.
        
        Args:
            transformed_event: The transformed event
            original_event: Original event for reference in logging
            
        Returns:
            True if event is valid, False otherwise
        """
        required_fields = ['uuid', 'eventTime']
        missing_fields = [field for field in required_fields if not transformed_event.get(field)]
        
        if missing_fields:
            self.logger.warning(f"Event validation failed - missing required fields: {missing_fields}")
            return False
        
        # Log warning if name is missing (not blocking but important for identification)
        if not transformed_event.get('name'):
            self.logger.warning(f"Event {transformed_event.get('uuid', 'unknown')} missing 'name' field for identification")
        
        return True
    
    def get_dcr_schema_fields(self) -> Set[str]:
        """
        Returns the set of fields defined in the DCR schema.
        Useful for validation and debugging.
        
        Returns:
            Set of field names that will be included in transformed events
        """
        return self.DCR_SCHEMA_FIELDS.copy()
    
    def validate_raw_event_coverage(self, raw_events: List[Dict]) -> Dict[str, int]:
        """
        Analyzes raw events to see which DCR fields are commonly populated.
        Useful for debugging and understanding data quality.
        
        Args:
            raw_events: List of raw events to analyze
            
        Returns:
            Dictionary with field names and count of events that have that field
        """
        field_coverage = {field: 0 for field in self.DCR_SCHEMA_FIELDS}
        
        for event in raw_events:
            # Simulate transformation to see which fields would be populated
            temp_transformed = {field: None for field in self.DCR_SCHEMA_FIELDS}
            temp_transformed["TimeGenerated"] = "dummy"
            
            try:
                self._map_identifiers_and_metadata(event, temp_transformed)
                self._map_endpoint_information(event, temp_transformed)
                self._map_user_and_session_info(event, temp_transformed)
                self._map_process_information(event, temp_transformed)
                self._map_parent_process_information(event, temp_transformed)
                self._map_object_information(event, temp_transformed)
                self._map_network_connections(event, temp_transformed)
                
                # Count populated fields
                for field, value in temp_transformed.items():
                    if value is not None and value != "dummy":
                        field_coverage[field] += 1
                        
            except Exception as e:
                self.logger.warning(f"Error analyzing event coverage: {str(e)}")
                continue
        
        return field_coverage
