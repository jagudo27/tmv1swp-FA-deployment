import azure.functions as func
import logging
import json
import os
from datetime import datetime, timedelta, timezone
import requests
from azure.monitor.ingestion import LogsIngestionClient
from azure.identity import DefaultAzureCredential

# Configurar logging para Azure
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main(mytimer: func.TimerRequest) -> None:
    """
    Function App que extrae eventos OAT de Trend Micro y los envía a Log Analytics
    Ejecuta cada 5 minutos: 0 */5 * * * *
    """
    logging.info("TREND MICRO ETL FUNCTION STARTED")
    
    if mytimer.past_due:
        logging.warning('The timer is past due!')

    try:
        # Verificar variables de entorno primero
        logging.info("Checking environment variables...")
        
        required_vars = ["TREND_MICRO_TOKEN", "DATA_COLLECTION_ENDPOINT", "DATA_COLLECTION_RULE_ID"]
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        
        if missing_vars:
            error_msg = f"Missing required environment variables: {missing_vars}"
            logging.error(error_msg)
            raise ValueError(error_msg)

        # Configuración desde variables de entorno
        token = os.environ["TREND_MICRO_TOKEN"]
        data_collection_endpoint = os.environ["DATA_COLLECTION_ENDPOINT"]
        data_collection_rule_id = os.environ["DATA_COLLECTION_RULE_ID"]
        stream_name = os.environ.get("STREAM_NAME", "TrendMicroOAT_CL")
        
        logging.info("=== TREND MICRO OAT ETL STARTED ===")
        
        # Extraer eventos de Trend Micro
        events_data = fetch_sds_oat_events(token)
        
        if events_data and events_data.get('items'):
            events = events_data['items']
            total_count = events_data.get('totalCount', 0)
            
            logging.info(f"Total events available in API: {total_count}")
            logging.info(f"Events extracted: {len(events)}")
            
            # Transformar eventos para Log Analytics
            transformed_events = transform_events_for_log_analytics(events)
            logging.info(f"Events transformed: {len(transformed_events)}")
            
            # Enviar a Log Analytics si hay eventos
            if transformed_events:
                send_to_log_analytics(
                    transformed_events, 
                    data_collection_endpoint,
                    data_collection_rule_id,
                    stream_name
                )
                logging.info(f"SUCCESS: {len(transformed_events)} events sent to Log Analytics")
            else:
                logging.warning("No events to send after transformation")
        else:
            logging.info("No events found in Trend Micro API")
            
        logging.info("=== TREND MICRO OAT ETL COMPLETED ===")
            
    except Exception as e:
        error_msg = f"ERROR in ETL process: {str(e)}"
        logging.error(error_msg)
        raise

