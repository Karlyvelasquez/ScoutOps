"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import "@/app/control-core.css";

type MainView = "tickets" | "report";
type TicketView = "cards" | "list";
type VoiceLang = "es" | "en";
type VoiceStatus = "idle" | "listening" | "processing" | "speaking";

type ApiTicket = {
  id: string;
  incident_type: string | null;
  severity: string | null;
  affected_plugin: string | null;
  summary: string | null;
  original_description: string | null;
  status: string | null;
  github_ticket_url: string | null;
  github_ticket_number: number | null;
  jira_ticket_url: string | null;
  jira_ticket_key: string | null;
  created_at: string;
  resolved_at: string | null;
};

type TicketInfo = {
  ticket_id: string;
  status: string;
  duplicate_of?: number | null;
};

type IncidentResult = {
  incident_type: string;
  severity: string;
  affected_plugin: string;
  summary: string;
  suggested_actions?: string[];
  layer?: string;
  affected_file?: string;
  confidence_score?: number;
  assigned_team?: string;
  processing_time_ms?: number;
  attachment_analysis?: string;
};

type IncidentData = {
  incident_id: string;
  status: "en_proceso" | "completado" | "escalado_humano" | "error";
  description: string;
  source: "QA" | "soporte" | "monitoring";
  result?: IncidentResult;
  error?: string;
  ticket?: TicketInfo | null;
  reporter_email?: string;
};

type UiTicket = {
  id: string;
  title: string;
  agent: string;
  statusLabel: string;
  statusClass: string;
  desc: string;
  source: ApiTicket;
};

type SourceOption = {
  key: "QA" | "Production" | "Infra";
  value: "QA" | "soporte" | "monitoring";
  label: string;
  context: string;
};

const SOURCE_OPTIONS: SourceOption[] = [
  {
    key: "QA",
    value: "QA",
    label: "QA",
    context:
      "Context: include test case, expected vs actual behavior, build version, and reproducible steps.",
  },
  {
    key: "Production",
    value: "soporte",
    label: "Production",
    context:
      "Context: include user impact, affected services, error rates, timeline, and rollback status.",
  },
  {
    key: "Infra",
    value: "monitoring",
    label: "Infra",
    context:
      "Context: include host/service IDs, infrastructure layer, recent deployments, and relevant logs.",
  },
];

const VOICE_LANG: Record<VoiceLang, { bcp47: string; label: string }> = {
  es: { bcp47: "es-MX", label: "ES" },
  en: { bcp47: "en-US", label: "EN" },
};

function mapTicketStatus(ticket: ApiTicket): Pick<UiTicket, "statusLabel" | "statusClass"> {
  const severity = (ticket.severity || "").toUpperCase();
  const status = (ticket.status || "open").toLowerCase();

  if (severity === "P1") {
    return { statusLabel: "Critical", statusClass: "status-critical" };
  }

  if (severity === "P2") {
    return { statusLabel: "High", statusClass: "status-high" };
  }

  if (status === "resolved" || status === "closed") {
    return { statusLabel: "Stable", statusClass: "status-stable" };
  }

  if (status === "open" || status === "in_progress") {
    return { statusLabel: "Pending", statusClass: "status-pending" };
  }

  return { statusLabel: "Pending", statusClass: "status-default" };
}

function toUiTicket(ticket: ApiTicket): UiTicket {
  const map = mapTicketStatus(ticket);
  const title = `${ticket.incident_type || "unknown_incident"} - ${ticket.affected_plugin || "unknown-plugin"}`;
  const ticketId = ticket.github_ticket_number ? `#${ticket.github_ticket_number}` : `#${ticket.id.slice(-4)}`;

  return {
    id: ticketId,
    title,
    agent: ticket.jira_ticket_key || "AI-Core",
    statusLabel: map.statusLabel,
    statusClass: map.statusClass,
    desc: (ticket.summary || ticket.original_description || "No summary available").slice(0, 180),
    source: ticket,
  };
}

function createGithubIssueBody(data: IncidentData): { title: string; body: string } {
  const result = data.result;
  if (!result) {
    return {
      title: "[P3] unknown_incident - General",
      body: "No result details available",
    };
  }

  const title = `[${result.severity}] ${result.incident_type} - ${result.affected_plugin || "General"}`;
  const actionsBlock = result.suggested_actions?.length
    ? result.suggested_actions.map((a) => `- ${a}`).join("\n")
    : "- No suggestions provided";

  const body = [
    "## Incident Triage Report",
    "",
    `- **Incident Type:** ${result.incident_type || "unknown"}`,
    `- **Severity:** ${result.severity || "unknown"}`,
    `- **Affected Plugin:** ${result.affected_plugin || "unknown"}`,
    `- **Layer:** ${result.layer || "unknown"}`,
    `- **Assigned Team:** ${result.assigned_team || "unknown"}`,
    `- **Reporter Email:** ${data.reporter_email || "unknown"}`,
    "",
    "### Summary",
    result.summary || "",
    "",
    "### Suggested Actions",
    actionsBlock,
    "",
    "### Original Description",
    data.description || "",
  ].join("\n");

  return { title, body };
}

