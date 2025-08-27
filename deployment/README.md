# 🚀 Despliegue COMPLETO de Trend Micro ETL Function App

Esta plantilla ARM despliega **TODA** la infraestructura necesaria automáticamente, incluyendo Log Analytics, Data Collection Endpoint/Rule y conecta directamente al repositorio de GitHub.

## 📋 ¿Qué despliega esta plantilla?

- ✅ **Log Analytics Workspace** (para almacenar logs)
- ✅ **Data Collection Endpoint (DCE)** (endpoint de ingesta)
- ✅ **Data Collection Rule (DCR)** (reglas de transformación)
- ✅ **Function App** (Linux, Python 3.12)
- ✅ **App Service Plan** (Consumption Y1)
- ✅ **Storage Account** (para Function App)
- ✅ **Managed Identity** (System Assigned)
- ✅ **Conexión automática** a GitHub repo
- ✅ **Variables de entorno** configuradas

> **⚠️ Nota**: Los permisos para Log Analytics se configuran manualmente después del despliegue.

## 🔧 Parámetros Requeridos

### **Antes del despliegue, solo necesitas:**

1. **Trend Micro Token**: Tu token de API de Trend Micro
2. **Nombre único**: Para Function App y Storage Account

**¡ESO ES TODO!** La plantilla crea automáticamente:
- Log Analytics Workspace
- Data Collection Endpoint y Rule
- Todos los permisos necesarios

## 🚀 Opción 1: Despliegue via Azure Portal

### **Deploy to Azure Button:**

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fjagudo27%2Ftmv1swp-FA-deployment%2Fmain%2Fdeployment%2Fazuredeploy.json)

### **Pasos:**
1. **Click** en "Deploy to Azure"
2. **Login** en Azure Portal
3. **Completar parámetros**:
   - Function App Name: `mi-trend-micro-etl`
   - Storage Account Name: `mitrendmicrostorage` (único en Azure)
   - Trend Micro Token: `tu_token_aqui`
4. **Review + Create** → **Create**

**¡La plantilla crea automáticamente Log Analytics, DCE y DCR!**

## 🚀 Opción 2: Despliegue via Azure CLI

### **Paso 1: Descargar archivos**
```bash
# Descargar template y parámetros
curl -O https://raw.githubusercontent.com/jagudo27/tmv1swp-FA-deployment/main/deployment/azuredeploy.json
curl -O https://raw.githubusercontent.com/jagudo27/tmv1swp-FA-deployment/main/deployment/azuredeploy.parameters.json
```

### **Paso 2: Editar parámetros**
```json
# Editar azuredeploy.parameters.json
{
    "parameters": {
        "functionAppName": {
            "value": "TU_NOMBRE_FUNCTION_APP"
        },
        "storageAccountName": {
            "value": "TU_STORAGE_ACCOUNT_UNICO"
        },
        "TREND_MICRO_TOKEN": {
            "value": "TU_TOKEN_TREND_MICRO"
        }
    }
}
```

### **Paso 3: Desplegar**
```bash
# Login
az login

# Crear resource group (si no existe)
az group create --name "mi-resource-group" --location "North Europe"

# Desplegar template
az deployment group create \
  --resource-group "mi-resource-group" \
  --template-file azuredeploy.json \
  --parameters @azuredeploy.parameters.json
```

## 🚀 Opción 3: Despliegue via PowerShell

```powershell
# Login
Connect-AzAccount

# Crear resource group (si no existe)
New-AzResourceGroup -Name "mi-resource-group" -Location "North Europe"

# Desplegar template
New-AzResourceGroupDeployment `
  -ResourceGroupName "mi-resource-group" `
  -TemplateUri "https://raw.githubusercontent.com/jagudo27/tmv1swp-FA-deployment/main/deployment/azuredeploy.json" `
  -functionAppName "mi-trend-micro-etl" `
  -storageAccountName "mitrendmicrostorage" `
  -TREND_MICRO_TOKEN "tu_token_aqui"
```

## ✅ Post-Despliegue (IMPORTANTE)

### **1. Configurar Permisos Log Analytics (REQUERIDO)**

Después del despliegue, **DEBES** configurar permisos para que la Function App pueda enviar datos a Log Analytics:

```bash
# Obtener Principal ID de la salida del template (aparece al final del despliegue)
PRINCIPAL_ID="<principal_id_from_output>"
DCR_NAME="<dcr_name_from_output>"
SUBSCRIPTION_ID="<your_subscription_id>"
RESOURCE_GROUP="<your_resource_group>"

# Asignar rol "Monitoring Metrics Publisher"
az role assignment create \
  --assignee $PRINCIPAL_ID \
  --role "3913510d-42f4-4e42-8a64-420c390055eb" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Insights/dataCollectionRules/$DCR_NAME"
```

**O via Azure Portal:**
1. **Azure Portal** → **Data Collection Rules** → **Tu DCR creado**
2. **Access control (IAM)** → **Add role assignment**
3. **Role**: "Monitoring Metrics Publisher"
4. **Assign access to**: "Managed Identity"
5. **Members**: Seleccionar tu Function App

### **2. Verificar Función**
- **Azure Portal** → Function App → Functions
- **Debería aparecer**: `trend_micro_etl`
- **Estado**: Enabled
- **Trigger**: Timer (cada 5 minutos)

### **3. Monitorear Logs**
- **Azure Portal** → Function App → Monitor → Log stream
- **Buscar**: Ejecuciones cada 5 minutos
- **Verificar**: Sin errores de autenticación

## 🔧 Personalización

### **Cambiar frecuencia del timer:**
1. **Portal** → Function App → Functions → trend_micro_etl
2. **Integration** → Timer trigger
3. **Modificar schedule**: `0 */X * * * *` (X = minutos)

### **Variables adicionales:**
```bash
# Añadir via CLI
az functionapp config appsettings set \
  --name "tu-function-app" \
  --resource-group "tu-resource-group" \
  --settings "MI_VARIABLE=mi_valor"
```

## 🆘 Solución de Problemas

### **Error: Storage Account ya existe**
- Cambiar `storageAccountName` por algo único

### **Error: Function App ya existe**
- Cambiar `functionAppName` por algo único

### **Error: Autenticación Log Analytics**
- Verificar permisos "Monitoring Metrics Publisher"
- Verificar Data Collection Rule ID

### **Error: No aparece función**
- Esperar 2-3 minutos después del despliegue
- Verificar conexión GitHub en Deployment Center

## 📞 Soporte

- **GitHub Issues**: https://github.com/jagudo27/tmv1swp-FA-deployment/issues
- **Documentación**: Ver archivos .md en el repositorio
- **Logs**: Azure Portal → Function App → Monitor

## 🔄 Actualizaciones

El código se actualiza automáticamente desde GitHub. No necesita redeployar la infraestructura para actualizaciones de código.
