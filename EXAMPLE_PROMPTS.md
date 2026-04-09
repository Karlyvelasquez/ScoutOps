# Ejemplos de Prompts para Probar el Agente

Estos ejemplos están diseñados para probar el agente después de los fixes de confidence. Cada uno debería retornar `confidence_score >= 0.75`.

---

## 1. Checkout Failure (Claro - P1)

```json
{
  "source": "QA",
  "description": "Users are getting 'Payment declined' errors when trying to complete checkout with Stripe. The error appears after clicking 'Pay Now' button. This started happening 30 minutes ago. Multiple users reporting in #incidents channel. Transaction logs show Stripe API returning 402 status code.",
  "reporter_email": "ops@company.com"
}
```

**Esperado:**
- `incident_type`: checkout_failure
- `severity`: P1
- `affected_plugin`: api-plugin-payments-stripe
- `assigned_team`: payments-team
- `confidence_score`: 0.85+ ✅

---

## 2. Login Error (Claro - P2)

```json
{
  "source": "soporte",
  "description": "Customers unable to login. Getting 'Invalid credentials' error even with correct password. Session tokens not being generated. Issue started after deployment at 2:15 AM. Affects all users, not just specific accounts.",
  "reporter_email": "support@company.com"
}
```

**Esperado:**
- `incident_type`: login_error
- `severity`: P2
- `affected_plugin`: api-plugin-accounts
- `assigned_team`: accounts-team
- `confidence_score`: 0.82+ ✅

---

## 3. Catalog Issue (Claro - P2)

```json
{
  "source": "QA",
  "description": "Product search is returning no results for any query. The search endpoint is responding with 500 errors. Product listing page works fine but search feature is completely broken. This is blocking customer ability to find products.",
  "reporter_email": "dev@company.com"
}
```

**Esperado:**
- `incident_type`: catalog_issue
- `severity`: P2
- `affected_plugin`: api-plugin-catalog
- `assigned_team`: catalog-team
- `confidence_score`: 0.80+ ✅

---

## 4. Cart Issue (Claro - P2)

```json
{
  "source": "QA",
  "description": "Items not persisting in shopping cart. When users add products to cart and refresh the page, items disappear. Cart API endpoint /graphql returning null for cart query. Database queries show items are being inserted but not retrieved.",
  "reporter_email": "ops@company.com"
}
```

**Esperado:**
- `incident_type`: cart_issue
- `severity`: P2
- `affected_plugin`: api-plugin-carts
- `assigned_team`: catalog-team
- `confidence_score`: 0.81+ ✅

---

## 5. Inventory Issue (Moderado - P3)

```json
{
  "source": "soporte",
  "description": "Stock levels not updating correctly. When orders are placed, inventory counts are not decreasing. Backorder system is not triggering notifications. This is causing overselling of out-of-stock items.",
  "reporter_email": "inventory@company.com"
}
```

**Esperado:**
- `incident_type`: inventory_issue
- `severity`: P3
- `affected_plugin`: api-plugin-inventory
- `assigned_team`: catalog-team
- `confidence_score`: 0.78+ ✅

---

## 6. Shipping Issue (Moderado - P3)

```json
{
  "source": "soporte",
  "description": "Shipping rate calculation is broken. Customers see incorrect shipping costs at checkout. Some regions showing $0 shipping, others showing $999. The shipping provider integration with FedEx API seems to be failing silently.",
  "reporter_email": "fulfillment@company.com"
}
```

**Esperado:**
- `incident_type`: shipping_issue
- `severity`: P3
- `affected_plugin`: api-plugin-shipments
- `assigned_team`: orders-team
- `confidence_score`: 0.77+ ✅

---

## 7. Performance Issue (Claro - P2)

```json
{
  "source": "monitoring",
  "description": "API response times degraded significantly. GraphQL queries taking 5-10 seconds instead of normal 200-500ms. Database queries are slow. CPU usage at 95%. This is affecting all endpoints across the platform.",
  "reporter_email": "sre@company.com"
}
```

**Esperado:**
- `incident_type`: performance_issue
- `severity`: P2
- `affected_plugin`: api-plugin-unknown (o el que RAG encuentre)
- `assigned_team`: platform-team
- `confidence_score`: 0.75+ ✅

---

## 8. Ambiguo (Debería ser más bajo - P3)

```json
{
  "source": "soporte",
  "description": "Something is broken. Users are complaining. Not sure what the issue is exactly.",
  "reporter_email": "unknown@company.com"
}
```

**Esperado:**
- `incident_type`: unknown
- `severity`: P3
- `affected_plugin`: unknown
- `assigned_team`: platform-team
- `confidence_score`: 0.45-0.60 ⚠️ (bajo, como debe ser)

---

## Cómo Probar

### Opción 1: Usando `quick_test.py` (sin Docker)

```bash
python quick_test.py
```

### Opción 2: Usando pytest

```bash
pytest test_integration_e2e.py -v -s
```

### Opción 3: Manualmente con curl

```bash
curl -X POST http://localhost:8000/api/triage \
  -H "Content-Type: application/json" \
  -d '{
    "source": "slack",
    "description": "Users are getting Payment declined errors when trying to complete checkout with Stripe...",
    "reporter_email": "ops@company.com"
  }'
```

### Opción 4: Desde el frontend

1. Abre `http://localhost:3000`
2. Llena el formulario con uno de los ejemplos arriba
3. Envía el reporte
4. Verifica que `confidence_score` sea >= 0.75 ✅

---

## Cambios Implementados

Los siguientes fixes mejoraron la confidence:

1. **route.py**: Fórmula híbrida corregida
   - Antes: `hybrid = llm × 0.6 + rag × 0.4` (siempre < 0.70)
   - Ahora: Sin RAG usa LLM directo; con RAG usa 70/30 blend

2. **route_prompt.txt**: Recalibración de escala
   - El prompt ahora instruye al LLM que incidentes claros deben tener >= 0.80
   - Solo baja de 0.70 ante ambigüedad genuina

3. **queries.py**: Fórmula de relevancia RAG corregida
   - Antes: `1 / (1 + d)` (subestimaba matches buenos)
   - Ahora: `1 - d²/2` (similitud coseno correcta para embeddings normalizados)

---

## Checklist de Validación

- [ ] Ejecuta `quick_test.py` y verifica que todos los tests pasen
- [ ] Prueba los 7 ejemplos claros arriba y verifica confidence >= 0.75
- [ ] Prueba el ejemplo ambiguo y verifica que confidence sea bajo (0.45-0.60)
- [ ] Verifica que los `escalated` sean False para ejemplos claros
- [ ] Verifica que los `escalated` sean True solo para ambiguos o con errores
