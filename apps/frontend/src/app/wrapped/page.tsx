"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

type Period = "day" | "week" | "month";

type WrappedResponse = {
  raw: {
    period: Period;
    period_days: number;
    total_incidents: number;
    most_failing_plugin: string;
    fastest_resolved_category: string;
    p1_hour_distribution: number[];
    peak_p1_hour: number;
    avg_resolution_time_per_category: Record<string, number>;
    total_hours_lost: number;
    estimated_cost_usd: number;
  };
  phrases: {
    team_summary: string;
    villain_plugin: string;
    villain_phrase: string;
    superpower_category: string;
    superpower_phrase: string;
    chaos_hour_phrase: string;
    downtime_cost_phrase: string;
    chef_recommendation: string;
  };
};

declare global {
  interface Window {
    jspdf?: { jsPDF: new (opts?: Record<string, unknown>) => any };
  }
}

function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${src}"]`) as HTMLScriptElement | null;
    if (existing) {
      if (existing.dataset.loaded === "true") {
        resolve();
        return;
      }
      existing.addEventListener("load", () => resolve(), { once: true });
      existing.addEventListener("error", () => reject(new Error(`Failed loading ${src}`)), { once: true });
      return;
    }

    const script = document.createElement("script");
    script.src = src;
    script.async = true;
    script.dataset.loaded = "false";
    script.onload = () => {
      script.dataset.loaded = "true";
      resolve();
    };
    script.onerror = () => reject(new Error(`Failed loading ${src}`));
    document.body.appendChild(script);
  });
}

function safePeriodLabel(period: Period): string {
  if (period === "day") return "day";
  if (period === "week") return "week";
  return "month";
}

