"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

type Ticket = {
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

function formatDate(value: string | null): string {
  if (!value) {
    return "";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  const datePart = new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);

  const timePart = new Intl.DateTimeFormat("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  }).format(date);

  return `${datePart} at ${timePart}`;
}

function severityBadgeClass(severity: string | null): string {
  const normalized = (severity || "P3").toUpperCase();
  if (normalized === "P1") return "bg-red-600 text-white";
  if (normalized === "P2") return "bg-orange-500 text-white";
  return "bg-yellow-500 text-white";
}

function statusBadgeClass(status: string | null): string {
  const normalized = (status || "open").toLowerCase();
  if (normalized === "resolved" || normalized === "closed") return "bg-emerald-600 text-white";
  return "bg-blue-600 text-white";
}

export default function HistoryPage() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTickets = async () => {
    try {
      const res = await fetch("/api/tickets", { cache: "no-store" });
      if (!res.ok) {
        throw new Error("Could not load tickets. Try again.");
      }
      const data = (await res.json()) as Ticket[];
      setTickets(Array.isArray(data) ? data : []);
      setError(null);
    } catch {
      setError("Could not load tickets. Try again.");
      setTickets([]);
    }
  };

  const stats = useMemo(() => {
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

  useEffect(() => {
    setLoading(true);
    fetchTickets().finally(() => setLoading(false));

    const intervalId = setInterval(() => {
      fetchTickets();
    }, 15000);

    return () => {
      clearInterval(intervalId);
    };
  }, []);

  return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-slate-50 p-6 md:p-12">
      <div className="max-w-5xl mx-auto space-y-8">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 dark:text-white">Incident Dashboard</h1>
            <p className="text-slate-500 dark:text-slate-400 mt-1">Live status of all incident tickets.</p>
          </div>
          <Link href="/" className="text-sm font-semibold text-blue-600 hover:text-blue-700">
            Back to Report
          </Link>
        </header>

        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow p-5 border border-slate-100 dark:border-slate-700">
            <p className="text-sm text-slate-500 dark:text-slate-400">Total tickets</p>
            <p className="text-2xl font-bold mt-1">{stats.total}</p>
          </div>
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow p-5 border border-slate-100 dark:border-slate-700">
            <p className="text-sm text-slate-500 dark:text-slate-400">Open tickets</p>
            <p className="text-2xl font-bold mt-1 text-blue-600 dark:text-blue-400">{stats.open}</p>
          </div>
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow p-5 border border-slate-100 dark:border-slate-700">
            <p className="text-sm text-slate-500 dark:text-slate-400">Resolved tickets</p>
            <p className="text-2xl font-bold mt-1 text-emerald-600 dark:text-emerald-400">{stats.resolved}</p>
          </div>
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow p-5 border border-slate-100 dark:border-slate-700">
            <p className="text-sm text-slate-500 dark:text-slate-400">Most affected plugin</p>
            <p className="text-lg font-bold mt-1 truncate">{stats.mostAffectedPlugin}</p>
          </div>
        </section>

        <section className="space-y-4">
          {error && (
            <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg p-4 text-red-700 dark:text-red-300 font-medium">
              Could not load tickets. Try again.
            </div>
          )}

          {!loading && !error && tickets.length === 0 && (
            <div className="bg-white dark:bg-slate-800 rounded-xl shadow p-6 text-slate-600 dark:text-slate-300">
              No incidents reported yet.
            </div>
          )}

          {tickets.map((ticket) => {
            const statusLabel = (ticket.status || "open").toLowerCase() === "resolved" || (ticket.status || "open").toLowerCase() === "closed" ? "Resolved" : "Open";
            const summary = (ticket.summary || "No summary available").slice(0, 120);
            const titleIncidentType = ticket.incident_type || "unknown_incident";
            const titlePlugin = ticket.affected_plugin || "unknown-plugin";

            return (
              <article key={ticket.id} className="bg-white dark:bg-slate-800 rounded-xl shadow-lg p-6 border border-slate-100 dark:border-slate-700">
                <div className="flex flex-wrap items-center gap-2 mb-3">
                  <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${severityBadgeClass(ticket.severity)}`}>
                    {(ticket.severity || "P3").toUpperCase()}
                  </span>
                  <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${statusBadgeClass(ticket.status)}`}>
                    {statusLabel}
                  </span>
                </div>

                <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                  {titleIncidentType} - {titlePlugin}
                </h2>

                <p className="mt-2 text-slate-600 dark:text-slate-300">{summary}</p>

                <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">Created {formatDate(ticket.created_at)}</p>
                {ticket.resolved_at && (
                  <p className="text-sm text-emerald-600 dark:text-emerald-400 font-medium">
                    Resolved on {formatDate(ticket.resolved_at)}
                  </p>
                )}

                <div className="mt-4 flex flex-wrap gap-3">
                  {ticket.github_ticket_url && (
                    <a
                      href={ticket.github_ticket_url}
                      target="_blank"
                      rel="noreferrer"
                      className="px-4 py-2 rounded-lg text-sm font-semibold bg-slate-900 text-white hover:bg-slate-800"
                    >
                      View on GitHub
                    </a>
                  )}
                  {ticket.jira_ticket_url && (
                    <a
                      href={ticket.jira_ticket_url}
                      target="_blank"
                      rel="noreferrer"
                      className="px-4 py-2 rounded-lg text-sm font-semibold bg-blue-700 text-white hover:bg-blue-800"
                    >
                      View on Jira
                    </a>
                  )}
                </div>
              </article>
            );
          })}
        </section>
      </div>
    </main>
  );
}
