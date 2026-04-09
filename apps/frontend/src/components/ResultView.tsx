"use client";

interface ResultViewProps {
  result: {
    incident_type: string;
    severity: string;
    affected_plugin: string;
    summary: string;
    suggested_actions: string[];
    layer: string;
    affected_file?: string;
    confidence_score?: number;
    assigned_team?: string;
    processing_time_ms?: number;
  };
}

export default function ResultView({ result }: ResultViewProps) {
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "P1": return "bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800";
      case "P2": return "bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-900/30 dark:text-orange-400 dark:border-orange-800";
      case "P3": return "bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-400 dark:border-yellow-800";
      default: return "bg-gray-100 text-gray-800 border-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-700";
    }
  };

  const confidencePct = result.confidence_score != null
    ? Math.round(result.confidence_score * 100)
    : null;

  const confidenceColor = confidencePct == null
    ? "bg-slate-200 dark:bg-slate-700"
    : confidencePct >= 80
      ? "bg-green-500"
      : confidencePct >= 70
        ? "bg-yellow-400"
        : "bg-red-500";

  return (
    <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-lg border border-slate-100 dark:border-slate-700">
      <div className="flex justify-between items-start mb-6">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 dark:text-white">Diagnóstico del Agente</h2>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            Análisis completado
            {result.processing_time_ms != null && (
              <span className="ml-2 text-xs bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400 px-2 py-0.5 rounded-full">
                {result.processing_time_ms < 1000
                  ? `${result.processing_time_ms}ms`
                  : `${(result.processing_time_ms / 1000).toFixed(1)}s`}
              </span>
            )}
          </p>
        </div>
        <span className={`px-4 py-1.5 rounded-full text-sm font-semibold border ${getSeverityColor(result.severity)}`}>
          {result.severity}
        </span>
      </div>

      <div className="space-y-5">
        {/* Main metadata grid */}
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-slate-50 dark:bg-slate-900 p-3 rounded-lg">
            <h3 className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Tipo</h3>
            <p className="mt-1 text-sm font-semibold text-slate-900 dark:text-white">{result.incident_type}</p>
          </div>
          <div className="bg-slate-50 dark:bg-slate-900 p-3 rounded-lg">
            <h3 className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Equipo</h3>
            <p className="mt-1 text-sm font-semibold text-slate-900 dark:text-white">{result.assigned_team || 'N/A'}</p>
          </div>
          <div className="bg-slate-50 dark:bg-slate-900 p-3 rounded-lg">
            <h3 className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Plugin Afectado</h3>
            <p className="mt-1 text-sm font-semibold text-slate-900 dark:text-white font-mono">{result.affected_plugin || 'N/A'}</p>
          </div>
          <div className="bg-slate-50 dark:bg-slate-900 p-3 rounded-lg">
            <h3 className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Capa</h3>
            <p className="mt-1 text-sm font-semibold text-slate-900 dark:text-white">{result.layer || 'N/A'}</p>
          </div>
        </div>

        {/* Affected file — WOW factor */}
        {result.affected_file && (
          <div className="bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-700 rounded-lg p-4">
            <div className="flex items-center space-x-2 mb-1">
              <svg className="w-4 h-4 text-indigo-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
              </svg>
              <h3 className="text-xs font-semibold text-indigo-700 dark:text-indigo-300 uppercase tracking-wide">
                Archivo identificado por RAG
              </h3>
            </div>
            <p className="text-sm font-mono text-indigo-900 dark:text-indigo-200 break-all">{result.affected_file}</p>
          </div>
        )}

        {/* Confidence score */}
        {confidencePct != null && (
          <div>
            <div className="flex justify-between items-center mb-1">
              <h3 className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                Confianza del Agente
              </h3>
              <span className="text-xs font-bold text-slate-700 dark:text-slate-300">{confidencePct}%</span>
            </div>
            <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all duration-700 ${confidenceColor}`}
                style={{ width: `${confidencePct}%` }}
              />
            </div>
            <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
              Umbral mínimo: 70% — {confidencePct >= 70 ? "Acción automática aprobada" : "Requiere revisión humana"}
            </p>
          </div>
        )}

        {/* Summary */}
        <div>
          <h3 className="text-sm font-semibold text-slate-800 dark:text-white mb-2">Resumen Técnico</h3>
          <p className="text-sm text-slate-700 dark:text-slate-300 bg-slate-50 dark:bg-slate-900 p-4 rounded-lg leading-relaxed">
            {result.summary}
          </p>
        </div>

        {/* Suggested actions */}
        <div>
          <h3 className="text-sm font-semibold text-slate-800 dark:text-white mb-2">Acciones Sugeridas</h3>
          <ul className="space-y-2">
            {result.suggested_actions?.map((action, index) => (
              <li key={index} className="flex items-start space-x-3 bg-slate-50 dark:bg-slate-900 p-3 rounded-lg">
                <svg className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="text-sm text-slate-700 dark:text-slate-300">{action}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
