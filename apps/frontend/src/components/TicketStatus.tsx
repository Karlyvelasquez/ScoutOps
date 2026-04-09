"use client";

interface TicketStatusProps {
  ticket: {
    ticket_id: string;
    status: string;
    duplicate_of?: number | null;
  } | null;
  incidentId: string;
  onCreating?: boolean;
}

export default function TicketStatus({ ticket, incidentId, onCreating }: TicketStatusProps) {
  const isDuplicate = ticket?.duplicate_of != null;

  return (
    <div className="bg-slate-50 dark:bg-slate-900/50 p-6 rounded-xl border border-slate-200 dark:border-slate-700 mt-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-semibold text-slate-800 dark:text-white">Ticket de GitHub</h3>
            {isDuplicate && (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-orange-100 text-orange-800 border border-orange-200 dark:bg-orange-900/30 dark:text-orange-300 dark:border-orange-700">
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                Duplicado
              </span>
            )}
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            {isDuplicate
              ? `Este incidente fue consolidado en el issue #${ticket!.duplicate_of} existente`
              : "Gestión y seguimiento del incidente"}
          </p>
        </div>

        {onCreating ? (
          <div className="flex items-center space-x-2 text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 px-4 py-2 rounded-lg">
            <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            <span className="font-medium text-sm">Creando issue...</span>
          </div>
        ) : ticket ? (
          <div className="flex items-center space-x-4">
            <div className={`px-3 py-1 rounded-full text-sm font-medium border ${
              isDuplicate
                ? 'bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-900/30 dark:text-orange-400 dark:border-orange-700'
                : ticket.status === 'open'
                ? 'bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-400'
                : 'bg-purple-100 text-purple-800 border-purple-200 dark:bg-purple-900/30 dark:text-purple-400'
            }`}>
              {isDuplicate ? `#${ticket.duplicate_of}` : ticket.status}
            </div>
            {ticket.ticket_id.startsWith('http') ? (
              <a
                href={ticket.ticket_id}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center space-x-1 text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 font-medium"
              >
                <span>{isDuplicate ? 'Ver Issue Original' : 'Ver Issue'}</span>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
            ) : (
              <span className="text-slate-600 dark:text-slate-300 font-mono text-sm">
                ID: {ticket.ticket_id}
              </span>
            )}
          </div>
        ) : (
          <div className="text-sm font-medium text-slate-500 dark:text-slate-400 bg-white dark:bg-slate-800 px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700">
            Pendiente de creación
          </div>
        )}
      </div>

      {isDuplicate && (
        <div className="mt-4 flex items-start gap-2 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg px-4 py-3">
          <svg className="w-4 h-4 text-orange-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-xs text-orange-700 dark:text-orange-300">
            El agente detectó un issue abierto con el mismo tipo de incidente y plugin afectado. Se añadió un comentario al issue existente en lugar de crear uno nuevo, para evitar duplicados y centralizar el seguimiento.
          </p>
        </div>
      )}
    </div>
  );
}
