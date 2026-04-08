"use client";

import { useState, useEffect } from "react";
import ReportForm from "@/components/ReportForm";
import ResultView from "@/components/ResultView";
import TicketStatus from "@/components/TicketStatus";

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

        if (data.status === "completado" || data.status === "error") {
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
      const title = `[${result.severity}] ${result.incident_type}: ${result.affected_plugin || 'General'}`;
      const body = `**Resumen:**\n${result.summary}\n\n**Acciones Sugeridas:**\n${result.suggested_actions?.map((a: string) => `- ${a}`).join('\n')}\n\n**Contexto:**\n- Fuente: ${data.source}\n- ID: ${data.incident_id}`;

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
          <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent mb-2">
            ScoutOps SRE Agent
          </h1>
          <p className="text-slate-500 dark:text-slate-400 text-lg">
            Plataforma Inteligente de Triage de Incidentes
          </p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          <div className="lg:col-span-5">
            <ReportForm onIncidentCreated={handleIncidentCreated} />
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

            {incidentData?.result && (
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
