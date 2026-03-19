"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import EmptyState from "@/components/empty-state";
import { ShieldCheckIcon } from "@/components/icons";

const STATUS_OPTIONS = [
  { value: "leaving", label: "Leaving now", emoji: "🚗" },
  { value: "reached", label: "Reached safely", emoji: "✅" },
  { value: "check_in", label: "Quick check-in", emoji: "👋" },
];

const STATUS_COLORS = {
  leaving: "text-yellow-400",
  reached: "text-emerald-400",
  check_in: "text-sky-400",
};

function timeAgo(dateStr) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function CheckInButton({ option, onSend, disabled }) {
  return (
    <button
      disabled={disabled}
      onClick={() => onSend(option.value)}
      className="flex flex-1 flex-col items-center gap-2 rounded-xl border border-zinc-800 bg-zinc-900 p-4 transition-colors hover:border-purple-500/40 hover:bg-zinc-800 disabled:opacity-50"
    >
      <span className="text-2xl">{option.emoji}</span>
      <span className="text-sm font-medium text-white">{option.label}</span>
    </button>
  );
}

function HistoryItem({ event }) {
  const opt = STATUS_OPTIONS.find((o) => o.value === event.status);
  return (
    <div className="flex items-start gap-3 border-b border-zinc-800/60 py-3 last:border-0">
      <span className="mt-0.5 text-lg">{opt?.emoji || "📍"}</span>
      <div className="flex-1">
        <p className="text-sm font-medium text-white">
          <span className={STATUS_COLORS[event.status] || "text-white"}>
            {opt?.label || event.status}
          </span>
          <span className="ml-2 font-normal text-zinc-500">
            — {event.triggered_by}
          </span>
        </p>
        {event.message && (
          <p className="mt-0.5 text-sm text-zinc-400">{event.message}</p>
        )}
        <p className="mt-0.5 text-xs text-zinc-600">{timeAgo(event.created_at)}</p>
      </div>
    </div>
  );
}

export default function SafeCheckPage() {
  const [history, setHistory] = useState([]);
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [loaded, setLoaded] = useState(false);

  const fetchHistory = useCallback(async () => {
    try {
      const res = await apiFetch("/safety/history/");
      if (res.ok) setHistory(await res.json());
    } catch {
      /* ignore */
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const handleSend = async (status) => {
    setSending(true);
    try {
      const res = await apiFetch("/safety/check/", {
        method: "POST",
        body: JSON.stringify({ status, message: message.trim() }),
      });
      if (res.ok) {
        const event = await res.json();
        setHistory((prev) => [event, ...prev]);
        setMessage("");
      }
    } catch {
      /* ignore */
    } finally {
      setSending(false);
    }
  };

  if (!loaded) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-purple-500 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold">Safe Check</h1>
        <p className="mt-1 text-sm text-zinc-400">
          Quick check-ins with your partner
        </p>
      </div>

      {/* Action buttons */}
      <div className="flex gap-3">
        {STATUS_OPTIONS.map((opt) => (
          <CheckInButton
            key={opt.value}
            option={opt}
            onSend={handleSend}
            disabled={sending}
          />
        ))}
      </div>

      {/* Optional message */}
      <input
        type="text"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="Add an optional message…"
        maxLength={300}
        className="rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm text-white placeholder-zinc-600 outline-none focus:border-purple-500/50"
      />

      {/* History */}
      {history.length > 0 ? (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 px-4">
          {history.map((ev) => (
            <HistoryItem key={ev.id} event={ev} />
          ))}
        </div>
      ) : (
        <EmptyState
          icon={<ShieldCheckIcon className="h-7 w-7" />}
          title="No check-ins yet"
          description="Tap one of the buttons above to send your first check-in."
        />
      )}
    </div>
  );
}
