"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import ReportForm from "@/components/ReportForm";
import ResultView from "@/components/ResultView";
import TicketStatus from "@/components/TicketStatus";
import VoiceInput from "@/components/VoiceInput";

export default function Home() {
  const [incidentId, setIncidentId] = useState<string | null>(null);
  const [incidentData, setIncidentData] = useState<any>(null);
  const [isPolling, setIsPolling] = useState(false);
  const [isCreatingTicket, setIsCreatingTicket] = useState(false);

  useEffect(() => {
    let intervalId: NodeJS.Timeout;

    const pollIncident = async () => {
      try {
        const res = await fetch(`/api/incident/${incidentId}`);
        if (!res.ok) throw new Error("Error polling incident");
        
        const data = await res.json();
        setIncidentData(data);

        if (data.status === "completado" || data.status === "escalado_humano" || data.status === "error") {
          setIsPolling(false);
          clearInterval(intervalId);

          // Si se completó y no tiene ticket, creamos el ticket en Github
          if (data.status === "completado" && !data.ticket) {
            createGithubIssue(data);
          }
        }
      } catch (error) {
        console.error("Polling check failed:", error);
      }
    };

    if (isPolling && incidentId) {
      intervalId = setInterval(pollIncident, 2000);
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [isPolling, incidentId]);

  const createGithubIssue = async (data: any) => {
    setIsCreatingTicket(true);
    try {
      const result = data.result;
      const title = `[${result.severity}] ${result.incident_type} — ${result.affected_plugin || 'General'}`;
      const actionsBlock = result.suggested_actions?.length
        ? result.suggested_actions.map((a: string) => `- ${a}`).join('\n')
        : '- No suggestions provided';
      const body = [
        '## Incident Triage Report',
        '',
        `- **Incident Type:** ${result.incident_type || 'unknown'}`,
        `- **Severity:** ${result.severity || 'unknown'}`,
        `- **Affected Plugin:** ${result.affected_plugin || 'unknown'}`,
        `- **Layer:** ${result.layer || 'unknown'}`,
        `- **Assigned Team:** ${result.assigned_team || 'unknown'}`,
        `- **Reporter Email:** ${data.reporter_email || 'unknown'}`,
        '',
        '### Summary',
        result.summary || '',
        '',
        '### Suggested Actions',
        actionsBlock,
        '',
        '### Original Description',
        data.description || '',
      ].join('\n');

      const res = await fetch('/api/github', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, body, incident_id: data.incident_id })
      });

      if (!res.ok) throw new Error("Failed to create github issue");
      
      const issueData = await res.json();
      
      // Actualizamos la vista localmente
      setIncidentData((prev: any) => ({
        ...prev,
        ticket: {
          ticket_id: issueData.html_url,
          status: 'open'
        }
      }));
    } catch (error) {
      console.error("Error creating github issue:", error);
    } finally {
      setIsCreatingTicket(false);
    }
  };

  const handleIncidentCreated = (id: string) => {
    setIncidentId(id);
    setIsPolling(true);
    setIncidentData(null);
  };

  return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-slate-50 p-6 md:p-12">
      <div className="max-w-4xl mx-auto space-y-8">
        <header className="mb-10 text-center">
          <div className="flex justify-end mb-3">
            <Link
              href="/wrapped"
              className="mr-2 inline-flex items-center rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500"
            >
              Wrapped
            </Link>
            <Link
              href="/history"
              className="inline-flex items-center rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 dark:bg-slate-700 dark:hover:bg-slate-600"
            >
              Dashboard
            </Link>
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent mb-2">
            ScoutOps SRE Agent
          </h1>
          <p className="text-slate-500 dark:text-slate-400 text-lg">
            Plataforma Inteligente de Triage de Incidentes
          </p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          <div className="lg:col-span-5 flex flex-col gap-6">
            <ReportForm onIncidentCreated={handleIncidentCreated} isProcessing={isPolling} />

            {/* Voice channel */}
            <div className="bg-white dark:bg-slate-800 rounded-xl shadow-lg p-6 flex flex-col items-center gap-3">
              <div className="flex items-center gap-2 self-start">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wide">
                  Asistente de Voz
                </h2>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 text-center">
                Describe el incidente en voz — en español o inglés
              </p>
              <VoiceInput
                onIncidentCreated={handleIncidentCreated}
                onIncidentResult={(data) => {
                  if (data) setIncidentData(data);
                }}
              />
            </div>
          </div>

          <div className="lg:col-span-7">
            {incidentId && !incidentData?.result && isPolling && (
              <div className="bg-white dark:bg-slate-800 p-8 rounded-xl shadow-lg border border-slate-100 dark:border-slate-700 h-full flex flex-col items-center justify-center min-h-[300px]">
                <div className="relative">
                  <div className="w-16 h-16 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
                  <div className="w-16 h-16 border-4 border-transparent border-b-indigo-400 rounded-full animate-pulse absolute inset-0"></div>
                </div>
                <h3 className="mt-6 text-xl font-semibold text-slate-700 dark:text-slate-200">El Agente está analizando...</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-2">Extrayendo entidades y determinando severidad</p>
              </div>
            )}

            {incidentData?.status === "escalado_humano" && incidentData?.result && (() => {
              const isVague = (incidentData.result.confidence_score ?? 0) === 0;
              return (
                <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 space-y-4">
                  <div className={`border rounded-xl p-6 ${isVague ? "bg-red-50 dark:bg-red-900/20 border-red-300 dark:border-red-700" : "bg-amber-50 dark:bg-amber-900/20 border-amber-300 dark:border-amber-700"}`}>
                    <div className="flex items-start space-x-3">
                      <svg className={`w-7 h-7 flex-shrink-0 mt-0.5 ${isVague ? "text-red-500" : "text-amber-500"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
                      </svg>
                      <div>
                        {isVague ? (
                          <>
                            <h3 className="text-lg font-bold text-red-800 dark:text-red-300">Descripción no reconocida</h3>
                            <p className="text-sm text-red-700 dark:text-red-400 mt-1">
                              El agente no pudo identificar un incidente válido en esta descripción. No se creó ticket ni se envió notificación. Por favor, describe un problema técnico específico.
                            </p>
                          </>
                        ) : (
                          <>
                            <h3 className="text-lg font-bold text-amber-800 dark:text-amber-300">Escalado — Revisión Humana Requerida</h3>
                            <p className="text-sm text-amber-700 dark:text-amber-400 mt-1">
                              El agente tiene una confianza de <strong>{((incidentData.result.confidence_score || 0) * 100).toFixed(0)}%</strong> (umbral: 70%).
                              No se creó ticket automáticamente. El equipo de SRE ha sido notificado vía Slack para revisión manual.
                            </p>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                  <ResultView result={incidentData.result} />
                </div>
              );
            })()}

            {incidentData?.result && incidentData?.status !== "escalado_humano" && (
              <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
                <ResultView result={incidentData.result} />
                <TicketStatus 
                  ticket={incidentData.ticket} 
                  incidentId={incidentData.incident_id} 
                  onCreating={isCreatingTicket} 
                />
              </div>
            )}

            {!incidentId && (
              <div className="bg-slate-100 dark:bg-slate-800/50 p-8 rounded-xl border border-dashed border-slate-300 dark:border-slate-700 h-full flex flex-col items-center justify-center text-center min-h-[300px]">
                <svg className="w-16 h-16 text-slate-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <h3 className="text-lg font-medium text-slate-600 dark:text-slate-300">Esperando reporte</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 max-w-sm">
                  Llena el formulario a la izquierda para iniciar el análisis automático del incidente.
                </p>
              </div>
            )}

            {incidentData?.status === "error" && (
              <div className="bg-red-50 dark:bg-red-900/20 p-6 rounded-xl border border-red-200 dark:border-red-800 text-center">
                <svg className="w-12 h-12 text-red-500 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <h3 className="text-lg font-bold text-red-800 dark:text-red-400">Error durante el análisis</h3>
                <p className="text-sm text-red-600 dark:text-red-300 mt-1">{incidentData.error || "Algo salió mal"}</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
