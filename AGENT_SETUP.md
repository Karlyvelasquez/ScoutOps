# SRE Agent - Setup y Uso

## 🚀 Quick Start

### 1. Crear Entorno Virtual

```bash
python -m venv venv
```

Activar el entorno virtual:

**Windows (PowerShell):**
```bash
.\venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```bash
venv\Scripts\activate
```

**Mac/Linux:**
```bash
source venv/bin/activate
```

### 2. Instalación de Dependencias

```bash
pip install -r requirements.txt
```

### 3. Configuración de Variables de Entorno

Copia el archivo `.env.example` a `.env`:

```bash
cp .env.example .env
```

Edita `.env` y agrega tu API key de Gemini:

```env
GEMINI_API_KEY=tu_api_key_aqui
MODEL_NAME=gemini-2.5-flash
TEMPERATURE=0.3
MAX_OUTPUT_TOKENS=2048
LOG_LEVEL=INFO
INCIDENTS_DATA_DIR=./data/incidents
```

**Obtener API Key de Gemini:**
1. Visita: https://aistudio.google.com/app/apikey
2. Crea un nuevo API key
3. Copia y pega en `.env`

### 3. Probar el Agente

Ejecuta el script de prueba:

```bash
python test_agent.py
```

Este script probará 3 escenarios:
- ✅ Checkout failure (error de pago)
- ✅ Login error (error de autenticación)
- ✅ Catalog issue (problema de catálogo)

### 4. Iniciar el Backend API

```bash
cd apps/backend
uvicorn app.main:app --reload --port 8000
```

La API estará disponible en: http://localhost:8000

**Documentación interactiva:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📡 Uso de la API

### Crear un Incidente

```bash
curl -X POST http://localhost:8000/incident \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Users getting 500 error when trying to pay with credit card",
    "source": "QA"
  }'
```

**Respuesta:**
```json
{
  "incident_id": "abc-123-def",
  "incident_type": "checkout_failure",
  "severity": "P1",
  "affected_plugin": "api-plugin-payments-stripe",
  "layer": "GraphQL resolver",
  "assigned_team": "payments-team",
  "summary": "Users cannot complete checkout due to payment processing errors...",
  "suggested_actions": [
    "Check Stripe API status",
    "Inspect payment resolver logs",
    "Verify API keys"
  ],
  "confidence_score": 0.85,
  "processing_time_ms": 3500
}
```

### Obtener un Incidente

```bash
curl http://localhost:8000/incident/{incident_id}
```

### Listar Incidentes

```bash
curl http://localhost:8000/incidents?limit=10
```

## 🧪 Uso Programático

```python
from agent import run_triage_agent, IncidentReport

# Crear reporte
report = IncidentReport(
    description="Users cannot log in to their accounts",
    source="soporte"
)

# Ejecutar agente
result = run_triage_agent(report)

# Acceder a resultados
print(f"Tipo: {result.incident_type}")
print(f"Severidad: {result.severity}")
print(f"Equipo: {result.assigned_team}")
print(f"Resumen: {result.summary}")
```

## 📊 Estructura del Pipeline

```
Input (IncidentReport)
    ↓
┌─────────────────────┐
│  1. Classify Node   │  → Clasifica tipo de incidente
└─────────────────────┘
    ↓
┌─────────────────────┐
│  2. Extract Node    │  → Extrae entidades técnicas
└─────────────────────┘
    ↓
┌─────────────────────┐
│  3. Summarize Node  │  → Genera resumen técnico
└─────────────────────┘
    ↓
┌─────────────────────┐
│  4. Route Node      │  → Asigna severidad y equipo
└─────────────────────┘
    ↓
Output (TriageResult)
```

## 🔍 Tipos de Incidentes Soportados

- `checkout_failure`: Problemas de pago o completar orden
- `login_error`: Problemas de autenticación
- `catalog_issue`: Problemas de catálogo/productos
- `cart_issue`: Problemas con el carrito
- `inventory_issue`: Problemas de inventario
- `shipping_issue`: Problemas de envío
- `performance_issue`: Problemas de rendimiento
- `unknown`: No se puede determinar

## 📁 Almacenamiento de Resultados

Los resultados se guardan automáticamente en:
```
data/incidents/{incident_id}.json
```

Cada archivo contiene el resultado completo del análisis.

## 🐛 Troubleshooting

### Error: "GEMINI_API_KEY not found"
- Verifica que el archivo `.env` existe
- Verifica que `GEMINI_API_KEY` está configurado
- Reinicia el servidor

### Error: "Rate limit exceeded"
- Gemini tiene límites de rate (15 requests/min en tier gratuito)
- Espera 1 minuto y reintenta
- Considera usar un API key de pago para mayor throughput

### Pipeline falla con errores
- Revisa los logs en consola (formato JSON)
- Cada nodo tiene manejo de errores y continúa el pipeline
- El campo `errors` en el estado contiene detalles

## 🚀 Próximos Pasos

1. **RAG Integration**: Indexar Reaction Commerce para contexto de código
2. **Multimodal**: Agregar análisis de imágenes y logs
3. **Observabilidad**: Integrar Langfuse para trazabilidad
4. **Integraciones**: GitHub Issues y Slack webhooks

## 📝 Logs

Los logs están en formato JSON estructurado:

```json
{
  "timestamp": "2026-04-08T12:00:00",
  "level": "info",
  "event": "classify_node_completed",
  "incident_type": "checkout_failure",
  "elapsed_ms": 1200
}
```

Para ver logs en tiempo real:
```bash
tail -f logs/agent.log
```

## 🎯 Métricas de Performance

El agente típicamente procesa un incidente en:
- **Classify**: ~1-2 segundos
- **Extract**: ~1-2 segundos
- **Summarize**: ~1-2 segundos
- **Route**: ~1-2 segundos
- **Total**: ~5-8 segundos

## 📞 Soporte

Para problemas o preguntas, revisa:
1. Logs del agente
2. Documentación de Gemini API
3. Issues del repositorio