export default function WrappedPage() {
  const [period, setPeriod] = useState<Period>("month");
  const [data, setData] = useState<WrappedResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isExporting, setIsExporting] = useState(false);

  useEffect(() => {
    const run = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`/api/reports/summary?period=${period}`, { cache: "no-store" });
        if (!res.ok) {
          throw new Error("Could not load wrapped summary.");
        }
        const payload = (await res.json()) as WrappedResponse;
        setData(payload);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not load wrapped summary.");
        setData(null);
      } finally {
        setLoading(false);
      }
    };
    run();
  }, [period]);

  const heatmapMax = useMemo(() => {
    if (!data) return 1;
    return Math.max(1, ...data.raw.p1_hour_distribution);
  }, [data]);

  const shareText = useMemo(() => {
    if (!data) return "";
    return [
      `SRE Wrapped — ${safePeriodLabel(period)}`,
      `Villain: ${data.phrases.villain_plugin} | Superpower: ${data.phrases.superpower_category} | Cost: $${data.raw.estimated_cost_usd.toFixed(2)}`,
      `Chef says: ${data.phrases.chef_recommendation}`,
    ].join("\n");
  }, [data, period]);

  const onDownloadPdf = async () => {
    if (!data) return;
    setIsExporting(true);
    try {
      await loadScript("https://cdn.jsdelivr.net/npm/jspdf@2.5.1/dist/jspdf.umd.min.js");

      if (!window.jspdf?.jsPDF) {
        throw new Error("PDF tools unavailable");
      }

      const JsPdfCtor = window.jspdf.jsPDF;
      const pdf = new JsPdfCtor({ orientation: "portrait", unit: "pt", format: "a4" });
      const pageWidth = pdf.internal.pageSize.getWidth();
      const pageHeight = pdf.internal.pageSize.getHeight();

      const marginX = 46;
      const contentWidth = pageWidth - marginX * 2;
      let y = 48;

      const ensureSpace = (neededHeight: number) => {
        if (y + neededHeight > pageHeight - 46) {
          pdf.addPage();
          y = 48;
        }
      };

      const drawHeading = (text: string) => {
        ensureSpace(28);
        pdf.setFont("helvetica", "bold");
        pdf.setFontSize(18);
        pdf.setTextColor(15, 23, 42);
        pdf.text(text, marginX, y);
        y += 22;
      };

      const drawParagraph = (text: string, size = 11) => {
        if (!text) return;
        pdf.setFont("helvetica", "normal");
        pdf.setFontSize(size);
        pdf.setTextColor(51, 65, 85);
        const lines = pdf.splitTextToSize(text, contentWidth);
        const blockHeight = lines.length * (size + 3) + 4;
        ensureSpace(blockHeight);
        pdf.text(lines, marginX, y);
        y += blockHeight;
      };

      const drawStatCard = (label: string, value: string, x: number, width: number) => {
        const cardHeight = 64;
        ensureSpace(cardHeight + 12);
        pdf.setFillColor(248, 250, 252);
        pdf.setDrawColor(226, 232, 240);
        pdf.roundedRect(x, y, width, cardHeight, 8, 8, "FD");
        pdf.setFont("helvetica", "normal");
        pdf.setFontSize(9);
        pdf.setTextColor(100, 116, 139);
        pdf.text(label.toUpperCase(), x + 10, y + 16);
        pdf.setFont("helvetica", "bold");
        pdf.setFontSize(15);
        pdf.setTextColor(15, 23, 42);
        const valueLines = pdf.splitTextToSize(value, width - 20);
        pdf.text(valueLines, x + 10, y + 38);
      };

      drawHeading(`SRE Wrapped (${safePeriodLabel(period)})`);
      drawParagraph(`Generated from incident data for the last ${data.raw.period_days} day(s).`);

      const colGap = 10;
      const colWidth = (contentWidth - colGap) / 2;
      drawStatCard("Total incidents", `${data.raw.total_incidents}`, marginX, colWidth);
      drawStatCard("Estimated cost", `$${data.raw.estimated_cost_usd.toFixed(2)}`, marginX + colWidth + colGap, colWidth);
      y += 74;
      drawStatCard("Most failing plugin", data.phrases.villain_plugin, marginX, colWidth);
      drawStatCard("Fastest category", data.phrases.superpower_category, marginX + colWidth + colGap, colWidth);
      y += 84;

      drawHeading("Narrative Highlights");
      drawParagraph(data.phrases.team_summary);
      drawParagraph(data.phrases.villain_phrase);
      drawParagraph(data.phrases.superpower_phrase);
      drawParagraph(data.phrases.chaos_hour_phrase);
      drawParagraph(data.phrases.downtime_cost_phrase);
      drawParagraph(`Chef recommendation: ${data.phrases.chef_recommendation}`);

      ensureSpace(220);
      drawHeading("P1 Hour Distribution");
      const chartX = marginX;
      const chartY = y + 12;
      const chartWidth = contentWidth;
      const chartHeight = 140;
      const maxP1 = Math.max(1, ...data.raw.p1_hour_distribution);
      const barGap = 2;
      const barWidth = (chartWidth - barGap * 23) / 24;

      pdf.setDrawColor(203, 213, 225);
      pdf.line(chartX, chartY + chartHeight, chartX + chartWidth, chartY + chartHeight);
      pdf.setFillColor(37, 99, 235);

      data.raw.p1_hour_distribution.forEach((count, hour) => {
        const h = (count / maxP1) * chartHeight;
        const x = chartX + hour * (barWidth + barGap);
        const yBase = chartY + chartHeight - h;
        pdf.rect(x, yBase, barWidth, h, "F");
      });

      pdf.setFont("helvetica", "normal");
      pdf.setFontSize(8);
      pdf.setTextColor(100, 116, 139);
      for (let hour = 0; hour < 24; hour += 2) {
        const x = chartX + hour * (barWidth + barGap);
        pdf.text(String(hour), x, chartY + chartHeight + 12);
      }
      y = chartY + chartHeight + 26;

      const avgPairs = Object.entries(data.raw.avg_resolution_time_per_category)
        .sort((a, b) => a[1] - b[1])
        .slice(0, 8);
      const maxAvg = Math.max(1, ...avgPairs.map(([, value]) => value), 1);

      ensureSpace(220);
      drawHeading("Average Resolution Time by Category (hours)");
      avgPairs.forEach(([category, value]) => {
        ensureSpace(24);
        pdf.setFont("helvetica", "normal");
        pdf.setFontSize(10);
        pdf.setTextColor(51, 65, 85);
        const categoryLabel = `${category} (${value.toFixed(2)}h)`;
        pdf.text(pdf.splitTextToSize(categoryLabel, 190), marginX, y + 9);

        const barX = marginX + 200;
        const barY = y;
        const barMaxWidth = contentWidth - 210;
        const barW = Math.max(10, (value / maxAvg) * barMaxWidth);
        pdf.setFillColor(16, 185, 129);
        pdf.roundedRect(barX, barY, barW, 10, 4, 4, "F");
        y += 20;
      });

      ensureSpace(70);
      y += 8;
      pdf.setDrawColor(226, 232, 240);
      pdf.line(marginX, y, marginX + contentWidth, y);
      y += 16;
      pdf.setFont("helvetica", "bold");
      pdf.setFontSize(11);
      pdf.setTextColor(15, 23, 42);
      pdf.text("Raw Totals", marginX, y);
      y += 14;
      pdf.setFont("helvetica", "normal");
      pdf.setFontSize(10);
      pdf.setTextColor(71, 85, 105);
      pdf.text(`Peak P1 hour: ${data.raw.peak_p1_hour}:00`, marginX, y);
      y += 14;
      pdf.text(`Total hours lost: ${data.raw.total_hours_lost.toFixed(2)}`, marginX, y);
      y += 14;
      pdf.text(`Fastest resolved category: ${data.raw.fastest_resolved_category}`, marginX, y);

      pdf.save(`sre-wrapped-${period}.pdf`);
    } finally {
      setIsExporting(false);
    }
  };

  if (loading) {
    return (
      <main className="min-h-screen grid place-items-center bg-slate-50 text-slate-900 font-sans">
        <p className="text-2xl font-semibold">Loading SRE Wrapped...</p>
      </main>
    );
  }

  if (error || !data) {
    return (
      <main className="min-h-screen grid place-items-center bg-slate-50 text-slate-900 font-sans px-6 text-center">
        <div className="space-y-4">
          <p className="text-2xl font-semibold">Could not load Wrapped summary</p>
          <p className="text-slate-600">{error || "Unknown error"}</p>
          <Link href="/" className="inline-flex rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold">
            Back to Home
          </Link>
        </div>
      </main>
    );
  }

  const avgCategories = Object.entries(data.raw.avg_resolution_time_per_category)
    .sort((a, b) => a[1] - b[1])
    .slice(0, 8);
  const avgMax = Math.max(1, ...avgCategories.map(([, value]) => value));

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900 p-6 md:p-12" style={{ fontFamily: "system-ui" }}>
      <section className="max-w-6xl mx-auto space-y-8">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight">SRE Wrapped</h1>
            <p className="text-slate-500 mt-1">All your incident highlights in one clean view.</p>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/" className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800">
              Back to Report
            </Link>
            <button
              type="button"
              onClick={onDownloadPdf}
              className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700"
            >
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 3v12" />
                <path d="M8 11l4 4 4-4" />
                <path d="M4 21h16" />
              </svg>
              {isExporting ? "Building PDF..." : "Download PDF"}
            </button>
          </div>
        </header>

        <div className="flex items-center gap-2">
          <label htmlFor="period" className="text-sm text-slate-600 font-semibold">Period</label>
          <select
            id="period"
            value={period}
            onChange={(event) => {
              setPeriod(event.target.value as Period);
            }}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold outline-none"
          >
            <option value="day">Last day</option>
            <option value="week">Last week</option>
            <option value="month">Last month</option>
          </select>
        </div>

        <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm text-slate-500">Total incidents</p>
            <p className="text-[clamp(2.2rem,7vw,4rem)] font-extrabold leading-none mt-2">{data.raw.total_incidents}</p>
          </article>
          <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm text-slate-500">Most failing plugin</p>
            <p className="text-xl md:text-2xl font-extrabold mt-2 break-words">{data.phrases.villain_plugin}</p>
          </article>
          <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm text-slate-500">Fastest category</p>
            <p className="text-xl md:text-2xl font-extrabold mt-2 break-words">{data.phrases.superpower_category}</p>
          </article>
          <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm text-slate-500">Estimated cost</p>
            <p className="text-[clamp(2.1rem,6vw,3.6rem)] font-extrabold leading-none mt-2 text-orange-600">
              ${data.raw.estimated_cost_usd.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </p>
          </article>
        </section>

        <section className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-bold">Team Summary</h2>
            <p className="text-slate-700 mt-2">{data.phrases.team_summary}</p>
            <p className="text-slate-700 mt-3">{data.phrases.villain_phrase}</p>
            <p className="text-slate-700 mt-3">{data.phrases.superpower_phrase}</p>
            <p className="text-slate-700 mt-3">{data.phrases.downtime_cost_phrase}</p>
          </article>

          <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-bold">Chef Recommendation</h2>
            <p className="text-slate-700 mt-2 leading-relaxed">{data.phrases.chef_recommendation}</p>
            <div className="mt-4 rounded-lg bg-slate-100 p-3 text-sm text-slate-700">
              <p className="font-semibold">Share preview</p>
              <p className="mt-2 whitespace-pre-line">{shareText}</p>
            </div>
          </article>
        </section>

        <section className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-bold">P1 Chaos Hour Heatmap</h2>
            <p className="text-slate-600 mt-1">{data.phrases.chaos_hour_phrase}</p>
            <div className="mt-5 grid grid-cols-12 md:grid-cols-24 gap-2 items-end h-52">
              {data.raw.p1_hour_distribution.map((count, hour) => {
                const ratio = count / heatmapMax;
                const minHeight = 10;
                const dynamicHeight = minHeight + Math.round(ratio * 160);
                return (
                  <div key={hour} className="flex flex-col items-center gap-1">
                    <div
                      className="w-3 md:w-4 rounded-sm bg-blue-600"
                      style={{ height: `${dynamicHeight}px`, opacity: 0.35 + ratio * 0.65 }}
                      title={`Hour ${hour}: ${count} incidents`}
                    />
                    <span className="text-[10px] md:text-xs text-slate-500">{hour}</span>
                  </div>
                );
              })}
            </div>
          </article>

          <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-bold">Avg Resolution Time by Category</h2>
            <p className="text-slate-600 mt-1">Hours to resolution in this {safePeriodLabel(period)}.</p>
            <div className="mt-5 space-y-3">
              {avgCategories.length === 0 && (
                <p className="text-slate-500">No resolved incidents yet in this period.</p>
              )}
              {avgCategories.map(([category, value]) => {
                const width = Math.max(8, Math.round((value / avgMax) * 100));
                return (
                  <div key={category}>
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium text-slate-700 truncate mr-3">{category}</span>
                      <span className="text-slate-500">{value.toFixed(2)}h</span>
                    </div>
                    <div className="mt-1 h-2 rounded-full bg-slate-200">
                      <div className="h-2 rounded-full bg-emerald-600" style={{ width: `${width}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </article>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-bold">Raw Stats</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mt-4">
            <div className="rounded-lg bg-slate-100 p-3">
              <p className="text-xs uppercase tracking-wide text-slate-500">Period days</p>
              <p className="text-2xl font-bold mt-1">{data.raw.period_days}</p>
            </div>
            <div className="rounded-lg bg-slate-100 p-3">
              <p className="text-xs uppercase tracking-wide text-slate-500">Peak P1 hour</p>
              <p className="text-2xl font-bold mt-1">{data.raw.peak_p1_hour}:00</p>
            </div>
            <div className="rounded-lg bg-slate-100 p-3">
              <p className="text-xs uppercase tracking-wide text-slate-500">Total hours lost</p>
              <p className="text-2xl font-bold mt-1">{data.raw.total_hours_lost.toFixed(2)}</p>
            </div>
            <div className="rounded-lg bg-slate-100 p-3">
              <p className="text-xs uppercase tracking-wide text-slate-500">Fastest resolved category</p>
              <p className="text-sm font-bold mt-2 break-words">{data.raw.fastest_resolved_category}</p>
            </div>
          </div>
        </section>
      </section>
    </main>
  );
}
