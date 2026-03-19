"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { apiFetch } from "@/lib/api";
import {
  getPushPermission,
  isPushSubscribed,
  subscribeToPush,
  unsubscribeFromPush,
} from "@/lib/push";
import Link from "next/link";

const NOTIF_CATEGORIES = [
  { key: "notes", label: "Notes", desc: "When your partner leaves a note" },
  { key: "memories", label: "Memories", desc: "When a new photo is added" },
  { key: "safety", label: "Safety", desc: "Safe check-in events" },
  { key: "location", label: "Location", desc: "When location sharing starts" },
];

const TIMEZONES = [
  "UTC",
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "America/Anchorage",
  "Pacific/Honolulu",
  "Europe/London",
  "Europe/Paris",
  "Europe/Berlin",
  "Europe/Moscow",
  "Asia/Dubai",
  "Asia/Kolkata",
  "Asia/Shanghai",
  "Asia/Tokyo",
  "Australia/Sydney",
  "Pacific/Auckland",
];

/* ------------------------------------------------------------------ */
/*  Toggle component                                                  */
/* ------------------------------------------------------------------ */
function Toggle({ checked, onChange, disabled }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ${
        checked ? "bg-purple-600" : "bg-zinc-700"
      } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
    >
      <span
        className={`pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow transition-transform duration-200 ${
          checked ? "translate-x-5" : "translate-x-0"
        }`}
      />
    </button>
  );
}

