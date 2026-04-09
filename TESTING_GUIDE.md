# Testing Guide — ScoutOps Agent Integration

**Última actualización:** April 8, 2026, 10:25 PM UTC-05:00  
**Deadline:** April 9, 2026, 9:00 PM COT (< 24 horas)

---

## 📋 Resumen de lo que se implementó

| Gap                                 | Solución                                                       | Verificación                            |
| ----------------------------------- | -------------------------------------------------------------- | --------------------------------------- |
| **RAG no estaba en el grafo**       | Nodo `retrieve.py` conecta `query_codebase()` al pipeline      | `affected_file` no es null              |
| **Sin análisis de adjuntos**        | Nodo `attachments.py` con Gemini Vision + análisis de logs     | `attachment_analysis` poblado           |
| **Confianza hardcodeada**           | Confianza híbrida: 60% LLM + 40% RAG relevancia                | `confidence_score` varía (0.45–0.95)    |
| **Sin Human-in-the-loop**           | Si `confidence < 0.70` → estado `escalado_humano`, skip ticket | Status `escalado_humano` + banner ámbar |
| **Email del reportero hardcodeado** | Campo email en formulario, guardado en backend                 | Email en form + usado en watcher        |

---

## 🧪 Opción 1: Test Rápido (5 minutos) — Sin Docker

### Paso 1: Activar venv

```bash
cd c:\Users\User\Desktop\Programacion\ScoutOps
.\venv\Scripts\activate
```

### Paso 2: Ejecutar test rápido

```bash
python quick_test.py
```

**Salida esperada:**

```
============================================================
ScoutOps Agent Integration — Quick Test Suite
============================================================

TEST 1: RAG Integration (Retrieve Node)
✓ Incident type: payment_failure
✓ Severity: P2
✓ Affected plugin: api-plugin-payments-stripe
✓ Affected file: plugins/payments/stripe/resolver.ts
✓ Summary: Stripe payment integration is failing...

✅ TEST 1 PASSED: RAG context populated affected_file

TEST 2: Confidence Scoring (Hybrid: 60% LLM + 40% RAG)
✓ LLM confidence: 0.75
✓ RAG relevance: 0.80
✓ Expected hybrid: 0.7400
✓ Actual confidence: 0.7400

✅ TEST 2 PASSED: Confidence is real (not hardcoded to 0.85)

TEST 3: Human-in-the-Loop (Escalation at < 0.70)
✓ Confidence score: 0.4500
✓ Threshold: 0.70
✓ Should escalate: True

✅ TEST 3 PASSED: Low confidence triggers escalation

TEST 4: AgentState Fields (rag_context, attachment_analysis, escalated)
✓ rag_context: [{'plugin_name': 'test', ...}]
✓ attachment_analysis: Error code: ECONNREFUSED
✓ escalated: False

✅ TEST 4 PASSED: All AgentState fields present

TEST 5: Reporter Email Field
✓ Reporter email: engineer@company.com

✅ TEST 5 PASSED: Reporter email collected

============================================================
SUMMARY
============================================================
✅ PASS: RAG Integration
✅ PASS: Confidence Scoring
✅ PASS: Escalation Threshold
✅ PASS: AgentState Fields
✅ PASS: Reporter Email

Total: 5/5 tests passed

🎉 All tests passed! Implementation is working correctly.
```

---

## 🧪 Opción 2: Test de Integración — Con pytest

### Paso 1: Instalar pytest (si no está)

```bash
pip install pytest pytest-asyncio
```

### Paso 2: Ejecutar tests

```bash
pytest test_integration_e2e.py -v -s
```

**Salida esperada:**