def fetch_sds_oat_events(token):
    """
    Extrae eventos OAT de Server & Workload Protection (SDS) de Trend Micro Vision One
    Solo eventos medium, high, critical de las últimas 24 horas
    """
    logging.info("Starting to fetch events from Trend Micro API")
    
    url_base = 'https://api.eu.xdr.trendmicro.com'
    url_path = '/v3.0/oat/detections'
    
    # Rango temporal - últimas 24 horas
    now = datetime.now(timezone.utc)
    last_24_hours = now - timedelta(hours=4)
    
    detected_start_date = last_24_hours.strftime('%Y-%m-%dT%H:%M:%SZ')
    detected_end_date = now.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    query_params = {
        'detectedStartDateTime': detected_start_date,
        'detectedEndDateTime': detected_end_date,
        'top': 6000  # Máximo permitido por Trend Micro API
    }
    
    # Filtros: Solo SDS + solo eventos relevantes para seguridad
    headers = {
        'Authorization': f'Bearer {token}',
        'TMV1-Filter': "productCode eq 'sds' and (riskLevel eq 'high' or riskLevel eq 'critical' or riskLevel eq 'medium')"
    }
    
    all_events = []
    total_count = 0
    url = f"{url_base}{url_path}"
    page_count = 0
    
    logging.info(f"Fetching SDS OAT events from {detected_start_date} to {detected_end_date}")
    logging.info(f"Filter: SDS events with medium/high/critical risk only")
    
    while True:
        page_count += 1
        try:
            response = requests.get(url, params=query_params, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                all_events.extend(items)
                
                # Capturar totalCount del primer response
                if total_count == 0:
                    total_count = data.get('totalCount', len(all_events))
                
                logging.info(f"Page {page_count}: Retrieved {len(items)} events. Total so far: {len(all_events)}")
                
                # Verificar si hay más páginas
                next_link = data.get('nextLink')
                if next_link:
                    url = next_link
                    query_params = {}  # Limpiar parámetros para nextLink
                else:
                    logging.info(f"Pagination completed. Total pages: {page_count}")
                    break
                    
            elif response.status_code == 403:
                error_msg = "Access forbidden (403). Check API token or permissions."
                logging.error(error_msg)
                break
            elif response.status_code == 400:
                error_msg = f"Bad Request (400). Response: {response.text}"
                logging.error(error_msg)
                break
            else:
                error_msg = f"API request failed: {response.status_code} - {response.text}"
                logging.error(error_msg)
                break
                
        except requests.exceptions.Timeout:
            error_msg = f"Timeout on page {page_count}"
            logging.error(error_msg)
            break
        except Exception as e:
            error_msg = f"Error fetching page {page_count}: {str(e)}"
            logging.error(error_msg)
            break
    
    logging.info(f"Extraction completed: {len(all_events)} events extracted from {total_count} available")
    
    return {
        "totalCount": total_count,
        "count": len(all_events),
        "items": all_events
    }

def transform_events_for_log_analytics(events):
    """
    Transforma eventos de Trend Micro para enviar a Log Analytics Custom Table
    Extrae solo los 5 campos requeridos: detectedDateTime, name, riskLevel, endpointHostName, endpointIp
    """
    logging.info(f"Starting transformation of {len(events)} events")
    
    transformed = []
    
    for event in events:
        try:
            # Buscar el filtro con riskLevel más alto
            selected_filter = get_highest_risk_filter(event.get('filters', []))
            
            # Extraer campos específicos
            transformed_event = {
                "TimeGenerated": datetime.now(timezone.utc).isoformat(),
                "detectedDateTime": event.get('detectedDateTime', ''),
                "name": selected_filter.get('name', '') if selected_filter else '',
                "riskLevel": selected_filter.get('riskLevel', '') if selected_filter else '',
                "endpointHostName": extract_endpoint_hostname(event),
                "endpointIp": extract_endpoint_ip(event)
            }
            
            # Solo añadir si tiene datos mínimos válidos
            if transformed_event['detectedDateTime'] and transformed_event['name']:
                transformed.append(transformed_event)
            else:
                logging.warning(f"Skipping event {event.get('uuid', 'unknown')} - missing required fields")
                
        except Exception as e:
            logging.error(f"Error transforming event {event.get('uuid', 'unknown')}: {str(e)}")
            continue
    
    logging.info(f"Transformation completed: {len(transformed)} events ready for Log Analytics")
    return transformed

def get_highest_risk_filter(filters):
    """
    Selecciona el filtro con el riskLevel más alto
    """
    if not filters:
        return None
        
    risk_priority = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
    highest_risk = -1
    selected_filter = None
    
    for filter_item in filters:
        risk_level = filter_item.get('riskLevel', 'info')
        risk_value = risk_priority.get(risk_level, 0)
        if risk_value > highest_risk:
            highest_risk = risk_value
            selected_filter = filter_item
    
    return selected_filter

def extract_endpoint_hostname(event):
    """
    Extrae endpointHostName de diferentes posibles ubicaciones
    """
    detail = event.get('detail', {})
    
    # Intentar diferentes campos
    hostname = (
        detail.get('endpointHostName') or 
        event.get('entityName', '').split('(')[0].strip() or
        detail.get('shost') or 
        ''
    )
    
    return hostname

def extract_endpoint_ip(event):
    """
    Extrae endpointIp de diferentes posibles ubicaciones
    """
    detail = event.get('detail', {})
    
    # Intentar diferentes campos
    ip_list = detail.get('endpointIp') or detail.get('interestedIp') or []
    
    if isinstance(ip_list, list) and ip_list:
        return ip_list[0]
    elif isinstance(ip_list, str):
        return ip_list
    
    # Intentar extraer de entityName
    entity_name = event.get('entityName', '')
    if '(' in entity_name and ')' in entity_name:
        ip_part = entity_name.split('(')[-1].split(')')[0]
        if '.' in ip_part:  # Verificar que parece una IP
            return ip_part
    
    return ''

def send_to_log_analytics(events, data_collection_endpoint, rule_id, stream_name):
    """
    Envía eventos transformados a Log Analytics Custom Table
    """
    logging.info(f"Starting upload of {len(events)} events to Log Analytics")
    
    try:
        # Usar Managed Identity para autenticación
        credential = DefaultAzureCredential()
        
        logging.info(f"Connecting to Log Analytics: {data_collection_endpoint}")
        logging.info(f"Using DCR: {rule_id}")
        logging.info(f"Target stream: {stream_name}")
        
        # Cliente de Log Analytics Ingestion
        client = LogsIngestionClient(
            endpoint=data_collection_endpoint,
            credential=credential,
            logging_enable=True
        )
        
        # Enviar datos en lotes (máximo 1MB por request)
        batch_size = 100  # Ajustar si es necesario
        total_sent = 0
        
        for i in range(0, len(events), batch_size):
            batch = events[i:i+batch_size]
            
            try:
                client.upload(
                    rule_id=rule_id,
                    stream_name=stream_name,
                    logs=batch
                )
                total_sent += len(batch)
                logging.info(f"Batch {i//batch_size + 1}: Sent {len(batch)} events to Log Analytics")
                
            except Exception as batch_error:
                error_msg = f"Error sending batch {i//batch_size + 1}: {str(batch_error)}"
                logging.error(error_msg)
                raise
        
        logging.info(f"Successfully uploaded {total_sent} events to {stream_name}")
        
    except Exception as e:
        error_msg = f"Failed to send data to Log Analytics: {str(e)}"
        logging.error(error_msg)
        raise
