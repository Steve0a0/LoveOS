"use client";

import { useAuth } from "@/lib/auth-context";
import { apiFetch } from "@/lib/api";
import { useRouter } from "next/navigation";
import { useState } from "react";

export default function PairPage() {
  const { user, refetchUser } = useAuth();
  const router = useRouter();
  const [coupleName, setCoupleName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  // Already paired — redirect
  if (user?.couple_id) {
    router.replace("/dashboard");
    return null;
  }

  async function handleCreate(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      const res = await apiFetch("/couples/create/", {
        method: "POST",
        body: JSON.stringify({ name: coupleName }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to create couple.");
      await refetchUser();
      router.push("/pair/invite");
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-1 items-center justify-center bg-black">
      <div className="w-full max-w-sm space-y-6 px-4">
        <div className="text-center">
          <h1 className="text-2xl font-semibold text-white">Start your couple</h1>
          <p className="mt-1 text-sm text-zinc-400">
            Give your couple a name, then invite your partner.
          </p>
        </div>

        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label htmlFor="coupleName" className="block text-sm text-zinc-300">
              Couple name (optional)
            </label>
            <input
              id="coupleName"
              type="text"
              value={coupleName}
              onChange={(e) => setCoupleName(e.target.value)}
              className="mt-1 w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-white placeholder-zinc-500 focus:border-white focus:outline-none"
              placeholder="e.g. Us ❤️"
            />
          </div>

          {error && <p className="text-sm text-red-400">{error}</p>}

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-md bg-white px-4 py-2 text-sm font-medium text-black transition-colors hover:bg-zinc-200 disabled:opacity-50"
          >
            {submitting ? "Creating…" : "Create couple"}
          </button>
        </form>
      </div>
    </div>
  );
}
