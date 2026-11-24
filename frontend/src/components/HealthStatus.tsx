/**
 * DealForge Frontend — HealthStatus Component.
 *
 * Displays the backend API health in a live status badge.
 * Used in the Dashboard header as a real-time connectivity indicator.
 */

import { clsx } from "clsx";
import { AlertTriangle, CheckCircle, Loader2, XCircle } from "lucide-react";
import { useHealth } from "../hooks/useHealth";

export function HealthStatus() {
  const { data, isLoading, isError } = useHealth();

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 rounded-full bg-white/10 px-4 py-1.5 text-sm text-slate-300">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span>Connecting…</span>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="flex items-center gap-2 rounded-full bg-red-500/20 px-4 py-1.5 text-sm text-red-300 border border-red-500/30">
        <XCircle className="h-4 w-4" />
        <span>Backend unreachable</span>
      </div>
    );
  }

  const isOk = data.status === "ok";
  const isDegraded = data.status === "degraded";

  return (
    <div
      className={clsx(
        "flex items-center gap-2 rounded-full px-4 py-1.5 text-sm border transition-all",
        isOk && "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
        isDegraded && "bg-amber-500/20 text-amber-300 border-amber-500/30",
        !isOk && !isDegraded && "bg-red-500/20 text-red-300 border-red-500/30"
      )}
      title={`Uptime: ${data.uptime_seconds}s | v${data.version} | ${data.environment}`}
    >
      {isOk ? (
        <CheckCircle className="h-4 w-4" />
      ) : isDegraded ? (
        <AlertTriangle className="h-4 w-4" />
      ) : (
        <XCircle className="h-4 w-4" />
      )}
      <span className="font-medium capitalize">{data.status}</span>
      <span className="text-xs opacity-70">· v{data.version}</span>
    </div>
  );
}
