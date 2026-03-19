"use client";

import { useAuth } from "@/lib/auth-context";
import { apiFetch } from "@/lib/api";
import Link from "next/link";
import { useEffect, useState } from "react";
import {
  PencilIcon,
  PhotoIcon,
  CalendarIcon,
  ShieldCheckIcon,
  MapPinIcon,
  HeartIcon,
} from "@/components/icons";

const QUICK_ACTIONS = [
  { href: "/notes", label: "Notes", description: "Leave a note for your partner", icon: PencilIcon },
  { href: "/timeline", label: "Timeline", description: "Share a memory together", icon: PhotoIcon },
  { href: "/dates", label: "Dates", description: "Track important dates", icon: CalendarIcon },
  { href: "/safe-check", label: "Safety", description: "Check in with your partner", icon: ShieldCheckIcon },
  { href: "/live-location", label: "Location", description: "Share your live location", icon: MapPinIcon },
];

function DashCard({ icon, title, children, href }) {
  const Wrapper = href ? Link : "div";
  return (
    <Wrapper
      {...(href ? { href } : {})}
      className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 transition-colors hover:border-zinc-700"
    >
      <div className="mb-2 flex items-center gap-2 text-zinc-400">
        {icon}
        <span className="text-xs font-medium uppercase tracking-wider">{title}</span>
      </div>
      {children}
    </Wrapper>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const res = await apiFetch("/dashboard/");
        if (res.ok) setData(await res.json());
      } catch { /* ignore */ }
      finally { setLoading(false); }
    }
    load();
  }, []);

  return (
    <div className="space-y-8">
      {/* Greeting */}
      <div>
        <h1 className="text-2xl font-semibold">
          Hey{user?.display_name ? `, ${user.display_name}` : ""}
        </h1>
        <p className="mt-1 text-zinc-400">Welcome back to your shared space.</p>
      </div>

      {/* Not paired banner */}
      {!user?.couple_id && (
        <div className="rounded-xl border border-yellow-800/50 bg-yellow-950/30 p-5">
          <p className="text-sm text-yellow-300">
            You&apos;re not paired yet. Most features require a partner.{" "}
            <Link href="/pair" className="underline">Set up your couple</Link>
          </p>
        </div>
      )}

      {/* Dashboard cards */}
      {loading ? (
        <p className="text-zinc-500 text-sm">Loading dashboard…</p>
      ) : data?.paired ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {/* Relationship days */}
          <DashCard
            icon={<HeartIcon className="h-4 w-4 text-rose-500" />}
            title="Relationship"
          >
            {data.days_together !== null ? (
              <>
                <p className="text-3xl font-bold text-white">{data.days_together}</p>
                <p className="text-xs text-zinc-500">days together</p>
              </>
            ) : (
              <p className="text-sm text-zinc-500">
                No start date set.{" "}
                <Link href="/settings" className="text-zinc-300 underline">Add it</Link>
              </p>
            )}
          </DashCard>

          {/* Next date */}
          <DashCard
            icon={<CalendarIcon className="h-4 w-4" />}
            title="Next date"
            href="/dates"
          >
            {data.next_date ? (
              <>
                <p className="text-lg font-semibold text-white">{data.next_date.title}</p>
                <p className="text-xs text-zinc-500">
                  {data.next_date.days_away === 0
                    ? "Today!"
                    : data.next_date.days_away === 1
                    ? "Tomorrow"
                    : `Next ${data.next_date.date_type || "date"} in ${data.next_date.days_away} days`}
                  {" · "}
                  {data.next_date.date}
                </p>
              </>
            ) : (
              <p className="text-sm text-zinc-500">No upcoming dates</p>
            )}
          </DashCard>

          {/* Latest memory / photo */}
          <DashCard
            icon={<PhotoIcon className="h-4 w-4" />}
            title="Newest photo"
            href="/timeline"
          >
            {data.latest_memory ? (
              <>
                {(data.latest_memory.thumbnail || data.latest_memory.image) && (
                  <img
                    src={data.latest_memory.thumbnail || data.latest_memory.image}
                    alt={data.latest_memory.caption || "Memory"}
                    className="mb-2 h-24 w-full rounded-lg object-cover"
                  />
                )}
                <p className="text-sm text-zinc-300 truncate">
                  {data.latest_memory.caption || "Untitled memory"}
                </p>
                {data.latest_memory.uploaded_by && (
                  <p className="text-[10px] text-zinc-600">
                    by {data.latest_memory.uploaded_by}
                  </p>
                )}
              </>
            ) : (
              <p className="text-sm text-zinc-500">No memories yet</p>
            )}
          </DashCard>

          {/* Latest note */}
          <DashCard
            icon={<PencilIcon className="h-4 w-4" />}
            title="Latest note"
            href="/notes"
          >
            {data.latest_note ? (
              <>
                <p className="text-sm font-medium text-white truncate">
                  {data.latest_note.title || "Untitled"}
                </p>
                {data.latest_note.open_when_type && data.latest_note.open_when_type !== "normal" && (
                  <span className="inline-block mt-0.5 rounded-full bg-zinc-800 px-2 py-0.5 text-[10px] text-zinc-400">
                    {data.latest_note.open_when_type.replace(/_/g, " ")}
                  </span>
                )}
                <p className="mt-0.5 text-xs text-zinc-500 line-clamp-2">
                  {data.latest_note.body || "No content"}
                </p>
                <p className="mt-1 text-[10px] text-zinc-600">
                  {data.latest_note.is_pinned ? "📌 " : ""}by {data.latest_note.author}
                </p>
              </>
            ) : (
              <p className="text-sm text-zinc-500">No notes yet</p>
            )}
          </DashCard>

          {/* Safety status */}
          <DashCard
            icon={<ShieldCheckIcon className="h-4 w-4" />}
            title="Safety"
            href="/safe-check"
          >
            {data.latest_safe_check ? (
              <>
                <p className="text-sm text-white">
                  {data.latest_safe_check.status === "reached" ? (
                    <span className="text-emerald-400">Reached safely</span>
                  ) : data.latest_safe_check.status === "leaving" ? (
                    <span className="text-yellow-400">Leaving now</span>
                  ) : (
                    <span className="text-sky-400">Checked in</span>
                  )}
                </p>
                <p className="text-[10px] text-zinc-600">
                  by {data.latest_safe_check.triggered_by}
                </p>
              </>
            ) : (
              <p className="text-sm text-zinc-500">No check-ins yet</p>
            )}
          </DashCard>

          {/* Location status */}
          <DashCard
            icon={<MapPinIcon className="h-4 w-4" />}
            title="Live location"
            href="/live-location"
          >
            {data.active_location_session ? (
              <>
                <p className="text-sm text-emerald-400">Sharing active</p>
                <p className="text-[10px] text-zinc-600">
                  by {data.active_location_session.started_by}
                  {data.active_location_session.time_remaining != null &&
                    ` · ${Math.ceil(data.active_location_session.time_remaining / 60)}m left`}
                </p>
              </>
            ) : (
              <p className="text-sm text-zinc-500">No active session</p>
            )}
          </DashCard>
        </div>
      ) : null}

      {/* Quick actions */}
      <div>
        <h2 className="mb-3 text-sm font-medium text-zinc-400 uppercase tracking-wider">Quick actions</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {QUICK_ACTIONS.map((action) => {
            const Icon = action.icon;
            return (
              <Link
                key={action.href}
                href={action.href}
                className="group flex items-start gap-3 rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 transition-colors hover:border-zinc-700 hover:bg-zinc-900"
              >
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-zinc-800 text-zinc-400 group-hover:text-white">
                  <Icon className="h-4 w-4" />
                </div>
                <div>
                  <p className="text-sm font-medium text-white">{action.label}</p>
                  <p className="text-xs text-zinc-500">{action.description}</p>
                </div>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