```
test_integration_e2e.py::TestRAGIntegration::test_retrieve_node_called_and_populates_rag_context PASSED
test_integration_e2e.py::TestRAGIntegration::test_rag_context_enriches_summary PASSED
test_integration_e2e.py::TestMultimodalAttachments::test_attachments_node_with_log_file PASSED
test_integration_e2e.py::TestMultimodalAttachments::test_attachments_node_skipped_when_no_attachment PASSED
test_integration_e2e.py::TestConfidenceAndHumanInTheLoop::test_confidence_score_is_calculated PASSED
test_integration_e2e.py::TestConfidenceAndHumanInTheLoop::test_hybrid_confidence_combines_llm_and_rag PASSED
test_integration_e2e.py::TestConfidenceAndHumanInTheLoop::test_low_confidence_triggers_escalation PASSED
test_integration_e2e.py::TestReporterEmailFlow::test_incident_report_accepts_reporter_email PASSED
test_integration_e2e.py::TestReporterEmailFlow::test_reporter_email_optional PASSED
test_integration_e2e.py::TestAgentStateFields::test_agent_state_has_rag_context PASSED
test_integration_e2e.py::TestAgentStateFields::test_agent_state_has_attachment_analysis PASSED
test_integration_e2e.py::TestAgentStateFields::test_agent_state_has_escalated_flag PASSED

======================== 12 passed in 2.34s ========================
```

---

## 🚀 Opción 3: Test End-to-End Completo (30 minutos) — Con Docker

### Paso 1: Levantar la stack completa

```bash
docker-compose up -d
```

Esperar a que todos los servicios estén healthy (2-3 minutos):

```bash
docker-compose ps
```

**Esperado:**

```
NAME                COMMAND                  STATUS
scoutops-frontend   "npm run dev"            Up (healthy)
scoutops-backend    "python -m uvicorn..."  Up (healthy)
scoutops-vector-db  "chroma run"             Up (healthy)
```

### Paso 2: Abrir el navegador

```
http://localhost:3000
```

### Paso 3: Ejecutar Test 1 — RAG Integration

**Formulario:**

- **Descripción:** "Payment processing failing for Stripe integration"
- **Fuente:** QA
- **Email:** test@company.com
- **Adjunto:** (dejar vacío)

**Click:** "Reportar Incidente"

**Verificación (en DevTools → Network):**

```json
{
  "result": {
    "affected_file": "plugins/payments/stripe/resolver.ts", // ← NOT null
    "affected_plugin": "api-plugin-payments-stripe",
    "confidence_score": 0.82,
    "summary": "Stripe payment integration is failing..."
  }
}
```

✅ **Si `affected_file` no es null → RAG funciona**

### Paso 4: Ejecutar Test 2 — Multimodal Attachments

**Crear archivo `test.log`:**

```
ERROR: Connection timeout at 2026-04-08T10:15:32Z
Stack trace: at PaymentProcessor.charge (resolver.ts:45)
Caused by: ECONNREFUSED 127.0.0.1:5432
```

**Formulario:**

- **Descripción:** "Database connection refused during payment"
- **Fuente:** monitoring
- **Email:** sre@company.com
- **Adjunto:** Upload `test.log`

**Click:** "Reportar Incidente"

**Verificación:**

- Backend logs debe mostrar: `attachments_node_completed attachment_type=log`
- Response debe incluir `attachment_analysis` con info del log
- Summary debe mencionar "ECONNREFUSED" o "database"

✅ **Si `attachment_analysis` está poblado → Multimodal funciona**

### Paso 5: Ejecutar Test 3 — Confidence & Escalation

**Test 3a: Alta confianza (auto-crear ticket)**

- **Descripción:** "Stripe payment integration returning 401 Unauthorized for valid API keys"
- **Fuente:** QA
- **Email:** engineer@company.com

**Esperado:**

- `status: "completado"` (NO `escalado_humano`)
- `confidence_score: 0.75+`
- GitHub issue creado automáticamente

✅ **Si status es `completado` → Confianza alta funciona**

**Test 3b: Baja confianza (escalación)**

- **Descripción:** "Something is broken"
- **Fuente:** soporte
- **Email:** support@company.com

**Esperado:**

- `status: "escalado_humano"`
- `confidence_score: < 0.70`
- **Banner ámbar en la UI:**
  ```
  ⚠️ Escalado — Revisión Humana Requerida
  El agente tiene una confianza de 45% (umbral: 70%).
  No se creó ticket automáticamente.
  ```