interface SpeechRecognitionLike {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: SpeechRecognitionErrorLike) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
}

interface SpeechRecognitionResultLike {
  transcript: string;
}

interface SpeechRecognitionEventLike {
  results: ArrayLike<ArrayLike<SpeechRecognitionResultLike>>;
}

interface SpeechRecognitionErrorLike {
  error: string;
}

type SpeechRecognitionCtor = new () => SpeechRecognitionLike;

interface ControlCoreShellProps {
  initialView?: MainView;
}

export default function ControlCoreShell({ initialView = "report" }: ControlCoreShellProps) {
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [mainView, setMainView] = useState<MainView>(initialView);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [ticketView, setTicketView] = useState<TicketView>("cards");

  const [tickets, setTickets] = useState<ApiTicket[]>([]);
  const [ticketsLoading, setTicketsLoading] = useState(false);
  const [ticketSearch, setTicketSearch] = useState("");
  const [ticketStatusFilter, setTicketStatusFilter] = useState<"all" | "open" | "resolved">("all");
  const [ticketSeverityFilter, setTicketSeverityFilter] = useState<"all" | "P1" | "P2" | "P3">("all");

  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);

  const [source, setSource] = useState<SourceOption>(SOURCE_OPTIONS[0]);
  const [description, setDescription] = useState("");
  const [fileName, setFileName] = useState("No file attached");
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [reportError, setReportError] = useState<string | null>(null);
  const [inputInvalid, setInputInvalid] = useState(false);
  const [validating, setValidating] = useState(false);
  const [submitLoading, setSubmitLoading] = useState(false);
  const [micHighlight, setMicHighlight] = useState(false);

  const [incidentId, setIncidentId] = useState<string | null>(null);
  const [incidentData, setIncidentData] = useState<IncidentData | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const [isCreatingTicket, setIsCreatingTicket] = useState(false);

  const [voiceLang, setVoiceLang] = useState<VoiceLang>("en");
  const [voiceStatus, setVoiceStatus] = useState<VoiceStatus>("idle");
  const [voiceActive, setVoiceActive] = useState(false);
  const [voiceHeard, setVoiceHeard] = useState("Awaiting voice input...");
  const [voiceAgent, setVoiceAgent] = useState("Awaiting response output...");

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const submittingRef = useRef(false);

  const wsRef = useRef<WebSocket | null>(null);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const audioQueueRef = useRef<ArrayBuffer[]>([]);
  const isPlayingRef = useRef(false);
  const voiceLiveRef = useRef(false);

  const selectedTicket = useMemo(() => {
    if (!selectedTicketId) return null;
    return tickets.find((t) => t.id === selectedTicketId) || null;
  }, [selectedTicketId, tickets]);

  const uiTickets = useMemo(() => tickets.map(toUiTicket), [tickets]);

  const ticketStats = useMemo(() => {
    const total = tickets.length;
    const resolved = tickets.filter((ticket) => {
      const status = (ticket.status || "open").toLowerCase();
      return status === "resolved" || status === "closed";
    }).length;
    const open = total - resolved;

    const pluginCounts = tickets.reduce<Record<string, number>>((acc, ticket) => {
      const plugin = (ticket.affected_plugin || "unknown-plugin").trim() || "unknown-plugin";
      acc[plugin] = (acc[plugin] || 0) + 1;
      return acc;
    }, {});

    let mostAffectedPlugin = "N/A";
    let maxCount = 0;
    for (const [plugin, count] of Object.entries(pluginCounts)) {
      if (count > maxCount) {
        maxCount = count;
        mostAffectedPlugin = plugin;
      }
    }

    return { total, open, resolved, mostAffectedPlugin };
  }, [tickets]);

  const filteredUiTickets = useMemo(() => {
    const query = ticketSearch.trim().toLowerCase();

    return uiTickets.filter((ticket) => {
      const api = ticket.source;
      const status = (api.status || "open").toLowerCase();
      const severity = (api.severity || "P3").toUpperCase();

      const matchesSearch =
        query.length === 0 ||
        ticket.id.toLowerCase().includes(query) ||
        ticket.title.toLowerCase().includes(query) ||
        ticket.desc.toLowerCase().includes(query) ||
        (api.affected_plugin || "").toLowerCase().includes(query);

      const matchesStatus =
        ticketStatusFilter === "all" ||
        (ticketStatusFilter === "resolved"
          ? status === "resolved" || status === "closed"
          : status !== "resolved" && status !== "closed");

      const matchesSeverity = ticketSeverityFilter === "all" || severity === ticketSeverityFilter;

      return matchesSearch && matchesStatus && matchesSeverity;
    });
  }, [ticketSearch, ticketSeverityFilter, ticketStatusFilter, uiTickets]);

  const fetchTickets = useCallback(async () => {
    try {
      const res = await fetch("/api/tickets", { cache: "no-store" });
      if (!res.ok) return;
      const data = (await res.json()) as ApiTicket[];
      setTickets(Array.isArray(data) ? data : []);
    } catch {
      setTickets([]);
    }
  }, []);

  useEffect(() => {
    setTicketsLoading(true);
    fetchTickets().finally(() => setTicketsLoading(false));

    const intervalId = setInterval(() => {
      fetchTickets();
    }, 15000);

    return () => clearInterval(intervalId);
  }, [fetchTickets]);

  const createGithubIssue = useCallback(async (data: IncidentData) => {
    if (!data.result) return;

    setIsCreatingTicket(true);
    try {
      const payload = createGithubIssueBody(data);

      const res = await fetch("/api/github", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: payload.title,
          body: payload.body,
          incident_id: data.incident_id,
        }),
      });

      if (!res.ok) {
        throw new Error("Failed to create github issue");
      }

      const issueData = (await res.json()) as { html_url: string };

      setIncidentData((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          ticket: {
            ticket_id: issueData.html_url,
            status: "open",
          },
        };
      });
    } catch {
      // keep UI stable, non-blocking
    } finally {
      setIsCreatingTicket(false);
    }
  }, []);

  useEffect(() => {
    let intervalId: ReturnType<typeof setInterval> | undefined;

    const pollIncident = async () => {
      if (!incidentId) return;
      try {
        const res = await fetch(`/api/incident/${incidentId}`);
        if (!res.ok) throw new Error("Error polling incident");

        const data = (await res.json()) as IncidentData;
        setIncidentData(data);

        if (
          data.status === "completado" ||
          data.status === "escalado_humano" ||
          data.status === "error"
        ) {
          setIsPolling(false);
          if (intervalId) clearInterval(intervalId);

          if (data.status === "completado" && !data.ticket) {
            createGithubIssue(data);
          }
        }
      } catch {
        // non-blocking polling failure
      }
    };

    if (isPolling && incidentId) {
      intervalId = setInterval(pollIncident, 2000);
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [createGithubIssue, incidentId, isPolling]);

  const handleDescriptionBlur = useCallback(async () => {
    if (description.trim().length < 10) return;
    setValidating(true);

    try {
      const res = await fetch("/api/validate-input", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description, source: source.value }),
      });

      if (res.ok && !submittingRef.current) {
        const data = (await res.json()) as { is_valid?: boolean };
        setInputInvalid(data.is_valid === false);
      }
    } catch {
      // validation is non-blocking
    } finally {
      setValidating(false);
    }
  }, [description, source.value]);

  const handleSubmit = useCallback(
    async (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      submittingRef.current = true;
      setSubmitLoading(true);
      setReportError(null);

      try {
        const formData = new FormData();
        formData.append("description", description);
        formData.append("source", source.value);
        if (attachedFile) {
          formData.append("attachment", attachedFile);
        }

        const res = await fetch("/api/incident", {
          method: "POST",
          body: formData,
        });

        if (!res.ok) {
          const errorData = (await res.json()) as { details?: string; error?: string };
          throw new Error(errorData.details || errorData.error || "Error al crear el incidente");
        }

        const data = (await res.json()) as { incident_id: string };
        setIncidentId(data.incident_id);
        setIncidentData(null);
        setIsPolling(true);
        setMainView("report");

        setDescription("");
        setAttachedFile(null);
        setFileName("No file attached");
      } catch (err) {
        const message = err instanceof Error ? err.message : "No se pudo enviar el reporte";
        setReportError(message);
      } finally {
        setSubmitLoading(false);
        submittingRef.current = false;
      }
    },
    [attachedFile, description, source.value]
  );

  const onFileChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      setAttachedFile(null);
      setFileName("No file attached");
      return;
    }

    setAttachedFile(file);
    setFileName(file.name);
  }, []);

  const openDetail = useCallback((ticket: UiTicket) => {
    setSelectedTicketId(ticket.source.id);
  }, []);

  const closeDetail = useCallback(() => {
    setSelectedTicketId(null);
  }, []);

  const drainQueue = useCallback(async () => {
    if (isPlayingRef.current || audioQueueRef.current.length === 0) return;
    if (!audioCtxRef.current) return;

    isPlayingRef.current = true;
    setVoiceStatus("speaking");

    const ctx = audioCtxRef.current;

    while (audioQueueRef.current.length > 0) {
      const raw = audioQueueRef.current.shift();
      if (!raw) continue;

      try {
        const decoded = await ctx.decodeAudioData(raw.slice(0));
        const src = ctx.createBufferSource();
        src.buffer = decoded;
        src.connect(ctx.destination);

        await new Promise<void>((resolve) => {
          src.onended = () => resolve();
          src.start();
        });
      } catch {
        // ignore decode errors
      }
    }

    isPlayingRef.current = false;
    if (voiceLiveRef.current) {
      setVoiceStatus("listening");
    }
  }, []);

  const stopVoiceSession = useCallback(() => {
    voiceLiveRef.current = false;
    recognitionRef.current?.stop();
    wsRef.current?.send(JSON.stringify({ type: "end_session" }));
    wsRef.current?.close();

    audioCtxRef.current?.close().catch(() => undefined);

    wsRef.current = null;
    recognitionRef.current = null;
    audioCtxRef.current = null;
    audioQueueRef.current = [];
    isPlayingRef.current = false;

    setVoiceActive(false);
    setVoiceStatus("idle");
  }, []);

  const startVoiceSession = useCallback(() => {
    const speechWindow = window as Window & {
      SpeechRecognition?: SpeechRecognitionCtor;
      webkitSpeechRecognition?: SpeechRecognitionCtor;
    };
    const SpeechRecognitionCtor = speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition;
    if (!SpeechRecognitionCtor) {
      setVoiceAgent("Voice not supported in this browser. Use Chrome or Edge.");
      return;
    }

    setVoiceAgent("Awaiting response output...");
    setVoiceHeard("Awaiting voice input...");

    audioCtxRef.current = new AudioContext();
    voiceLiveRef.current = true;

    const wsBase = process.env.NEXT_PUBLIC_WS_URL?.replace(/^http/, "ws") || "ws://localhost:8000";
    const ws = new WebSocket(`${wsBase}/ws/voice`);
    wsRef.current = ws;

    ws.onopen = () => {
      setVoiceStatus("listening");
      setVoiceActive(true);
    };

    ws.onclose = () => {
      if (voiceLiveRef.current) {
        setVoiceAgent("Connection lost. Tap again to reconnect.");
      }
      setVoiceStatus("idle");
      setVoiceActive(false);
      voiceLiveRef.current = false;
    };

    ws.onmessage = async (event) => {
      if (typeof event.data === "string") {
        const msg = JSON.parse(event.data) as {
          type: string;
          text?: string;
          incident_id?: string;
          data?: IncidentData;
          message?: string;
        };

        if (msg.type === "transcript" && msg.text) {
          setVoiceHeard(msg.text);
          setVoiceStatus("processing");
        }

        if (msg.type === "response_text" && msg.text) {
          setVoiceAgent(msg.text);
        }

        if (msg.type === "incident_created" && msg.incident_id) {
          setIncidentId(msg.incident_id);
          setIncidentData(null);
          setIsPolling(true);
          setMainView("report");
        }

        if (msg.type === "incident_result" && msg.data) {
          setIncidentData(msg.data);
          setIsPolling(false);
          if (msg.data.status === "completado" && !msg.data.ticket) {
            createGithubIssue(msg.data);
          }
        }

        if (msg.type === "error" && msg.message) {
          setVoiceAgent(msg.message);
        }
      } else {
        const chunk = await (event.data as Blob).arrayBuffer();
        audioQueueRef.current.push(chunk);
        drainQueue();
      }
    };

    const recognition = new SpeechRecognitionCtor();
    recognition.lang = VOICE_LANG[voiceLang].bcp47;
    recognition.continuous = true;
    recognition.interimResults = false;

    recognition.onresult = (event: SpeechRecognitionEventLike) => {
      const transcript = event.results[event.results.length - 1][0]?.transcript?.trim();
      if (!transcript) return;
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "transcript", text: transcript, lang: voiceLang }));
      }
    };

    recognition.onerror = (event: SpeechRecognitionErrorLike) => {
      if (event.error === "no-speech" || event.error === "aborted") return;
      setVoiceAgent(`Recognition error: ${event.error}`);
    };

    recognition.onend = () => {
      if (!voiceLiveRef.current) return;
      try {
        recognition.start();
      } catch {
        // ignore if already started
      }
    };

    recognitionRef.current = recognition;
    recognition.start();
    setVoiceStatus("listening");
    setVoiceActive(true);
  }, [createGithubIssue, drainQueue, voiceLang]);

  const toggleVoiceSession = useCallback(() => {
    if (voiceActive) {
      stopVoiceSession();
      return;
    }
    startVoiceSession();
  }, [startVoiceSession, stopVoiceSession, voiceActive]);

  const toggleVoiceLang = useCallback(() => {
    setVoiceLang((prev) => {
      const next: VoiceLang = prev === "en" ? "es" : "en";

      if (recognitionRef.current && voiceLiveRef.current) {
        recognitionRef.current.lang = VOICE_LANG[next].bcp47;
        try {
          recognitionRef.current.stop();
        } catch {
          // ignore
        }
      }

      return next;
    });
  }, []);

  useEffect(() => {
    return () => {
      stopVoiceSession();
    };
  }, [stopVoiceSession]);

  const submitDisabled = submitLoading || isPolling || inputInvalid || (!attachedFile && description.trim().length < 10);

  const isEscalated = incidentData?.status === "escalado_humano";
  const isVague = (incidentData?.result?.confidence_score ?? 0) === 0;

  return (
    <div className="control-core-shell">
      <div
        className={`control-core-root ${sidebarCollapsed ? "sidebar-collapsed" : ""}`}
        data-theme={theme}
      >
        <aside className="sidebar">
          <div className="sidebar-head">
            <div className="logo" />
            <span className="brand">Control Core</span>
            <button
              className={`sidebar-toggle ${sidebarCollapsed ? "active" : ""}`}
              title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
              aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
              aria-expanded={!sidebarCollapsed}
              type="button"
              onClick={() => {
                setSidebarCollapsed((prev) => !prev);
                closeDetail();
              }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="15 18 9 12 15 6" />
              </svg>
            </button>
          </div>

          <nav className="sidebar-nav" aria-label="Main navigation">
            <button
              className={`nav-link ${mainView === "tickets" ? "active" : ""}`}
              type="button"
              onClick={() => {
                setMainView("tickets");
                closeDetail();
              }}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="3" width="18" height="18" rx="2" />
                <path d="M3 9h18M9 21V9" />
              </svg>
              <span className="nav-label">Tickets</span>
            </button>

            <button
              className={`nav-link ${mainView === "report" ? "active" : ""}`}
              type="button"
              onClick={() => {
                setMainView("report");
                closeDetail();
              }}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="3" />
                <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z" />
              </svg>
              <span className="nav-label">Report</span>
            </button>

            <Link href="/wrapped" className="nav-link">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
                <polyline points="17 6 23 6 23 12" />
              </svg>
              <span className="nav-label">Wrapped</span>
            </Link>
          </nav>

          <div className="sidebar-spacer" />

          <div className="utility-group">
            <button
              className="theme-toggle"
              id="themeToggle"
              title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
              aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
              aria-pressed={theme === "dark"}
              type="button"
              onClick={() => setTheme((prev) => (prev === "dark" ? "light" : "dark"))}
            >
              {theme === "dark" ? (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="5" />
                  <line x1="12" y1="1" x2="12" y2="3" />
                  <line x1="12" y1="21" x2="12" y2="23" />
                  <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
                  <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                  <line x1="1" y1="12" x2="3" y2="12" />
                  <line x1="21" y1="12" x2="23" y2="12" />
                  <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
                  <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
                </svg>
              ) : (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 12.79A9 9 0 1111.21 3a7 7 0 009.79 9.79z" />
                </svg>
              )}
              <span className="theme-label">{theme === "dark" ? "Dark mode enabled" : "Light mode enabled"}</span>
            </button>
          </div>
        </aside>

        <div className="app-view">
          <section
            className={`content-section tickets-section ${mainView !== "tickets" ? "hidden" : ""} ${selectedTicket ? "detail-open" : ""}`}
            id="ticketsSection"
          >
            <div className="page-heading-row">
              <h1 className="page-title">Ticket History</h1>
              <div className="view-switch" aria-label="Change view">
                <button
                  className={`view-btn ${ticketView === "cards" ? "active" : ""}`}
                  type="button"
                  onClick={() => {
                    setTicketView("cards");
                    closeDetail();
                  }}
                >
                  Cards
                </button>
                <button
                  className={`view-btn ${ticketView === "list" ? "active" : ""}`}
                  type="button"
                  onClick={() => {
                    setTicketView("list");
                    closeDetail();
                  }}
                >
                  List
                </button>
              </div>
            </div>

            <section className="history-stats-grid" aria-label="Ticket summary">
              <article className="history-stat-card">
                <p className="history-stat-label">Total tickets</p>
                <p className="history-stat-value">{ticketStats.total}</p>
              </article>
              <article className="history-stat-card">
                <p className="history-stat-label">Open tickets</p>
                <p className="history-stat-value">{ticketStats.open}</p>
              </article>
              <article className="history-stat-card">
                <p className="history-stat-label">Resolved tickets</p>
                <p className="history-stat-value">{ticketStats.resolved}</p>
              </article>
              <article className="history-stat-card">
                <p className="history-stat-label">Most affected plugin</p>
                <p className="history-stat-value truncate">{ticketStats.mostAffectedPlugin}</p>
              </article>
            </section>

            <div className="history-filters" role="group" aria-label="Ticket filters">
              <input
                className="history-filter-input"
                type="search"
                value={ticketSearch}
                onChange={(event) => setTicketSearch(event.target.value)}
                placeholder="Search by id, plugin or summary"
                aria-label="Search tickets"
              />

              <select
                className="history-filter-select"
                value={ticketStatusFilter}
                onChange={(event) => setTicketStatusFilter(event.target.value as "all" | "open" | "resolved")}
                aria-label="Filter by status"
              >
                <option value="all">All status</option>
                <option value="open">Open</option>
                <option value="resolved">Resolved</option>
              </select>

              <select
                className="history-filter-select"
                value={ticketSeverityFilter}
                onChange={(event) => setTicketSeverityFilter(event.target.value as "all" | "P1" | "P2" | "P3")}
                aria-label="Filter by severity"
              >
                <option value="all">All severity</option>
                <option value="P1">P1</option>
                <option value="P2">P2</option>
                <option value="P3">P3</option>
              </select>

              <button
                className="history-filter-clear"
                type="button"
                onClick={() => {
                  setTicketSearch("");
                  setTicketStatusFilter("all");
                  setTicketSeverityFilter("all");
                }}
              >
                Reset
              </button>
            </div>

            <div className={`list-header ${ticketView === "cards" ? "hidden" : ""}`}>
              <span>ID</span>
              <span>Subject</span>
              <span>Agent</span>
              <span>Status</span>
            </div>

            <div className={`ticket-list ${ticketView === "cards" ? "cards-view" : "list-view"}`}>
              {ticketsLoading && filteredUiTickets.length === 0 && (
                <div className="ticket-empty">Loading tickets...</div>
              )}

              {!ticketsLoading && filteredUiTickets.length === 0 && (
                <div className="ticket-empty">
                  {uiTickets.length === 0
                    ? "No incidents reported yet."
                    : "No tickets match the selected filters."}
                </div>
              )}

              {filteredUiTickets.map((ticket) => {
                const selected = selectedTicketId === ticket.source.id;

                if (ticketView === "cards") {
                  return (
                    <div
                      key={ticket.source.id}
                      className={`ticket-card ${selected ? "selected" : ""}`}
                      onClick={() => openDetail(ticket)}
                    >
                      <div className="card-head">
                        <span className="t-id">{ticket.id}</span>
                        <span className={`t-status ${ticket.statusClass}`}>{ticket.statusLabel}</span>
                      </div>
                      <p className="card-title">{ticket.title}</p>
                      <p className="card-desc">{ticket.desc}</p>
                      <span className="card-agent">Assigned to {ticket.agent}</span>
                    </div>
                  );
                }

                return (
                  <div
                    key={ticket.source.id}
                    className={`ticket-row ${selected ? "selected" : ""}`}
                    onClick={() => openDetail(ticket)}
                  >
                    <span className="t-id">{ticket.id}</span>
                    <span className="t-subject">{ticket.title}</span>
                    <span className="t-agent">{ticket.agent}</span>
                    <span className={`t-status ${ticket.statusClass}`}>{ticket.statusLabel}</span>
                  </div>
                );
              })}
            </div>
          </section>

          <section className={`content-section report-section ${mainView !== "report" ? "hidden" : ""}`} id="reportSection">
            <div className="page-heading-row">
              <h1 className="page-title">Incident Reports</h1>
            </div>

            <div className="report-shell">
              <article className="report-card">
                <h2>Create Incident Report</h2>

                {reportError && <p className="inline-error">{reportError}</p>}

                <form className="report-form" onSubmit={handleSubmit}>
                  <div className="field-group">
                    <span className="field-label">Source</span>
                    <div className="source-options">
                      {SOURCE_OPTIONS.map((item) => (
                        <button
                          key={item.key}
                          className={`source-btn ${source.key === item.key ? "active" : ""}`}
                          type="button"
                          onClick={() => setSource(item)}
                        >
                          {item.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="field-group issue-group">
                    <span className="field-label">Describe the issue</span>
                    <div className="problem-composer">
                      <textarea
                        className="problem-input"
                        id="problemInput"
                        placeholder="Describe the incident with as much technical context as possible..."
                        value={description}
                        onChange={(event) => {
                          setDescription(event.target.value);
                          setInputInvalid(false);
                        }}
                        onBlur={handleDescriptionBlur}
                      />

                      <div className="composer-tools">
                        <div className="tool-stack">
                          <label className="clip-only-btn" htmlFor="incidentFile" title="Attach file" aria-label="Attach file">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 115.66 5.66L9.41 17.41a2 2 0 01-2.83-2.83l8.49-8.48" />
                            </svg>
                          </label>
                          <button
                            className={`clip-only-btn ${micHighlight ? "active" : ""}`}
                            type="button"
                            title="Voice input"
                            aria-label="Voice input"
                            onClick={() => setMicHighlight((prev) => !prev)}
                          >
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z" />
                              <path d="M19 10v2a7 7 0 01-14 0v-2" />
                              <line x1="12" y1="19" x2="12" y2="23" />
                              <line x1="8" y1="23" x2="16" y2="23" />
                            </svg>
                          </button>
                        </div>

                        <span className="file-note">{fileName}</span>
                      </div>

                      <p className="problem-context">{source.context}</p>

                      <input
                        type="file"
                        id="incidentFile"
                        hidden
                        ref={fileInputRef}
                        onChange={onFileChange}
                        accept=".log,.txt,.csv,.json,.out,.err,image/*"
                      />
                    </div>
                  </div>

                  {inputInvalid && (
                    <p className="inline-warning">
                      Input no reconocido como reporte válido. Ajusta el contexto técnico antes de enviar.
                    </p>
                  )}

                  <button className="submit-btn" type="submit" disabled={submitDisabled}>
                    {submitLoading ? "Submitting..." : validating ? "Validating..." : "Submit Report"}
                  </button>
                </form>
              </article>

              <article className="voice-card">
                <span className="voice-eyebrow">Voice Assistant</span>
                <div className="voice-center">
                  <button
                    className={`voice-orb ${voiceActive ? "active" : ""}`}
                    type="button"
                    aria-label="Tap to talk"
                    onClick={toggleVoiceSession}
                  >
                    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z" />
                      <path d="M19 10v2a7 7 0 01-14 0v-2" />
                      <line x1="12" y1="19" x2="12" y2="23" />
                      <line x1="8" y1="23" x2="16" y2="23" />
                    </svg>
                  </button>

                  <div className="voice-center-info">
                    <span className="voice-title">Speak the incident</span>
                    <span className="voice-tap">{voiceStatus === "idle" ? "Tap to talk" : `${voiceStatus}...`} · EN / ES</span>
                  </div>

                  <div className="voice-actions">
                    <button
                      className={`voice-btn ${voiceActive ? "active" : ""}`}
                      type="button"
                      aria-label="Switch language"
                      onClick={toggleVoiceLang}
                    >
                      <svg className="lang-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M4 5h8" />
                        <path d="M8 3v2a9 9 0 0 1-9 9" />
                        <path d="M6 11l4 4" />
                        <path d="M12 20l4-9 4 9" />
                        <path d="M13 18h6" />
                      </svg>
                      <span>{VOICE_LANG[voiceLang].label}</span>
                    </button>
                  </div>
                </div>

                <div className="voice-log">
                  <div className="voice-line">
                    <strong>Heard:</strong> {voiceHeard}
                  </div>
                  <div className="voice-line">
                    <strong>Agent:</strong> {voiceAgent}
                  </div>
                </div>
              </article>

              <article className={`agent-panel ${incidentData ? "active" : ""}`}>
                <h2>Agent Response</h2>
                <div className="response-box response-box-scroll">
                  {!incidentData && !isPolling && (
                    <div className="response-placeholder">
                      <h3>Waiting for input</h3>
                      <p>Submit a report or use the voice assistant - the agent response will appear here.</p>
                    </div>
                  )}

                  {isPolling && (
                    <div className="response-placeholder">
                      <h3>Analyzing incident</h3>
                      <p>Agent is extracting entities and determining severity.</p>
                    </div>
                  )}

                  {incidentData?.status === "error" && (
                    <div className="response-content">
                      <h3 className="response-title">Error during analysis</h3>
                      <p className="response-text">{incidentData.error || "Something went wrong"}</p>
                    </div>
                  )}

                  {incidentData?.result && (
                    <div className="response-content">
                      {isEscalated && (
                        <div className={`escalation ${isVague ? "critical" : "pending"}`}>
                          <h3>{isVague ? "Description not recognized" : "Escalated - Human Review Required"}</h3>
                          <p>
                            {isVague
                              ? "The agent could not identify a valid technical incident from this description."
                              : `Agent confidence is ${Math.round((incidentData.result.confidence_score || 0) * 100)}% (threshold: 70%).`}
                          </p>
                        </div>
                      )}

                      <div className="response-grid">
                        <div>
                          <span className="meta-label">Severity</span>
                          <p>{incidentData.result.severity}</p>
                        </div>
                        <div>
                          <span className="meta-label">Incident Type</span>
                          <p>{incidentData.result.incident_type}</p>
                        </div>
                        <div>
                          <span className="meta-label">Plugin</span>
                          <p>{incidentData.result.affected_plugin || "N/A"}</p>
                        </div>
                        <div>
                          <span className="meta-label">Assigned Team</span>
                          <p>{incidentData.result.assigned_team || "N/A"}</p>
                        </div>
                      </div>

                      <div className="response-split">
                        <div className="response-block">
                          <span className="meta-label">Summary</span>
                          <p className="response-text">{incidentData.result.summary}</p>
                        </div>

                        <div className="response-block">
                          <span className="meta-label">Suggested Actions</span>
                          {incidentData.result.suggested_actions?.length ? (
                            <ul className="response-list">
                              {incidentData.result.suggested_actions.map((action) => (
                                <li key={action}>{action}</li>
                              ))}
                            </ul>
                          ) : (
                            <p className="response-text">No suggested actions were generated.</p>
                          )}
                        </div>
                      </div>

                      <div className="ticket-chip-row">
                        <span className="ticket-chip-label">Ticket</span>
                        {isCreatingTicket ? (
                          <span className="ticket-chip">Creating issue...</span>
                        ) : incidentData.ticket ? (
                          incidentData.ticket.ticket_id.startsWith("http") ? (
                            <a
                              href={incidentData.ticket.ticket_id}
                              target="_blank"
                              rel="noreferrer"
                              className="ticket-link"
                            >
                              Open issue
                            </a>
                          ) : (
                            <span className="ticket-chip">{incidentData.ticket.ticket_id}</span>
                          )
                        ) : (
                          <span className="ticket-chip">Pending creation</span>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </article>
            </div>
          </section>

          <aside className={`detail-panel ${selectedTicket ? "open" : ""}`}>
            <div className="detail-header">
              <span className="t-id">{selectedTicket ? (selectedTicket.github_ticket_number ? `#${selectedTicket.github_ticket_number}` : `#${selectedTicket.id.slice(-4)}`) : "#ID-000"}</span>
              <button className="close-btn" type="button" onClick={closeDetail}>
                X
              </button>
            </div>

            <div className="chrome-card">
              <h2 className="detail-title">
                {selectedTicket
                  ? `${selectedTicket.incident_type || "unknown_incident"} - ${selectedTicket.affected_plugin || "unknown-plugin"}`
                  : "Subject Title"}
              </h2>
              <p className="detail-desc">
                {selectedTicket?.summary || selectedTicket?.original_description || "No description available."}
              </p>
            </div>

            <div className="meta-info">
              <div className="meta-item">
                <span>Status</span>
                <span>{selectedTicket?.status || "Pending"}</span>
              </div>
              <div className="meta-item">
                <span>Assigned Agent</span>
                <span>{selectedTicket?.jira_ticket_key || "AI-Core"}</span>
              </div>
              <div className="meta-item">
                <span>Priority</span>
                <span>{selectedTicket?.severity || "P3"}</span>
              </div>
              <div className="meta-item">
                <span>Last Updated</span>
                <span>{selectedTicket?.resolved_at || selectedTicket?.created_at || "-"}</span>
              </div>
            </div>

            <button className="detail-action" type="button" onClick={closeDetail}>
              Take Action
            </button>
          </aside>
        </div>
      </div>
    </div>
  );
}
