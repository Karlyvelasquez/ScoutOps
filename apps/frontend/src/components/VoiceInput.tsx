"use client";

import { useRef, useState, useCallback, useEffect } from "react";

interface VoiceInputProps {
  /** Called when a new incident_id is created via voice */
  onIncidentCreated?: (incidentId: string) => void;
  /** Called when the agent finishes processing and returns the full result */
  onIncidentResult?: (data: any) => void;
}

// Web Speech API types not included in default TS lib
declare global {
  interface Window {
    SpeechRecognition: any;
    webkitSpeechRecognition: any;
  }
}

type Status = "idle" | "listening" | "processing" | "speaking";
type Lang = "es" | "en";

const LANG_CONFIG: Record<Lang, { bcp47: string; label: string }> = {
  es: { bcp47: "es-MX", label: "ES" },
  en: { bcp47: "en-US", label: "EN" },
};

export default function VoiceInput({ onIncidentCreated, onIncidentResult }: VoiceInputProps) {
  const [isActive, setIsActive] = useState(false);
  const [status, setStatus] = useState<Status>("idle");
  const [lang, setLang] = useState<Lang>("es");
  const [transcript, setTranscript] = useState<string | null>(null);
  const [responseText, setResponseText] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const recognitionRef = useRef<any>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const audioQueueRef = useRef<ArrayBuffer[]>([]);
  const isPlayingRef = useRef(false);
  const activeRef = useRef(false); // stable ref to avoid stale closure in recognition.onend

  // -------------------------------------------------------------------------
  // Audio playback — MP3 chunks queued and played sequentially
  // -------------------------------------------------------------------------
  const drainQueue = useCallback(async () => {
    if (isPlayingRef.current || audioQueueRef.current.length === 0) return;
    isPlayingRef.current = true;
    setStatus("speaking");

    const ctx = audioCtxRef.current!;
    while (audioQueueRef.current.length > 0) {
      const raw = audioQueueRef.current.shift()!;
      try {
        const decoded = await ctx.decodeAudioData(raw.slice(0));
        const src = ctx.createBufferSource();
        src.buffer = decoded;
        src.connect(ctx.destination);
        await new Promise<void>((res) => {
          src.onended = () => res();
          src.start();
        });
      } catch {
        // Chunk too small to decode — ignore
      }
    }

    isPlayingRef.current = false;
    if (activeRef.current) setStatus("listening");
  }, []);

  // -------------------------------------------------------------------------
  // Start voice session
  // -------------------------------------------------------------------------
  const startSession = useCallback(() => {
    setError(null);

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setError("Voice not supported in this browser. Use Chrome or Edge.");
      return;
    }

    audioCtxRef.current = new AudioContext();
    activeRef.current = true;

    // ---- WebSocket ----
    const wsBase =
      process.env.NEXT_PUBLIC_WS_URL?.replace(/^http/, "ws") ?? "ws://localhost:8000";
    const ws = new WebSocket(`${wsBase}/ws/voice`);
    wsRef.current = ws;

    ws.onopen = () => setStatus("listening");
    ws.onclose = () => {
      if (activeRef.current) setError("Connection lost. Click the mic to reconnect.");
      setIsActive(false);
      setStatus("idle");
    };

    ws.onmessage = async (event) => {
      if (typeof event.data === "string") {
        const msg = JSON.parse(event.data);

        if (msg.type === "transcript") {
          setTranscript(msg.text);
          setStatus("processing");
        }
        if (msg.type === "response_text") {
          setResponseText(msg.text);
        }
        if (msg.type === "audio_end") {
          // Queue drain handles status transition back to "listening"
        }
        if (msg.type === "incident_created") {
          onIncidentCreated?.(msg.incident_id);
        }
        if (msg.type === "incident_result") {
          onIncidentResult?.(msg.data);
        }
        if (msg.type === "error") {
          setError(msg.message);
        }
      } else {
        // Binary MP3 chunk from edge-tts
        const buf = await (event.data as Blob).arrayBuffer();
        audioQueueRef.current.push(buf);
        drainQueue();
      }
    };

    // ---- Web Speech API ----
    const recognition = new SpeechRecognition();
    recognition.lang = LANG_CONFIG[lang].bcp47;
    recognition.continuous = true;
    recognition.interimResults = false;
    recognitionRef.current = recognition;

    recognition.onresult = (e: any) => {
      const text = e.results[e.results.length - 1][0].transcript.trim();
      if (!text) return;
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "transcript", text, lang }));
      }
    };

    recognition.onerror = (e: any) => {
      if (e.error === "no-speech" || e.error === "aborted") return;
      setError(`Recognition error: ${e.error}`);
    };

    recognition.onend = () => {
      // Auto-restart while session is still active
      if (activeRef.current) {
        try { recognition.start(); } catch { /* already started */ }
      }
    };

    recognition.start();
    setIsActive(true);
    setStatus("listening");
  }, [lang, drainQueue, onIncidentCreated, onIncidentResult]);

  // -------------------------------------------------------------------------
  // Stop voice session
  // -------------------------------------------------------------------------
  const stopSession = useCallback(() => {
    activeRef.current = false;
    recognitionRef.current?.stop();
    wsRef.current?.send(JSON.stringify({ type: "end_session" }));
    wsRef.current?.close();
    audioCtxRef.current?.close().catch(() => {});
    audioQueueRef.current = [];
    isPlayingRef.current = false;
    setIsActive(false);
    setStatus("idle");
    setTranscript(null);
    setResponseText(null);
  }, []);

  // -------------------------------------------------------------------------
  // Language toggle — restarts recognition with new lang
  // -------------------------------------------------------------------------
  const toggleLang = useCallback(() => {
    const next: Lang = lang === "es" ? "en" : "es";
    setLang(next);
    if (recognitionRef.current && activeRef.current) {
      recognitionRef.current.lang = LANG_CONFIG[next].bcp47;
      try {
        recognitionRef.current.stop(); // onend will restart it with new lang
      } catch { /* ignore */ }
    }
  }, [lang]);

  // Cleanup on unmount
  useEffect(() => () => { stopSession(); }, [stopSession]);

  // -------------------------------------------------------------------------
  // Visual config per status
  // -------------------------------------------------------------------------
  const STATUS_CFG: Record<Status, {
    label: string;
    ringColor: string;
    btnColor: string;
    pulse: boolean;
  }> = {
    idle:       { label: "Toca para hablar",  ringColor: "ring-slate-300 dark:ring-slate-600", btnColor: "bg-slate-700 hover:bg-slate-600",  pulse: false },
    listening:  { label: "Escuchando...",     ringColor: "ring-red-400",                       btnColor: "bg-red-500 hover:bg-red-600",      pulse: true  },
    processing: { label: "Procesando...",     ringColor: "ring-blue-400",                      btnColor: "bg-blue-500",                      pulse: false },
    speaking:   { label: "Respondiendo...",   ringColor: "ring-emerald-400",                   btnColor: "bg-emerald-500",                   pulse: true  },
  };

  const cfg = STATUS_CFG[status];

  return (
    <div className="flex flex-col items-center gap-4">

      {/* Outer glow ring + mic button */}
      <div className="relative flex items-center justify-center">
        {/* Animated ring */}
        {cfg.pulse && (
          <span
            className={`absolute inset-0 rounded-full animate-ping opacity-20 ${cfg.btnColor}`}
            style={{ transform: "scale(1.5)" }}
          />
        )}

        <button
          onClick={isActive ? stopSession : startSession}
          className={`
            relative z-10 w-20 h-20 rounded-full text-white shadow-xl
            ring-4 ${cfg.ringColor}
            ${cfg.btnColor}
            transition-all duration-200
            focus:outline-none focus:ring-offset-2
          `}
          title={isActive ? "Detener sesión de voz" : "Iniciar sesión de voz"}
        >
          {/* Mic icon / stop icon */}
          <svg
            className="w-8 h-8 mx-auto"
            fill="currentColor"
            viewBox="0 0 24 24"
          >
            {isActive ? (
              // Stop square
              <rect x="6" y="6" width="12" height="12" rx="2.5" />
            ) : (
              // Microphone
              <path d="M12 1a4 4 0 014 4v6a4 4 0 01-8 0V5a4 4 0 014-4zm-1 17.93V21h2v-2.07A8.001 8.001 0 0020 11h-2a6 6 0 01-12 0H4a8.001 8.001 0 007 7.93z" />
            )}
          </svg>
        </button>
      </div>

      {/* Status label */}
      <span className="text-xs font-medium text-slate-500 dark:text-slate-400 tracking-wide uppercase">
        {cfg.label}
      </span>

      {/* Language toggle */}
      <button
        onClick={toggleLang}
        className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
        title="Toggle language / Cambiar idioma"
      >
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
        </svg>
        {LANG_CONFIG[lang].label}
      </button>

      {/* Error message */}
      {error && (
        <p className="text-xs text-red-500 dark:text-red-400 text-center max-w-[200px]">
          {error}
        </p>
      )}

      {/* Last transcript bubble */}
      {transcript && isActive && (
        <div className="w-full max-w-[220px] bg-slate-100 dark:bg-slate-700 rounded-xl px-3 py-2 text-xs text-slate-700 dark:text-slate-200 italic text-center leading-relaxed">
          "{transcript}"
        </div>
      )}

      {/* Last response bubble */}
      {responseText && isActive && status !== "idle" && (
        <div className="w-full max-w-[220px] bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-700 rounded-xl px-3 py-2 text-xs text-blue-800 dark:text-blue-200 text-center leading-relaxed">
          {responseText}
        </div>
      )}
    </div>
  );
}
