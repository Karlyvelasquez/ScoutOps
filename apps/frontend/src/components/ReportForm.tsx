"use client";

import { useState, useRef, ChangeEvent } from "react";

interface ReportFormProps {
  onIncidentCreated: (incidentId: string) => void;
  isProcessing?: boolean;
}

export default function ReportForm({ onIncidentCreated, isProcessing = false }: ReportFormProps) {
  const [description, setDescription] = useState("");
  const [source, setSource] = useState("QA");
  const [reporterEmail, setReporterEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [vagueWarning, setVagueWarning] = useState<string | null>(null);
  const [validating, setValidating] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [attachedFile, setAttachedFile] = useState<File | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    setAttachedFile(file);
  };

  const handleDescriptionBlur = async () => {
    if (description.trim().length < 10) return;
    setValidating(true);
    setVagueWarning(null);
    try {
      const res = await fetch('/api/validate-input', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description, source }),
      });
      if (res.ok) {
        const data = await res.json();
        if (!data.is_valid) {
          setVagueWarning(data.reason || 'This input does not look like a valid incident report.');
        }
      }
    } catch {
      // Silently ignore — validation is non-blocking
    } finally {
      setValidating(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("description", description);
      formData.append("source", source);
      if (reporterEmail) formData.append("reporter_email", reporterEmail);
      if (attachedFile) formData.append("attachment", attachedFile);

      const res = await fetch("/api/incident", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.details || errorData.error || "Error al crear el incidente");
      }

      const data = await res.json();
      onIncidentCreated(data.incident_id);
      setDescription("");
      setFileName(null);
      setAttachedFile(null);
      setReporterEmail("");
      setVagueWarning(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-lg space-y-6">
      <h2 className="text-2xl font-bold text-slate-800 dark:text-white">Reportar Incidente</h2>
      
      {error && (
        <div className="bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 p-4 rounded-lg flex items-center space-x-2">
          <svg className="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-sm font-medium">{error}</span>
        </div>
      )}

      <div className="space-y-2">
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Descripción</label>
        <textarea
          required
          minLength={10}
              className="w-full h-32 px-4 py-3 rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors resize-none"
          placeholder="Describe el incidente (min 10 caracteres)..."
          value={description}
          onChange={(e) => { setDescription(e.target.value); setVagueWarning(null); }}
          onBlur={handleDescriptionBlur}
        />
      </div>

      <div className="space-y-2">
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Fuente</label>
        <select
          className="w-full px-4 py-3 rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
          value={source}
          onChange={(e) => setSource(e.target.value)}
        >
          <option value="QA">QA</option>
          <option value="soporte">Soporte</option>
          <option value="monitoring">Monitoring</option>
        </select>
      </div>

      <div className="space-y-2">
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Email (Opcional)</label>
        <input
          type="email"
          className="w-full px-4 py-3 rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
          placeholder="tu@empresa.com — para notificación de resolución"
          value={reporterEmail}
          onChange={(e: ChangeEvent<HTMLInputElement>) => setReporterEmail(e.target.value)}
        />
      </div>

      <div className="space-y-2">
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Evidencia (Opcional)</label>
        <div
          onClick={() => fileInputRef.current?.click()}
          className="border-2 border-dashed border-slate-300 dark:border-slate-600 rounded-lg p-6 text-center cursor-pointer hover:border-blue-500 dark:hover:border-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-all"
        >
          <input
            type="file"
            className="hidden"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".log,image/*"
          />
          <div className="flex flex-col items-center space-y-2">
            <svg className="w-8 h-8 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <span className="text-sm font-medium text-slate-600 dark:text-slate-400">
              {fileName ? fileName : "Arrastra un archivo o haz clic para subir (.log o imágenes)"}
            </span>
          </div>
        </div>
      </div>

      {vagueWarning && (
        <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-300 dark:border-amber-700 rounded-lg p-4 flex items-start space-x-3">
          <svg className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
          </svg>
          <div>
            <p className="text-sm font-semibold text-amber-800 dark:text-amber-300">Input no reconocido como reporte válido</p>
            <p className="text-xs text-amber-700 dark:text-amber-400 mt-0.5">{vagueWarning}</p>
          </div>
        </div>
      )}

      <button
        type="submit"
        disabled={loading || validating || isProcessing}
        className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-4 rounded-lg flex items-center justify-center space-x-2 disabled:bg-blue-400 transition-colors"
      >
        {validating ? (
          <>
            <svg className="animate-spin h-5 w-5 text-white" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            <span>Validando...</span>
          </>
        ) : loading ? (
          <>
            <svg className="animate-spin h-5 w-5 text-white" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            <span>Procesando...</span>
          </>
        ) : (
          <span>Enviar Reporte</span>
        )}
      </button>
    </form>
  );
}
