"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch } from "@/lib/api";
import EmptyState from "@/components/empty-state";
import { MapPinIcon } from "@/components/icons";

const DURATION_OPTIONS = [
  { value: 15, label: "15 min" },
  { value: 30, label: "30 min" },
  { value: 60, label: "1 hour" },
  { value: 120, label: "2 hours" },
];

const UPDATE_INTERVAL = 15_000; // 15 seconds

function formatRemaining(seconds) {
  if (!seconds || seconds <= 0) return "Expired";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function formatTime(dateStr) {
  return new Date(dateStr).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

/* ------------------------------------------------------------------ */
/*  Simple map — renders a marker on an embedded OSM iframe           */
/* ------------------------------------------------------------------ */
function SimpleMap({ lat, lng, updatedAt, label }) {
  const src = `https://www.openstreetmap.org/export/embed.html?bbox=${lng - 0.005},${lat - 0.005},${Number(lng) + 0.005},${Number(lat) + 0.005}&layer=mapnik&marker=${lat},${lng}`;
  return (
    <div className="overflow-hidden rounded-xl border border-zinc-800">
      {label && (
        <div className="bg-zinc-900 px-3 py-1.5 text-xs font-medium text-zinc-300">
          {label}
        </div>
      )}
      <iframe
        title="Location"
        width="100%"
        height="300"
        src={src}
        className="border-0"
        loading="lazy"
      />
      <div className="flex items-center justify-between bg-zinc-900 px-3 py-2 text-xs text-zinc-400">
        <span>📍 {Number(lat).toFixed(4)}, {Number(lng).toFixed(4)}</span>
        {updatedAt && <span>Updated {formatTime(updatedAt)}</span>}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Duration picker                                                   */
/* ------------------------------------------------------------------ */
function DurationPicker({ onStart, starting }) {
  const [selected, setSelected] = useState(30);
  return (
    <div className="flex flex-col items-center gap-4 rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
      <p className="text-sm text-zinc-400">Choose sharing duration</p>
      <div className="flex gap-2">
        {DURATION_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => setSelected(opt.value)}
            className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
              selected === opt.value
                ? "bg-purple-600 text-white"
                : "border border-zinc-700 text-zinc-300 hover:border-purple-500/40"
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>
      <button
        disabled={starting}
        onClick={() => onStart(selected)}
        className="rounded-lg bg-purple-600 px-6 py-2 text-sm font-medium text-white transition-colors hover:bg-purple-500 disabled:opacity-50"
      >
        {starting ? "Starting…" : "Share my location"}
      </button>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  My sharing status bar                                             */
/* ------------------------------------------------------------------ */
function MySharingBar({ session, onStop, stopping, remaining }) {
  return (
    <div className="flex items-center justify-between rounded-xl border border-emerald-800/40 bg-emerald-950/30 px-4 py-3">
      <div className="flex items-center gap-2">
        <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" />
        <span className="text-sm font-medium text-emerald-400">
          You're sharing your location
        </span>
        <span className="text-xs text-zinc-500">
          {formatRemaining(remaining)} left
        </span>
      </div>
      <button
        disabled={stopping}
        onClick={onStop}
        className="rounded-lg border border-red-800/60 bg-red-950/30 px-3 py-1.5 text-xs font-medium text-red-400 transition-colors hover:bg-red-900/40 disabled:opacity-50"
      >
        {stopping ? "Stopping…" : "Stop"}
      </button>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Partner's location panel                                          */
/* ------------------------------------------------------------------ */
function PartnerLocation({ session }) {
  const point = session.latest_point;
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <span className="h-2 w-2 animate-pulse rounded-full bg-sky-400" />
        <span className="text-sm font-medium text-sky-400">
          {session.started_by} is sharing their location
        </span>
        <span className="text-xs text-zinc-500">
          {formatRemaining(session.time_remaining)} left
        </span>
      </div>
      {point ? (
        <SimpleMap
          lat={point.latitude}
          lng={point.longitude}
          updatedAt={point.recorded_at}
          label={`${session.started_by}'s location`}
        />
      ) : (
        <div className="flex h-48 items-center justify-center rounded-xl border border-zinc-800 bg-zinc-900/50">
          <p className="text-sm text-zinc-500">Waiting for first location…</p>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main page                                                         */
/* ------------------------------------------------------------------ */
export default function LiveLocationPage() {
  const [mySession, setMySession] = useState(null);
  const [partnerSession, setPartnerSession] = useState(null);
  const [loaded, setLoaded] = useState(false);
  const [starting, setStarting] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [myRemaining, setMyRemaining] = useState(null);
  const watchRef = useRef(null);
  const intervalRef = useRef(null);
  const countdownRef = useRef(null);
  const pollRef = useRef(null);
  const sessionIdRef = useRef(null);

  /* ---------- fetch current session state ---------- */
  const fetchCurrent = useCallback(async () => {
    try {
      const res = await apiFetch("/location/current/");
      if (res.ok) {
        const data = await res.json();
        setMySession(data.my_session);
        setPartnerSession(data.partner_session);
        sessionIdRef.current = data.my_session?.id ?? null;
        if (data.my_session?.time_remaining != null) {
          setMyRemaining(data.my_session.time_remaining);
        } else {
          setMyRemaining(null);
        }
      }
    } catch {
      /* ignore */
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => {
    fetchCurrent();
  }, [fetchCurrent]);

  /* ---------- poll for partner updates ---------- */
  useEffect(() => {
    if (partnerSession || mySession) {
      pollRef.current = setInterval(fetchCurrent, UPDATE_INTERVAL);
    }
    return () => clearInterval(pollRef.current);
  }, [!!partnerSession, !!mySession, fetchCurrent]);

  /* ---------- countdown timer for my session ---------- */
  useEffect(() => {
    if (mySession && myRemaining != null && myRemaining > 0) {
      countdownRef.current = setInterval(() => {
        setMyRemaining((prev) => {
          if (prev <= 1) {
            clearInterval(countdownRef.current);
            setMySession(null);
            cleanupWatcher();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(countdownRef.current);
  }, [!!mySession, myRemaining != null]); // eslint-disable-line react-hooks/exhaustive-deps

  /* ---------- geolocation watcher ---------- */
  const sendPosition = useCallback(
    async (pos) => {
      const sid = sessionIdRef.current;
      if (!sid) return;
      try {
        const res = await apiFetch("/location/update/", {
          method: "POST",
          body: JSON.stringify({
            session_id: sid,
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
            accuracy: pos.coords.accuracy,
          }),
        });
        if (res.ok) fetchCurrent();
      } catch {
        /* ignore */
      }
    },
    [fetchCurrent]
  );

  const startWatcher = useCallback(() => {
    if (!navigator.geolocation) return;
    // Send an immediate position right away
    navigator.geolocation.getCurrentPosition(
      (pos) => sendPosition(pos),
      () => {},
      { enableHighAccuracy: true, maximumAge: 10_000 }
    );
    watchRef.current = navigator.geolocation.watchPosition(
      (pos) => sendPosition(pos),
      () => {},
      { enableHighAccuracy: true, maximumAge: 10_000 }
    );
    intervalRef.current = setInterval(() => {
      navigator.geolocation.getCurrentPosition(
        (pos) => sendPosition(pos),
        () => {},
        { enableHighAccuracy: true, maximumAge: 10_000 }
      );
    }, UPDATE_INTERVAL);
  }, [sendPosition]);

  const cleanupWatcher = useCallback(() => {
    if (watchRef.current != null) {
      navigator.geolocation.clearWatch(watchRef.current);
      watchRef.current = null;
    }
    clearInterval(intervalRef.current);
    intervalRef.current = null;
  }, []);

  // Start watcher when I have an active session
  useEffect(() => {
    if (mySession) {
      startWatcher();
    }
    return () => cleanupWatcher();
  }, [mySession?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  /* ---------- handlers ---------- */
  const handleStart = async (durationMinutes) => {
    setStarting(true);
    try {
      const res = await apiFetch("/location/start/", {
        method: "POST",
        body: JSON.stringify({ duration_minutes: durationMinutes }),
      });
      if (res.ok) {
        const data = await res.json();
        sessionIdRef.current = data.id;
        setMySession(data);
        setMyRemaining(data.time_remaining);
      }
    } catch {
      /* ignore */
    } finally {
      setStarting(false);
    }
  };

  const handleStop = async () => {
    setStopping(true);
    try {
      const res = await apiFetch("/location/stop/", { method: "POST" });
      if (res.ok) {
        sessionIdRef.current = null;
        setMySession(null);
        setMyRemaining(null);
        cleanupWatcher();
      }
    } catch {
      /* ignore */
    } finally {
      setStopping(false);
    }
  };

  /* ---------- render ---------- */
  if (!loaded) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-purple-500 border-t-transparent" />
      </div>
    );
  }

  const hasAnyActivity = mySession || partnerSession;

  return (
    <div className="flex flex-1 flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold">Live Location</h1>
        <p className="mt-1 text-sm text-zinc-400">
          Real-time location sharing
        </p>
      </div>

      {/* My sharing status */}
      {mySession && (
        <MySharingBar
          session={mySession}
          onStop={handleStop}
          stopping={stopping}
          remaining={myRemaining}
        />
      )}

      {/* Partner's location */}
      {partnerSession && <PartnerLocation session={partnerSession} />}

      {/* Start sharing (always visible when I'm not sharing) */}
      {!mySession && (
        <DurationPicker onStart={handleStart} starting={starting} />
      )}

      {/* Empty state — only when nobody is sharing */}
      {!hasAnyActivity && (
        <EmptyState
          icon={<MapPinIcon className="h-7 w-7" />}
          title="No active session"
          description="Start a live location session so your partner can see where you are in real time. Sessions are temporary and privacy-first."
        />
      )}
    </div>
  );
}
