# Prompts de Prueba para ScoutOps SRE Agent

## 1. Inputs Vagos (Vague Input Filter)
Estos prompts deben ser detectados como vagos (classification_confidence < 0.35) y escalados sin crear ticket.

### 1.1 Completamente Vago
```
hola
```

### 1.2 Spam/Ruido
```
asdfghjkl qwerty zxcvbnm random text without meaning
```

### 1.3 Pregunta General (No Incidente)
```
¿Cuál es el mejor lenguaje de programación?
```

### 1.4 Muy Corto
```
error
```

### 1.5 Off-Topic
```
Me gustaría saber cómo hacer un pastel de chocolate
```

---

## 2. Inputs Válidos (Deduplication Test)
Estos prompts deben crear tickets o deduplicarse.

### 2.1 Checkout Failure (Nuevo)
```
Los usuarios no pueden completar el checkout. El carrito muestra error 500 cuando intentan procesar el pago. El equipo de pagos reporta que el servicio de Stripe está respondiendo lentamente. Afecta aproximadamente al 15% de los usuarios en la región de Latinoamérica. El error comenzó hace 30 minutos.
```

### 2.2 Login Error (Nuevo)
```
Reportamos un problema crítico en el servicio de autenticación. Los usuarios no pueden iniciar sesión con sus credenciales válidas. El error aparece en el endpoint /api/auth/login y retorna HTTP 401 incluso con credenciales correctas. El problema comenzó después del último deploy a las 14:30 UTC. Afecta a todos los usuarios.
```

### 2.3 Catalog Issue (Nuevo)
```
El catálogo de productos está mostrando datos inconsistentes. Algunos productos aparecen con precios duplicados y otros no aparecen en absoluto. El problema parece estar en la base de datos de catálogo. Los usuarios reportan que no pueden buscar productos correctamente.
```

### 2.4 Inventory Issue (Nuevo)
```
El sistema de inventario está reportando cantidades incorrectas. Tenemos 50 unidades del producto SKU-12345 pero el sistema muestra 0. Esto está causando que se rechacen órdenes válidas. El problema afecta a 10 SKUs diferentes.
```

### 2.5 Shipping Issue (Nuevo)
```
El servicio de envíos está caído. Los usuarios no pueden ver el estado de sus envíos y no se están generando etiquetas de envío. El error en los logs muestra "Connection timeout to shipping provider". Afecta a todos los pedidos creados en las últimas 2 horas.
```

### 2.6 Performance Issue (Nuevo)
```
El sitio web está muy lento. Los tiempos de respuesta del API han aumentado de 200ms a 2000ms. El CPU del servidor está al 95% y la memoria al 88%. Comenzó después del pico de tráfico de las 18:00 UTC.
```

### 2.7 Checkout Failure (Duplicado - Debería Deduplicarse)
```
Problema urgente: Los clientes no pueden completar sus compras. El carrito falla al procesar pagos. El error ocurre en la integración con Stripe. Afecta a muchos usuarios en Latinoamérica.
```

### 2.8 Login Error (Duplicado - Debería Deduplicarse)
```
Incidente crítico: El login no funciona. Los usuarios válidos no pueden acceder a la plataforma. El servicio de autenticación está fallando. Comenzó hace poco.
```

---

## 3. Casos Límite

### 3.1 Muy Corto pero Válido
```
El checkout falla con error 500 en pagos
```

### 3.2 Muy Largo pero Válido
```
Reportamos un problema crítico en el servicio de checkout que está afectando significativamente a nuestros usuarios. El problema comenzó hace aproximadamente 45 minutos cuando implementamos una actualización en el servicio de procesamiento de pagos. Los usuarios están recibiendo errores HTTP 500 cuando intentan completar sus compras. El equipo de pagos ha confirmado que la integración con Stripe está respondiendo correctamente, pero nuestro servicio intermedio está fallando. Los logs muestran que hay un timeout en la conexión a la base de datos de transacciones. Hemos identificado que la consulta de validación de tarjeta está tardando más de 30 segundos. El problema afecta aproximadamente al 25% de los intentos de checkout. La región más afectada es Latinoamérica pero también hay reportes de Europa. Necesitamos escalar esto inmediatamente.
```

