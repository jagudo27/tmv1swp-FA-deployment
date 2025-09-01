"""
Trend Micro API client for extracting OAT (Operation Anomaly Threat) events.
Handles communication with Trend Micro Vision One API to fetch security events.
"""

import logging
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional


class TrendMicroApiClient:
    """Client for interacting with Trend Micro Vision One API to fetch OAT events."""
    
    BASE_URL = 'https://api.eu.xdr.trendmicro.com'
    OAT_ENDPOINT = '/v3.0/oat/detections'
    MAX_EVENTS_PER_REQUEST = 6000
    REQUEST_TIMEOUT_SECONDS = 30
    LOOKBACK_HOURS = 4
    
    def __init__(self, api_token: str):
        """
        Initialize the Trend Micro API client.
        
        Args:
            api_token: Bearer token for API authentication
        """
        self.api_token = api_token
        self.logger = logging.getLogger(__name__)
    
    def fetch_security_events_from_last_hours(self, hours: int = None) -> Dict:
        """
        Fetches OAT security events from the specified number of hours ago until now.
        Only retrieves medium, high, and critical risk events from Server & Workload Protection (SDS).
        
        Args:
            hours: Number of hours to look back (defaults to LOOKBACK_HOURS)
            
        Returns:
            Dict containing totalCount, count, and items list
        """
        if hours is None:
            hours = self.LOOKBACK_HOURS
            
        time_range = self._calculate_time_range(hours)
        headers = self._build_request_headers()
        query_params = self._build_query_parameters(time_range)
        
        self.logger.info(f"Fetching SDS OAT events from {time_range['start']} to {time_range['end']}")
        self.logger.info("Filter: SDS events with medium/high/critical risk only")
        
        return self._fetch_all_pages(headers, query_params)
    
    def _calculate_time_range(self, hours: int) -> Dict[str, str]:
        """Calculates the time range for the API query."""
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(hours=hours)
        
        return {
            'start': start_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'end': now.strftime('%Y-%m-%dT%H:%M:%SZ')
        }
    
    def _build_request_headers(self) -> Dict[str, str]:
        """Builds the HTTP headers for API requests."""
        return {
            'Authorization': f'Bearer {self.api_token}',
            'TMV1-Filter': "productCode eq 'sds' and (riskLevel eq 'high' or riskLevel eq 'critical' or riskLevel eq 'medium')"
        }
    
    def _build_query_parameters(self, time_range: Dict[str, str]) -> Dict[str, str]:
        """Builds the query parameters for the API request."""
        return {
            'detectedStartDateTime': time_range['start'],
            'detectedEndDateTime': time_range['end'],
            'top': self.MAX_EVENTS_PER_REQUEST
        }
    
    def _fetch_all_pages(self, headers: Dict[str, str], initial_params: Dict[str, str]) -> Dict:
        """
        Fetches all pages of events using pagination.
        
        Args:
            headers: HTTP headers for the request
            initial_params: Initial query parameters
            
        Returns:
            Dict with totalCount, count, and items
        """
        all_events = []
        total_count = 0
        url = f"{self.BASE_URL}{self.OAT_ENDPOINT}"
        query_params = initial_params
        page_count = 0
        
        while True:
            page_count += 1
            try:
                page_result = self._fetch_single_page(url, headers, query_params, page_count)
                
                if page_result is None:
                    break
                
                events, total_count, next_url = page_result
                all_events.extend(events)
                
                if next_url:
                    url = next_url
                    query_params = {}  # Clear params for next link
                else:
                    self.logger.info(f"Pagination completed. Total pages: {page_count}")
                    break
                    
            except Exception as e:
                self.logger.error(f"Error fetching page {page_count}: {str(e)}")
                break
        
        self.logger.info(f"Extraction completed: {len(all_events)} events extracted from {total_count} available")
        
        return {
            "totalCount": total_count,
            "count": len(all_events),
            "items": all_events
        }
    
    def _fetch_single_page(self, url: str, headers: Dict[str, str], 
                          query_params: Dict[str, str], page_number: int) -> Optional[tuple]:
        """
        Fetches a single page of events from the API.
        
        Returns:
            Tuple of (events_list, total_count, next_url) or None if error
        """
        try:
            response = requests.get(
                url, 
                params=query_params, 
                headers=headers, 
                timeout=self.REQUEST_TIMEOUT_SECONDS
            )
            
            if response.status_code == 200:
                return self._process_successful_response(response, page_number)
            else:
                self._handle_error_response(response)
                return None
                
        except requests.exceptions.Timeout:
            self.logger.error(f"Timeout on page {page_number}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error on page {page_number}: {str(e)}")
            return None
    
    def _process_successful_response(self, response: requests.Response, page_number: int) -> tuple:
        """Processes a successful API response."""
        data = response.json()
        events = data.get('items', [])
        total_count = data.get('totalCount', 0)
        next_url = data.get('nextLink')
        
        self.logger.info(f"Page {page_number}: Retrieved {len(events)} events")
        
        return events, total_count, next_url
    
    def _handle_error_response(self, response: requests.Response) -> None:
        """Handles error responses from the API."""
        if response.status_code == 403:
            self.logger.error("Access forbidden (403). Check API token or permissions.")
        elif response.status_code == 400:
            self.logger.error(f"Bad Request (400). Response: {response.text}")
        else:
            self.logger.error(f"API request failed: {response.status_code} - {response.text}")