/* ------------------------------------------------------------------ */
/*  Inline editable field                                             */
/* ------------------------------------------------------------------ */
function EditableField({ label, value, onSave, type = "text", options }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value || "");
  const [saving, setSaving] = useState(false);

  useEffect(() => setDraft(value || ""), [value]);

  const handleSave = async () => {
    setSaving(true);
    await onSave(draft);
    setSaving(false);
    setEditing(false);
  };

  const handleCancel = () => {
    setDraft(value || "");
    setEditing(false);
  };

  return (
    <div className="flex items-center justify-between px-4 py-3">
      <span className="text-sm text-zinc-400">{label}</span>
      {editing ? (
        <div className="flex items-center gap-2">
          {options ? (
            <select
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              className="rounded border border-zinc-700 bg-zinc-800 px-2 py-1 text-sm text-white outline-none focus:border-purple-500"
            >
              {options.map((o) => (
                <option key={o} value={o}>
                  {o}
                </option>
              ))}
            </select>
          ) : (
            <input
              type={type}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              className="w-40 rounded border border-zinc-700 bg-zinc-800 px-2 py-1 text-sm text-white outline-none focus:border-purple-500"
            />
          )}
          <button
            onClick={handleSave}
            disabled={saving}
            className="text-xs text-purple-400 hover:text-purple-300 disabled:opacity-50"
          >
            Save
          </button>
          <button
            onClick={handleCancel}
            className="text-xs text-zinc-500 hover:text-zinc-300"
          >
            Cancel
          </button>
        </div>
      ) : (
        <button
          onClick={() => setEditing(true)}
          className="group flex items-center gap-1"
        >
          <span className="text-sm text-white">{value || "—"}</span>
          <span className="text-xs text-zinc-600 group-hover:text-zinc-400">✎</span>
        </button>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main settings page                                                */
/* ------------------------------------------------------------------ */
export default function SettingsPage() {
  const { user, refetchUser } = useAuth();

  // Push notification state
  const [pushEnabled, setPushEnabled] = useState(false);
  const [pushPermission, setPushPermission] = useState("default");

  // Notification + privacy preferences
  const [prefs, setPrefs] = useState({
    notes: true,
    memories: true,
    safety: true,
    location: true,
    location_share_enabled: true,
  });
  const [prefsLoaded, setPrefsLoaded] = useState(false);

  // Profile state
  const [displayName, setDisplayName] = useState("");
  const [timezone, setTimezone] = useState("UTC");

  // Couple state
  const [coupleData, setCoupleData] = useState(null);

  useEffect(() => {
    // Push status
    setPushPermission(getPushPermission());
    isPushSubscribed().then(setPushEnabled);

    // Notification preferences
    apiFetch("/notifications/preferences/").then(async (res) => {
      if (res.ok) setPrefs(await res.json());
      setPrefsLoaded(true);
    });

    // Profile settings
    apiFetch("/settings/profile/").then(async (res) => {
      if (res.ok) {
        const d = await res.json();
        setDisplayName(d.display_name || "");
        setTimezone(d.timezone || "UTC");
      }
    });

    // Couple settings
    apiFetch("/settings/couple/").then(async (res) => {
      if (res.ok) setCoupleData(await res.json());
    });
  }, []);

  /* ---- handlers ---- */
  const handlePushToggle = async (enable) => {
    if (enable) {
      const ok = await subscribeToPush();
      setPushEnabled(ok);
      setPushPermission(getPushPermission());
    } else {
      await unsubscribeFromPush();
      setPushEnabled(false);
    }
  };

  const handlePrefChange = useCallback(
    async (key, value) => {
      setPrefs((prev) => ({ ...prev, [key]: value }));
      await apiFetch("/notifications/preferences/", {
        method: "PATCH",
        body: JSON.stringify({ [key]: value }),
      });
    },
    []
  );

  const handleProfileSave = async (field, value) => {
    const res = await apiFetch("/settings/profile/", {
      method: "PATCH",
      body: JSON.stringify({ [field]: value }),
    });
    if (res.ok) {
      const updated = await res.json();
      setDisplayName(updated.display_name || "");
      setTimezone(updated.timezone || "UTC");
      refetchUser();
    }
  };

  const handleCoupleSave = async (field, value) => {
    const res = await apiFetch("/settings/couple/", {
      method: "PATCH",
      body: JSON.stringify({ [field]: value }),
    });
    if (res.ok) {
      setCoupleData(await res.json());
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">Settings</h1>
        <p className="mt-1 text-sm text-zinc-400">
          Manage your account and couple
        </p>
      </div>

      {/* ---- Profile ---- */}
      <section className="space-y-3">
        <h2 className="text-sm font-medium uppercase tracking-wider text-zinc-400">
          Profile
        </h2>
        <div className="divide-y divide-zinc-800 rounded-xl border border-zinc-800 bg-zinc-900/50">
          <EditableField
            label="Display name"
            value={displayName}
            onSave={(v) => handleProfileSave("display_name", v)}
          />
          <div className="flex items-center justify-between px-4 py-3">
            <span className="text-sm text-zinc-400">Email</span>
            <span className="text-sm text-white">{user?.email || "—"}</span>
          </div>
          <EditableField
            label="Timezone"
            value={timezone}
            onSave={(v) => handleProfileSave("timezone", v)}
            options={TIMEZONES}
          />
        </div>
      </section>

      {/* ---- Couple ---- */}
      <section className="space-y-3">
        <h2 className="text-sm font-medium uppercase tracking-wider text-zinc-400">
          Couple
        </h2>
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50">
          {user?.couple_id ? (
            <div className="divide-y divide-zinc-800">
              <div className="flex items-center justify-between px-4 py-3">
                <span className="text-sm text-zinc-400">Status</span>
                <span className="text-sm text-emerald-400">Paired</span>
              </div>
              {coupleData && (
                <>
                  <EditableField
                    label="Couple name"
                    value={coupleData.name}
                    onSave={(v) => handleCoupleSave("name", v)}
                  />
                  <EditableField
                    label="Anniversary"
                    value={coupleData.relationship_start_date || ""}
                    onSave={(v) =>
                      handleCoupleSave("relationship_start_date", v)
                    }
                    type="date"
                  />
                </>
              )}
              <div className="px-4 py-3">
                <Link
                  href="/pair/invite"
                  className="text-sm text-zinc-400 hover:text-white"
                >
                  Manage invite link &rarr;
                </Link>
              </div>
            </div>
          ) : (
            <div className="p-4 text-center">
              <p className="text-sm text-zinc-400">
                You&apos;re not paired yet.
              </p>
              <Link
                href="/pair"
                className="mt-2 inline-block text-sm text-white underline"
              >
                Pair with your partner
              </Link>
            </div>
          )}
        </div>
      </section>

      {/* ---- Notifications ---- */}
      <section className="space-y-3">
        <h2 className="text-sm font-medium uppercase tracking-wider text-zinc-400">
          Notifications
        </h2>
        <div className="divide-y divide-zinc-800 rounded-xl border border-zinc-800 bg-zinc-900/50">
          {/* Master push toggle */}
          <div className="flex items-center justify-between px-4 py-3">
            <div>
              <p className="text-sm text-white">Push notifications</p>
              <p className="text-xs text-zinc-500">
                {pushPermission === "denied"
                  ? "Blocked in browser settings"
                  : pushEnabled
                    ? "Enabled"
                    : "Disabled"}
              </p>
            </div>
            <Toggle
              checked={pushEnabled}
              onChange={handlePushToggle}
              disabled={pushPermission === "denied"}
            />
          </div>

          {/* Category toggles */}
          {prefsLoaded &&
            NOTIF_CATEGORIES.map((cat) => (
              <div
                key={cat.key}
                className="flex items-center justify-between px-4 py-3"
              >
                <div>
                  <p className="text-sm text-white">{cat.label}</p>
                  <p className="text-xs text-zinc-500">{cat.desc}</p>
                </div>
                <Toggle
                  checked={prefs[cat.key]}
                  onChange={(val) => handlePrefChange(cat.key, val)}
                />
              </div>
            ))}
        </div>
      </section>

      {/* ---- Privacy ---- */}
      <section className="space-y-3">
        <h2 className="text-sm font-medium uppercase tracking-wider text-zinc-400">
          Privacy
        </h2>
        <div className="divide-y divide-zinc-800 rounded-xl border border-zinc-800 bg-zinc-900/50">
          <div className="flex items-center justify-between px-4 py-3">
            <div>
              <p className="text-sm text-white">Location sharing</p>
              <p className="text-xs text-zinc-500">
                Allow your partner to see when you share location
              </p>
            </div>
            {prefsLoaded && (
              <Toggle
                checked={prefs.location_share_enabled}
                onChange={(val) =>
                  handlePrefChange("location_share_enabled", val)
                }
              />
            )}
          </div>
        </div>
      </section>

      {/* ---- Account ---- */}
      <section className="space-y-3">
        <h2 className="text-sm font-medium uppercase tracking-wider text-zinc-400">
          Account
        </h2>
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
          <p className="text-sm text-zinc-500">
            Account management options will appear here.
          </p>
        </div>
      </section>
    </div>
  );
}