### 3.3 Parcialmente Vago
```
Hay un problema con algo. No estoy seguro qué es exactamente pero algo no funciona bien.
```

---

## 4. Cómo Probar

### Opción A: Interfaz Web
1. Abre http://localhost:3000
2. Copia uno de los prompts arriba
3. Pega en el formulario
4. Observa:
   - **Inputs Vagos**: Debe mostrar "Descripción no reconocida" en rojo
   - **Inputs Válidos**: Debe mostrar el resultado del análisis
   - **Duplicados**: Debe mostrar que se agregó comentario a issue existente

### Opción B: cURL (API Directa)
```bash
# Test vago
curl -X POST http://localhost:8000/incident \
  -F "description=hola" \
  -F "source=QA" \
  -F "reporter_email=test@example.com"

# Test válido
curl -X POST http://localhost:8000/incident \
  -F "description=Los usuarios no pueden completar el checkout. El carrito muestra error 500 cuando intentan procesar el pago." \
  -F "source=QA" \
  -F "reporter_email=test@example.com"

# Luego polling
curl http://localhost:8000/incident/{incident_id}
```

### Opción C: Validación Rápida
```bash
curl -X POST http://localhost:8000/validate-input \
  -H "Content-Type: application/json" \
  -d '{"description":"hola","source":"QA"}'
```

---

## 5. Resultados Esperados

### Vague Input (classification_confidence < 0.35)
```json
{
  "status": "escalado_humano",
  "result": {
    "confidence_score": 0.0,
    "incident_type": "unknown"
  }
}
```

### Valid Input (confidence_score >= 0.70)
```json
{
  "status": "completado",
  "result": {
    "confidence_score": 0.75,
    "incident_type": "checkout_failure",
    "severity": "P1",
    "ticket": {
      "ticket_id": "123",
      "status": "open"
    }
  }
}
```

### Duplicated Input
```json
{
  "status": "completado",
  "result": {
    "confidence_score": 0.80,
    "incident_type": "checkout_failure"
  },
  "ticket": {
    "ticket_id": "123",
    "status": "open",
    "resolution_notes": "Deduplicated into existing issue #123: ..."
  }
}
```

---

## 6. Debugging

Si la interfaz no devuelve nada:

1. **Revisa los logs del backend**:
   ```bash
   docker logs scoutops-backend-1 -f
   ```

2. **Revisa la consola del navegador** (F12):
   - Abre DevTools
   - Ve a Network tab
   - Busca el request POST a `/api/incident`
   - Revisa la respuesta

3. **Revisa si el backend está corriendo**:
   ```bash
   curl http://localhost:8000/health
   ```

4. **Revisa si hay errores en el incident**:
   ```bash
   curl http://localhost:8000/incident/{incident_id}
   ```

---

## 7. Problemas Comunes

### "La interfaz solo carga un momento y no devuelve nada"

**Causa 1: El backend está tardando mucho**
- Los nodos del agente (classify, extract, retrieve, etc.) pueden tardar 30-60 segundos
- La interfaz está esperando polling cada 2 segundos
- Revisa los logs del backend para ver dónde se está tardando

**Causa 2: Error silencioso en el backend**
- El incident se crea pero luego falla en `process_incident_async`
- Revisa `data/incidents/{incident_id}.json` para ver el estado
- Busca "error" en los logs del backend

**Causa 3: Problema de CORS**
- Revisa la consola del navegador para errores de CORS
- El backend tiene `allow_origins=["*"]` así que debería funcionar

**Causa 4: El endpoint `/incident/{incident_id}` no existe**
- Asegúrate que el incident_id sea válido
- Revisa que el archivo exista en `data/incidents/`

### "Los inputs vagos no se detectan"

1. Revisa que `classification_confidence < 0.35` en el nodo classify
2. Revisa que el nodo route tenga la lógica de `vague_input`
3. Revisa los logs: busca "vague_input_detected"

### "Los duplicados no se deduplicación"

1. Revisa que `search_similar_issues()` esté funcionando
2. Revisa que el GitHub token sea válido
3. Revisa que los issues tengan el label `sre-agent`
4. Revisa los logs: busca "search_similar_issues"
