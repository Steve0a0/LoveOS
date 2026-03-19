"use client";

import { apiFetch } from "@/lib/api";
import { useEffect, useState } from "react";
import EmptyState from "@/components/empty-state";
import { CalendarIcon, PlusIcon } from "@/components/icons";

const DATE_TYPES = [
  { value: "anniversary", label: "Anniversary" },
  { value: "birthday", label: "Birthday" },
  { value: "visit", label: "Visit" },
  { value: "custom", label: "Custom" },
];

const TYPE_LABELS = Object.fromEntries(
  DATE_TYPES.map((t) => [t.value, t.label])
);

const TYPE_COLORS = {
  anniversary: "text-purple-400 bg-purple-950",
  birthday: "text-amber-400 bg-amber-950",
  visit: "text-sky-400 bg-sky-950",
  custom: "text-zinc-400 bg-zinc-800",
};

function daysUntil(dateStr) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(dateStr + "T00:00:00");
  const diff = Math.ceil((target - today) / (1000 * 60 * 60 * 24));
  return diff;
}

function countdownText(days) {
  if (days < 0) return `${Math.abs(days)} days ago`;
  if (days === 0) return "Today!";
  if (days === 1) return "Tomorrow";
  return `In ${days} days`;
}

// ---------------------------------------------------------------------------
// Date Form (used for both create and edit)
// ---------------------------------------------------------------------------
function DateForm({ initial, onSubmit, onCancel, submitLabel }) {
  const [title, setTitle] = useState(initial?.title || "");
  const [date, setDate] = useState(initial?.date || "");
  const [dateType, setDateType] = useState(initial?.date_type || "custom");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    if (!title.trim() || !date) return;
    setSubmitting(true);
    setError("");
    try {
      await onSubmit({ title, date, date_type: dateType });
    } catch (err) {
      setError(err.message);
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 space-y-3"
    >
      <input
        type="text"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Title (e.g. Our Anniversary)"
        className="w-full bg-transparent text-white text-sm placeholder-zinc-500 outline-none"
      />
      <div className="flex flex-wrap gap-3">
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="rounded-md border border-zinc-700 bg-zinc-800 px-2 py-1 text-xs text-zinc-300"
        />
        <select
          value={dateType}
          onChange={(e) => setDateType(e.target.value)}
          className="rounded-md border border-zinc-700 bg-zinc-800 px-2 py-1 text-xs text-zinc-300"
        >
          {DATE_TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
      </div>
      <div className="flex items-center gap-2 justify-end">
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md px-3 py-1.5 text-xs text-zinc-400 hover:text-white"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={submitting || !title.trim() || !date}
          className="rounded-md bg-white px-3 py-1.5 text-xs font-medium text-black hover:bg-zinc-200 disabled:opacity-50"
        >
          {submitting ? "Saving…" : submitLabel || "Save"}
        </button>
      </div>
      {error && <p className="text-xs text-red-400">{error}</p>}
    </form>
  );
}

// ---------------------------------------------------------------------------
// Date Card
// ---------------------------------------------------------------------------
function DateCard({ item, onUpdate, onDelete }) {
  const [editing, setEditing] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const days = daysUntil(item.date);
  const colors = TYPE_COLORS[item.date_type] || TYPE_COLORS.custom;

  async function handleEdit(data) {
    const res = await apiFetch(`/dates/${item.id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const d = await res.json();
      throw new Error(d.detail || "Failed to update.");
    }
    onUpdate(await res.json());
    setEditing(false);
  }

  async function handleDelete() {
    setDeleting(true);
    const res = await apiFetch(`/dates/${item.id}/`, { method: "DELETE" });
    if (res.ok) onDelete(item.id);
    else setDeleting(false);
  }

  if (editing) {
    return (
      <DateForm
        initial={item}
        onSubmit={handleEdit}
        onCancel={() => setEditing(false)}
        submitLabel="Update"
      />
    );
  }

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 flex items-start gap-4">
      {/* Countdown pill */}
      <div className="flex flex-col items-center shrink-0 min-w-[56px]">
        <span className="text-2xl font-bold text-white">
          {days >= 0 ? days : "—"}
        </span>
        <span className="text-[10px] text-zinc-500">
          {days >= 0 ? (days === 1 ? "day" : "days") : "passed"}
        </span>
      </div>

      {/* Content */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium text-white truncate">{item.title}</p>
          <span
            className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] ${colors}`}
          >
            {TYPE_LABELS[item.date_type]}
          </span>
        </div>
        <p className="mt-0.5 text-xs text-zinc-500">
          {new Date(item.date + "T00:00:00").toLocaleDateString(undefined, {
            weekday: "short",
            year: "numeric",
            month: "short",
            day: "numeric",
          })}{" "}
          · {countdownText(days)}
        </p>
        <p className="mt-1 text-[10px] text-zinc-600">
          Added by {item.created_by_name}
        </p>
      </div>

      {/* Actions */}
      <div className="flex shrink-0 gap-1">
        <button
          onClick={() => setEditing(true)}
          className="rounded px-1.5 py-1 text-xs text-zinc-600 hover:text-zinc-300"
        >
          Edit
        </button>
        <button
          onClick={handleDelete}
          disabled={deleting}
          className="rounded px-1.5 py-1 text-xs text-zinc-600 hover:text-red-400"
        >
          {deleting ? "…" : "Delete"}
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function DatesPage() {
  const [dates, setDates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [composing, setComposing] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const res = await apiFetch("/dates/");
        if (res.ok) setDates(await res.json());
      } catch {
        /* ignore */
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function handleCreate(data) {
    const res = await apiFetch("/dates/", {
      method: "POST",
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const d = await res.json();
      throw new Error(d.detail || "Failed to create date.");
    }
    const created = await res.json();
    setDates((prev) =>
      [...prev, created].sort(
        (a, b) => new Date(a.date) - new Date(b.date)
      )
    );
    setComposing(false);
  }

  function handleUpdate(updated) {
    setDates((prev) =>
      prev
        .map((d) => (d.id === updated.id ? updated : d))
        .sort((a, b) => new Date(a.date) - new Date(b.date))
    );
  }

  function handleDelete(id) {
    setDates((prev) => prev.filter((d) => d.id !== id));
  }

  // Split into upcoming and past
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const upcoming = dates.filter(
    (d) => new Date(d.date + "T00:00:00") >= today
  );
  const past = dates.filter(
    (d) => new Date(d.date + "T00:00:00") < today
  );

  return (
    <div className="flex flex-1 flex-col space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold">Important Dates</h1>
          <p className="mt-1 text-sm text-zinc-400">
            Anniversaries, birthdays, and milestones
          </p>
        </div>
        {!composing && dates.length > 0 && (
          <button
            onClick={() => setComposing(true)}
            className="flex items-center gap-1.5 rounded-md bg-white px-3 py-1.5 text-xs font-medium text-black hover:bg-zinc-200 shrink-0 whitespace-nowrap"
          >
            <PlusIcon className="h-3.5 w-3.5" />
            Add date
          </button>
        )}
      </div>

      {/* Composer */}
      {composing && (
        <DateForm
          onSubmit={handleCreate}
          onCancel={() => setComposing(false)}
          submitLabel="Add date"
        />
      )}

      {/* Loading */}
      {loading ? (
        <p className="text-sm text-zinc-500">Loading dates…</p>
      ) : dates.length === 0 && !composing ? (
        <EmptyState
          icon={<CalendarIcon className="h-7 w-7" />}
          title="Add your first important date"
          description="Never miss an anniversary, birthday, or milestone again. We'll show you the countdown."
          actionLabel="Add a date"
          onAction={() => setComposing(true)}
        />
      ) : (
        <>
          {/* Upcoming */}
          {upcoming.length > 0 && (
            <div className="space-y-2">
              <h2 className="text-xs font-medium uppercase tracking-wider text-zinc-400">
                Upcoming
              </h2>
              {upcoming.map((d) => (
                <DateCard
                  key={d.id}
                  item={d}
                  onUpdate={handleUpdate}
                  onDelete={handleDelete}
                />
              ))}
            </div>
          )}

          {/* Past */}
          {past.length > 0 && (
            <div className="space-y-2">
              <h2 className="text-xs font-medium uppercase tracking-wider text-zinc-500">
                Past
              </h2>
              {past.map((d) => (
                <DateCard
                  key={d.id}
                  item={d}
                  onUpdate={handleUpdate}
                  onDelete={handleDelete}
                />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
