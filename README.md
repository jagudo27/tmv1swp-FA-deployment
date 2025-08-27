# Trend Micro ETL Azure Function - Código Refactorizado

## 🏗️ Arquitectura Basada en SRP (Single Responsibility Principle)

Este proyecto ha sido refactorizado para seguir principios de código limpio y mantenible, aplicando el **Principio de Responsabilidad Única (SRP)** y mejorando la legibilidad y mantenibilidad del código.

## 📁 Estructura del Proyecto

```
├── shared_code/                          # Módulos compartidos organizados por responsabilidad
│   ├── __init__.py                       # Inicializador del paquete
│   ├── trend_micro_etl.py               # Función principal (coordinadora del ETL)
│   ├── environment_validator.py          # Validación y configuración del entorno
│   ├── trend_micro_api_client.py        # Cliente de la API de Trend Micro
│   ├── event_data_transformer.py        # Transformación de datos de eventos
│   └── log_analytics_client.py          # Cliente de Azure Log Analytics
├── trend_micro_etl/                      # Azure Function específica
│   ├── __init__.py                      # Punto de entrada de la función
│   └── function.json                    # Configuración de la función Azure
├── deployment/                           # Infraestructura como código
│   ├── azuredeploy.json                 # Plantilla ARM
│   ├── azuredeploy.parameters.json      # Parámetros de despliegue
│   └── README.md                        # Guía de despliegue
├── .github/workflows/                    # CI/CD con GitHub Actions
├── host.json                            # Configuración del host de Azure Functions
├── local.settings.json                  # Configuración local de desarrollo
├── requirements.txt                     # Dependencias de Python
└── deploy.ps1                          # Script de despliegue PowerShell
```

## 🔧 Módulos y Responsabilidades

### 1. `environment_validator.py`
**Responsabilidad:** Validación y configuración del entorno
- ✅ Validar variables de entorno requeridas
- ✅ Sanear y limpiar configuraciones
- ✅ Proporcionar configuración validada a otros módulos
- ✅ Logging detallado para depuración

**Clases:**
- `EnvironmentConfiguration`: Objeto de configuración inmutable
- `EnvironmentValidator`: Validador con métodos descriptivos

### 2. `trend_micro_api_client.py`
**Responsabilidad:** Comunicación con la API de Trend Micro
- ✅ Autenticación con tokens Bearer
- ✅ Paginación automática de resultados
- ✅ Filtrado de eventos por riesgo y producto
- ✅ Manejo de errores y timeouts
- ✅ Configuración de rangos temporales

**Clases:**
- `TrendMicroApiClient`: Cliente con métodos con nombres descriptivos

### 3. `event_data_transformer.py`
**Responsabilidad:** Transformación de datos de eventos
- ✅ Mapeo de eventos raw a formato Log Analytics
- ✅ Extracción de campos específicos
- ✅ Selección de filtros por nivel de riesgo
- ✅ Validación de eventos transformados
- ✅ Generación de TimeGenerated automático

**Clases:**
- `TrendMicroEventTransformer`: Transformador con lógica clara y métodos específicos

### 4. `log_analytics_client.py`
**Responsabilidad:** Ingesta de datos a Azure Log Analytics
- ✅ Autenticación con Managed Identity
- ✅ Envío de datos en lotes configurables
- ✅ Validación de endpoints y configuración
- ✅ Manejo de errores detallado
- ✅ Limpieza de URLs y parámetros

**Clases:**
- `LogAnalyticsIngestionClient`: Cliente con métodos para envío seguro y confiable

### 5. `trend_micro_etl.py` (Función Principal)
**Responsabilidad:** Coordinación del proceso ETL
- ✅ Orquestación de los módulos especializados
- ✅ Manejo de errores global
- ✅ Logging del flujo principal
- ✅ Punto de entrada para Azure Functions

## 🏆 Beneficios de la Refactorización

### ✅ **Principio de Responsabilidad Única (SRP)**
- Cada clase tiene una única razón para cambiar
- Módulos especializados y enfocados
- Fácil localización de funcionalidades

### ✅ **Nombres Descriptivos**
- Métodos con nombres que explican su propósito
- Variables claras y autodocumentadas
- Clases que representan conceptos del dominio

### ✅ **Mantenibilidad**
- Código modular y reutilizable
- Fácil testing unitario por módulo
- Cambios aislados en componentes específicos

### ✅ **Legibilidad**
- Flujo principal claro y conciso
- Separación lógica de responsabilidades
- Documentación inline y docstrings

## 🚀 Uso y Desarrollo

### **Función Principal:**
```python
# La función main() en trend_micro_etl.py coordina todo el proceso:
def main(mytimer: func.TimerRequest) -> None:
    # 1. Validar entorno
    config = EnvironmentValidator().validate_and_load_configuration()
    
    # 2. Extraer eventos
    client = TrendMicroApiClient(config.trend_micro_token)
    api_response = client.fetch_security_events_from_last_hours()
    
    # 3. Transformar datos
    transformer = TrendMicroEventTransformer()
    events = transformer.transform_events_for_log_analytics(api_response['items'])
    
    # 4. Enviar a Log Analytics
    log_client = LogAnalyticsIngestionClient(config.data_collection_endpoint, ...)
    log_client.send_events_to_log_analytics(events)
```

### **Testing Individual:**
```python
# Cada módulo puede probarse independientemente
from shared_code.environment_validator import EnvironmentValidator
from shared_code.trend_micro_api_client import TrendMicroApiClient

# Test de validación
validator = EnvironmentValidator()
config = validator.validate_and_load_configuration()

# Test de API client
client = TrendMicroApiClient("test-token")
events = client.fetch_security_events_from_last_hours(hours=1)
```

## 🔒 Seguridad y Buenas Prácticas

- ✅ **Managed Identity** para autenticación
- ✅ **Validación estricta** de parámetros de entrada
- ✅ **Sanitización** de URLs y endpoints
- ✅ **Logging seguro** (sin tokens en logs)
- ✅ **Manejo de errores** robusto
- ✅ **Timeouts configurables** para evitar colgado

## 📊 Variables de Entorno Requeridas

```bash
TREND_MICRO_TOKEN=<tu_token_bearer>           # Token de API de Trend Micro
DATA_COLLECTION_ENDPOINT=<endpoint_url>       # URL del Data Collection Endpoint
DATA_COLLECTION_RULE_ID=<dcr_id>             # ID de Data Collection Rule
STREAM_NAME=Custom-TrendMicroOATEvents_CL     # Nombre del stream (opcional)
```

## 🔄 Versionado y Actualizaciones

- **v1.0.0**: Versión monolítica original
- **v2.0.0**: Refactorización con SRP, nombres descriptivos y código limpio
- Próximas versiones: Testing automatizado, métricas de performance

---

## 💡 Filosofía de Desarrollo

> "Clean code is not written by following a set of rules. You don't become a software craftsman by learning a list of heuristics. Professionalism and craftsmanship come from values that drive disciplines." - Robert C. Martin

Este código fue refactorizado siguiendo principios de **Clean Code** y **SOLID**, priorizando:

1. **Legibilidad** sobre brevedad
2. **Responsabilidad única** sobre acoplamiento
3. **Nombres expresivos** sobre comentarios explicativos
4. **Módulos especializados** sobre funciones gigantes
5. **Testabilidad** sobre complejidad
