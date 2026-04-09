# Manual Testing Checklist — ScoutOps Agent Integration

**Deadline:** April 9, 9PM COT  
**Status:** All 13 implementation steps completed ✅

---

## 🚀 Quick Start: Run Everything Locally

### Prerequisites
- Python 3.10+ with venv activated
- Node.js 18+ (for frontend)
- `.env` file configured with:
  - `GEMINI_API_KEY=your_key`
  - `GITHUB_TOKEN=your_token`
  - `SLACK_WEBHOOK_URL=your_webhook` (optional, can be mocked)
  - `CHROMA_HOST=localhost` (if using local Chroma)

### Step 1: Start the backend
```bash
cd apps/backend
python -m uvicorn app.main:app --reload --port 8000
```
Expected: `Uvicorn running on http://127.0.0.1:8000`

### Step 2: Start the frontend (in another terminal)
```bash
cd apps/frontend
npm run dev
```
Expected: `▲ Next.js 14.2.3` running on `http://localhost:3000`

### Step 3: Start ChromaDB (in another terminal, if not using Docker)
```bash
chroma run --port 8001
```
Expected: `Chroma server running on http://localhost:8001`

---

## ✅ Test 1: RAG Integration (Retrieve Node)

### Manual Test
1. Open http://localhost:3000
2. Fill form:
   - **Description:** "Payment processing failing for Stripe integration"
   - **Source:** QA
   - **Email:** test@company.com
   - **Attachment:** (leave empty for now)
3. Click "Reportar Incidente"
4. Wait for agent to finish (should take 5-10 seconds)

### Expected Results
- ✅ **affected_file** is NOT `null` — should show a real file path from Reaction Commerce (e.g., `plugins/payments/stripe/resolver.ts`)
- ✅ **affected_plugin** is `api-plugin-payments-stripe` (not `unknown`)
- ✅ **summary** mentions specific code context from RAG (e.g., "Stripe resolver" or "payment handler")
- ✅ **processing_time_ms** includes time for RAG query (should be > 500ms)

### Verification in Browser DevTools
Open DevTools → Network tab → look for the GET `/api/incident/{incident_id}` response:
```json
{
  "result": {
    "affected_file": "plugins/payments/stripe/resolver.ts",  // ← NOT null
    "affected_plugin": "api-plugin-payments-stripe",
    "summary": "...[mentions Stripe or payment resolver]...",
    "confidence_score": 0.75
  }
}
```

### Backend Logs
Should see:
```
retrieve_node_started
retrieve_node_completed results_count=5 top_score=0.92
attachments_node_skipped reason=no_attachment
summarize_node_completed
route_node_completed
```

---

## ✅ Test 2: Multimodal Attachments (Attachments Node)

### Test 2a: Log File Analysis
1. Create a test log file `test.log`:
```
ERROR: Connection timeout at 2026-04-08T10:15:32Z
Stack trace: at PaymentProcessor.charge (resolver.ts:45)
Caused by: ECONNREFUSED 127.0.0.1:5432
```

2. In the form:
   - **Description:** "Database connection refused during payment"
   - **Source:** monitoring
   - **Email:** sre@company.com
   - **Attachment:** Upload `test.log`
3. Submit

### Expected Results
- ✅ **attachment_analysis** field is populated (not `null`)
- ✅ **summary** includes information from the log (e.g., "ECONNREFUSED", "database", "port 5432")
- ✅ **severity** is P1 or P2 (not P3, because database connection is critical)
- ✅ **suggested_actions** includes debugging steps like "Check database connectivity" or "Verify PostgreSQL service"

### Backend Logs
Should see:
```
attachments_node_started
attachments_node_completed attachment_type=log analysis_length=250
```

### Test 2b: Image Analysis (Optional, if you have a screenshot)
1. Take a screenshot of an error dialog (e.g., "500 Internal Server Error")
2. Upload as attachment with type `image`
3. Expected: Gemini Vision extracts the error code and status from the image

---

## ✅ Test 3: Confidence Scoring & Human-in-the-Loop

### Test 3a: High Confidence (Auto-Create Ticket)
1. Submit a **clear, specific incident:**
   - **Description:** "Stripe payment integration returning 401 Unauthorized for valid API keys"
   - **Source:** QA
2. Wait for completion

### Expected Results
- ✅ **confidence_score** is between 0.70–1.0 (e.g., 0.85)
- ✅ **status** is `completado` (not `escalado_humano`)
- ✅ GitHub issue is **automatically created** (check your repo)
- ✅ Slack notification sent with "Open Ticket" button (if webhook configured)

### Test 3b: Low Confidence (Human Escalation)
1. Submit a **vague, ambiguous incident:**
   - **Description:** "Something is broken"
   - **Source:** soporte
2. Wait for completion

### Expected Results
- ✅ **confidence_score** is < 0.70 (e.g., 0.45)
- ✅ **status** is `escalado_humano` (not `completado`)
- ✅ Frontend shows **amber warning banner:**
  ```
  ⚠️ Escalado — Revisión Humana Requerida
  El agente tiene una confianza de 45% (umbral: 70%).
  No se creó ticket automáticamente. El equipo de SRE ha sido notificado vía Slack para revisión manual.
  ```
