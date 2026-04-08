"use client";

interface ResultViewProps {
  result: {
    incident_type: string;
    severity: string;
    affected_plugin: string;
    summary: string;
    suggested_actions: string[];
    layer: string;
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

  return (
    <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-lg border border-slate-100 dark:border-slate-700">
      <div className="flex justify-between items-start mb-6">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 dark:text-white">Diagnóstico del Agente</h2>
          <p className="text-slate-500 dark:text-slate-400 mt-1">Análisis completado exitosamente</p>
        </div>
        <span className={`px-4 py-1.5 rounded-full text-sm font-semibold border ${getSeverityColor(result.severity)}`}>
          Severity: {result.severity}
        </span>
      </div>

      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-slate-50 dark:bg-slate-900 p-4 rounded-lg">
            <h3 className="text-sm font-medium text-slate-500 dark:text-slate-400">Tipo de Incidente</h3>
            <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{result.incident_type}</p>
          </div>
          <div className="bg-slate-50 dark:bg-slate-900 p-4 rounded-lg">
            <h3 className="text-sm font-medium text-slate-500 dark:text-slate-400">Plugin Afectado</h3>
            <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{result.affected_plugin || 'N/A'}</p>
          </div>
        </div>

        <div>
          <h3 className="text-lg font-semibold text-slate-800 dark:text-white mb-2">Resumen</h3>
          <p className="text-slate-700 dark:text-slate-300 bg-slate-50 dark:bg-slate-900 p-4 rounded-lg leading-relaxed">
            {result.summary}
          </p>
        </div>

        <div>
          <h3 className="text-lg font-semibold text-slate-800 dark:text-white mb-3">Acciones Sugeridas</h3>
          <ul className="space-y-2">
            {result.suggested_actions?.map((action, index) => (
              <li key={index} className="flex items-start space-x-3 bg-slate-50 dark:bg-slate-900 p-3 rounded-lg">
                <svg className="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="text-slate-700 dark:text-slate-300">{action}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
