# 🚀 Próximos Pasos - SRE Agent

## ✅ Implementación Completada

La implementación del agente SRE está **100% completa**. Todos los archivos y código necesarios han sido creados.

## 📋 Pasos para Ejecutar

### 1. Instalar Dependencias

```bash
pip install -r requirements.txt
```

Esto instalará:
- `langgraph` - Orquestación del pipeline
- `langchain` - Utilidades para LLMs
- `google-genai` - SDK de Gemini
- `pydantic` - Validación de datos
- `fastapi` - Backend API
- `structlog` - Logging estructurado
- Y otras dependencias necesarias

### 2. Configurar Variables de Entorno

```bash
# Copiar el archivo de ejemplo
cp .env.example .env
```

Editar `.env` y agregar tu API key de Gemini:

```env
GEMINI_API_KEY=tu_api_key_aqui
MODEL_NAME=gemini-2.5-flash
TEMPERATURE=0.3
MAX_OUTPUT_TOKENS=2048
LOG_LEVEL=INFO
INCIDENTS_DATA_DIR=./data/incidents
```

**Obtener API Key de Gemini (GRATIS):**
1. Visita: https://aistudio.google.com/app/apikey
2. Inicia sesión con tu cuenta de Google
3. Clic en "Create API Key"
4. Copia el API key
5. Pégalo en `.env`

### 3. Validar Setup

```bash
python validate_setup.py
```

Este script verificará que todo esté configurado correctamente.

### 4. Probar el Agente

#### Opción A: Ejemplo Simple

```bash
python example_usage.py
```

Este script ejecuta un ejemplo simple de triage de incidente.

#### Opción B: Suite de Tests Completa

```bash
python test_agent.py
```

Este script ejecuta 3 casos de prueba:
- ✅ Checkout failure (error de pago)
- ✅ Login error (error de autenticación)  
- ✅ Catalog issue (problema de catálogo)

Los resultados se guardarán en `test_results.json`.

### 5. Iniciar el Backend API

```bash
python start_backend.py
```

O alternativamente:

```bash
cd apps/backend
uvicorn app.main:app --reload --port 8000
```

La API estará disponible en:
- **API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 6. Probar la API

```bash
# Crear un incidente
curl -X POST http://localhost:8000/incident \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Users getting 500 error when trying to pay with credit card",
    "source": "QA"
  }'

# Listar incidentes
curl http://localhost:8000/incidents

# Obtener un incidente específico
curl http://localhost:8000/incident/{incident_id}
```

## 🎯 Verificación de Funcionamiento

Después de ejecutar los tests, deberías ver:

1. **Logs estructurados** en formato JSON
2. **Resultados guardados** en `data/incidents/`
3. **Output estructurado** con:
   - Tipo de incidente clasificado
   - Severidad asignada (P1/P2/P3)
   - Plugin afectado
   - Equipo asignado
   - Resumen técnico
   - Acciones sugeridas
   - Tiempo de procesamiento

## 📊 Ejemplo de Output Esperado

```json
{
  "incident_id": "abc-123-def",
  "incident_type": "checkout_failure",
  "severity": "P1",
  "affected_plugin": "api-plugin-payments-stripe",
  "layer": "GraphQL resolver",
  "assigned_team": "payments-team",
  "summary": "Users cannot complete checkout due to Stripe payment timeout. The placeOrder resolver fails to handle Stripe API timeouts gracefully.",
  "suggested_actions": [
    "Check Stripe API status at status.stripe.com",
    "Inspect resolver logs in api-plugin-payments-stripe/resolvers/",
    "Verify STRIPE_SECRET_KEY env variable in production"
  ],
  "confidence_score": 0.85,
  "processing_time_ms": 3500
}
```

## 🔍 Troubleshooting

### Error: "No module named 'langgraph'"
**Solución**: Ejecuta `pip install -r requirements.txt`

### Error: "GEMINI_API_KEY not found"
**Solución**: 
1. Verifica que `.env` existe
2. Verifica que `GEMINI_API_KEY` está configurado
3. No uses comillas en el valor del API key

### Error: "Rate limit exceeded"
**Solución**: 
- Gemini tiene límite de 15 requests/min en tier gratuito
- Espera 1 minuto y reintenta
- Los tests ejecutan 3 requests, deberían funcionar sin problema

### Pipeline falla con errores
**Solución**:
- Revisa los logs en consola (formato JSON)
- Cada nodo tiene manejo de errores
- El campo `errors` en el resultado contiene detalles

## 📚 Documentación Adicional

- **[README.md](README.md)**: Overview del proyecto
- **[AGENT_SETUP.md](AGENT_SETUP.md)**: Guía completa de setup y uso
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)**: Resumen de implementación
- **[SRE_Agent_Team_Briefing.md](SRE_Agent_Team_Briefing.md)**: Briefing técnico original

## 🎨 Uso Programático

```python
from agent import run_triage_agent, IncidentReport

# Crear reporte
report = IncidentReport(
    description="Users cannot log in to their accounts",
    source="soporte"
)

# Ejecutar agente
result = run_triage_agent(report)

# Usar resultados
print(f"Tipo: {result.incident_type}")
print(f"Severidad: {result.severity}")
print(f"Equipo: {result.assigned_team}")
```

## 🚀 Iteraciones Futuras

Una vez que el agente básico funcione, puedes expandirlo con:

### Fase 2: RAG Integration
1. Clonar Reaction Commerce
2. Indexar en Chroma
3. Agregar nodo de RAG query
4. Enriquecer resumen con código real

### Fase 3: Multimodal
1. Agregar análisis de imágenes
2. Procesar logs adjuntos
3. Extraer información de screenshots

### Fase 4: Integraciones
1. GitHub Issues API
2. Slack webhooks
3. Resolution watcher

### Fase 5: Observabilidad
1. Integrar Langfuse
2. Dashboard de métricas
3. Alertas

## ✅ Checklist de Inicio

- [ ] Instalar dependencias (`pip install -r requirements.txt`)
- [ ] Crear archivo `.env` desde `.env.example`
- [ ] Configurar `GEMINI_API_KEY` en `.env`
- [ ] Ejecutar `python validate_setup.py`
- [ ] Ejecutar `python example_usage.py`
- [ ] Ejecutar `python test_agent.py`
- [ ] Iniciar backend con `python start_backend.py`
- [ ] Probar API en http://localhost:8000/docs

## 🎉 ¡Listo para Usar!

Una vez completados estos pasos, tendrás un agente SRE completamente funcional que puede:
- Clasificar incidentes automáticamente
- Extraer información técnica
- Generar resúmenes accionables
- Asignar severidad y equipos
- Guardar resultados estructurados
- Exponer API REST para integración

**Tiempo estimado de setup**: 5-10 minutos

**¡Buena suerte con el hackathon! 🚀**