- ✅ GitHub issue is **NOT created** (only Slack alert with `:warning: HUMAN REVIEW REQUIRED`)
- ✅ Slack notification shows confidence % and says "Manual triage required"

### Verification
Check the response JSON:
```json
{
  "status": "escalado_humano",
  "result": {
    "confidence_score": 0.45,
    "severity": "P3",
    "summary": "..."
  }
}
```

---

## ✅ Test 4: Reporter Email Flow

### Manual Test
1. Submit incident with **Email:** `your-email@company.com`
2. Check backend logs for:
   ```
   save_issue_reporter_mapping ticket_number=123 reporter_email=your-email@company.com
   ```
3. (Optional) Wait for issue to be closed on GitHub
4. Check your email for resolution notification

### Expected Results
- ✅ Email is stored in the incident mapping
- ✅ When issue is closed, `resolution_watcher` sends email to the reporter
- ✅ Email contains incident summary and resolution link

---

## ✅ Test 5: Agent State Fields

### Verify in Backend Logs
Run a test incident and check the Langfuse traces (if configured) or backend logs for:
```
rag_context: [
  {
    "plugin_name": "api-plugin-payments",
    "file_path": "...",
    "relevance_score": 0.92
  }
]
attachment_analysis: "Error codes: [ECONNREFUSED], Severity indicators: [timeout]"
escalated: false
```

### Verify in Code
```python
# agent/state.py should have:
class AgentState(TypedDict):
    rag_context: Optional[List[Dict[str, Any]]]
    attachment_analysis: Optional[str]
    escalated: bool
```

---

## 🧪 Automated Tests

### Run Unit + Integration Tests
```bash
pytest test_integration_e2e.py -v -s
```

Expected output:
```
test_retrieve_node_called_and_populates_rag_context PASSED
test_rag_context_enriches_summary PASSED
test_attachments_node_with_log_file PASSED
test_confidence_score_is_calculated PASSED
test_hybrid_confidence_combines_llm_and_rag PASSED
test_low_confidence_triggers_escalation PASSED
...
======================== 12 passed in 2.34s ========================
```

### Run Existing Tests
```bash
pytest test_agent.py -v -s
pytest test_rag.py -v -s
```

---

## 🔍 Debugging Checklist

If something doesn't work:

### RAG Not Working
- [ ] Check `rag/vector_store.py` — is Chroma collection initialized?
- [ ] Check `.env` — `CHROMA_HOST` set correctly?
- [ ] Check logs for `query_codebase failed`
- [ ] Verify `rag/ingest_repo.py` has been run to populate the vector DB

### Attachments Not Analyzed
- [ ] Check `data/uploads/` — is the file being saved?
- [ ] Check `attachment_type` is "image" or "log"
- [ ] Check `GEMINI_API_KEY` is valid (for Vision)
- [ ] Check logs for `attachments_node_failed`

### Confidence Always 0.85
- [ ] Verify `route.py` is asking LLM for `confidence_score` in schema
- [ ] Check `route_prompt.txt` has the confidence_score field description
- [ ] Verify hybrid calculation: `(llm_confidence * 0.6) + (rag_boost * 0.4)`

### Email Not Sent
- [ ] Check `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` in `.env`
- [ ] Check `resolution_watcher.py` is running (background task)
- [ ] Check logs for `notify_reporter` calls

### Frontend Not Showing Escalation Banner
- [ ] Check `page.tsx` has the `escalado_humano` condition
- [ ] Check API response includes `status: "escalado_humano"`
- [ ] Check browser console for errors

---

## 📊 Success Criteria

| Criterion | Evidence |
|-----------|----------|
| **RAG integrated** | `affected_file` is not null; summary mentions code context |
| **Multimodal working** | Log/image analysis appears in summary; `attachment_analysis` populated |
| **Confidence real** | `confidence_score` varies (0.45–0.95), not always 0.85 |
| **Human-in-the-loop** | Low confidence incidents show `escalado_humano` status + amber banner |
| **Email collected** | Form has email field; backend stores it |
| **E2E flow** | Form → Agent → GitHub/Slack/Email all work together |

---

## 🎯 Final Verification (5 minutes)

1. **Test RAG:** Submit "Payment Stripe failure" → check `affected_file` is not null ✅
2. **Test Multimodal:** Upload a log file → check `attachment_analysis` in response ✅
3. **Test Confidence:** Submit vague incident → check `status: escalado_humano` ✅
4. **Test Email:** Submit with email → check it's stored ✅
5. **Test E2E:** Complete flow from form to GitHub issue (if confidence ≥ 0.70) ✅

If all 5 pass, **implementation is complete and working!** 🚀

---

## 📝 Notes

- **Deadline:** April 9, 9PM COT (less than 24 hours)
- **All 13 steps completed:** ✅
- **New files created:** 3 (retrieve.py, attachments.py, attachments_prompt.txt)
- **Files modified:** 10 (state.py, graph.py, route.py, input_schema.py, llm_client.py, summarize.py, main.py, agent_service.py, ReportForm.tsx, page.tsx)
- **Test coverage:** Unit tests + integration tests + manual checklist