- GitHub issue **NO** creado
- Slack alert con `:warning: HUMAN REVIEW REQUIRED`

✅ **Si status es `escalado_humano` + banner ámbar → Human-in-the-loop funciona**

### Paso 6: Verificar Email (Opcional)

Si SMTP está configurado:

1. Esperar a que el issue se cierre en GitHub
2. Revisar email en `engineer@company.com`
3. Debe contener: incident summary + link a GitHub issue

✅ **Si email llega → Reporter email funciona**

---

## 🔍 Debugging: Qué hacer si algo falla

### RAG no funciona (`affected_file` es null)

```bash
# Verificar que Chroma está corriendo
curl http://localhost:8001/api/v1/heartbeat

# Verificar que el vector DB tiene datos
docker exec scoutops-vector-db ls /chroma/chroma/

# Ver logs del backend
docker logs scoutops-backend | grep -i "retrieve\|rag"
```

### Attachments no se analizan

```bash
# Verificar que el archivo se guardó
ls -la data/uploads/

# Ver logs
docker logs scoutops-backend | grep -i "attachments"

# Verificar GEMINI_API_KEY en .env
grep GEMINI_API_KEY .env
```

### Confianza siempre 0.85

```bash
# Verificar que route_prompt.txt tiene confidence_score
grep -A5 "confidence_score" agent/prompts/route_prompt.txt

# Ver logs de route node
docker logs scoutops-backend | grep -i "route_node"
```

### Email no se envía

```bash
# Verificar SMTP config
grep SMTP .env

# Ver logs del watcher
docker logs scoutops-backend | grep -i "resolution_watcher\|notify_reporter"
```

---

## 📊 Checklist Final

- [ ] **Test 1 (RAG):** `affected_file` no es null
- [ ] **Test 2 (Multimodal):** `attachment_analysis` poblado con info del log/imagen
- [ ] **Test 3a (Confianza alta):** Status `completado`, GitHub issue creado
- [ ] **Test 3b (Escalación):** Status `escalado_humano`, banner ámbar, sin GitHub issue
- [ ] **Test 4 (Email):** Email del reportero guardado y usado
- [ ] **Test 5 (AgentState):** Campos `rag_context`, `attachment_analysis`, `escalated` presentes

**Si todos los checks pasan → ¡Implementación lista para el hackathon!** 🎉

---

## 📝 Archivos de Test

| Archivo                    | Propósito                                | Comando                                |
| -------------------------- | ---------------------------------------- | -------------------------------------- |
| `quick_test.py`            | Test rápido sin Docker (5 min)           | `python quick_test.py`                 |
| `test_integration_e2e.py`  | Tests de integración con pytest (10 min) | `pytest test_integration_e2e.py -v -s` |
| `test_manual_checklist.md` | Guía manual paso a paso (30 min)         | Leer + ejecutar manualmente            |
| `TESTING_GUIDE.md`         | Este archivo                             | Referencia                             |

---

## ⏰ Timeline Recomendado

| Tiempo                | Actividad                                     |
| --------------------- | --------------------------------------------- |
| 5 min                 | Ejecutar `quick_test.py`                      |
| 10 min                | Ejecutar `pytest test_integration_e2e.py`     |
| 15 min                | Levantar Docker y hacer Test 1-2 en navegador |
| 10 min                | Hacer Test 3a-3b (confianza + escalación)     |
| 5 min                 | Verificar logs y debugging si es necesario    |
| **Total: 45 minutos** | Validación completa                           |

---

## 🎯 Criterios de Éxito

✅ **RAG:** `affected_file` ≠ null  
✅ **Multimodal:** `attachment_analysis` poblado  
✅ **Confianza:** Varía (0.45–0.95), no siempre 0.85  
✅ **Escalación:** Status `escalado_humano` cuando confidence < 0.70  
✅ **Email:** Campo en formulario + guardado en backend  
✅ **E2E:** Flujo completo form → agent → GitHub/Slack/Email

Si todos pasan → **¡Implementación completada exitosamente!** 🚀
