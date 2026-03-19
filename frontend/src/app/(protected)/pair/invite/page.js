"use client";

import { useAuth } from "@/lib/auth-context";
import { apiFetch } from "@/lib/api";
import { useRouter } from "next/navigation";
import { useState } from "react";

export default function InvitePage() {
  const { user } = useAuth();
  const router = useRouter();
  const [inviteLink, setInviteLink] = useState("");
  const [partnerEmail, setPartnerEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  if (!user?.couple_id) {
    router.replace("/pair");
    return null;
  }

  async function handleGenerate(e) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await apiFetch("/invites/create/", {
        method: "POST",
        body: JSON.stringify({ email: partnerEmail }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to create invite.");
      setInviteLink(data.invite_link);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleCopy() {
    await navigator.clipboard.writeText(inviteLink);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="flex flex-1 items-center justify-center bg-zinc-950">
      <div className="w-full max-w-sm space-y-6 px-4">
        <div className="text-center">
          <h1 className="text-2xl font-semibold text-white">Invite your partner</h1>
          <p className="mt-1 text-sm text-zinc-400">
            Generate an invite link to share with your partner.
          </p>
        </div>

        {!inviteLink ? (
          <form onSubmit={handleGenerate} className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm text-zinc-300">
                Partner&apos;s email (optional)
              </label>
              <input
                id="email"
                type="email"
                value={partnerEmail}
                onChange={(e) => setPartnerEmail(e.target.value)}
                className="mt-1 w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-white placeholder-zinc-500 focus:border-white focus:outline-none"
                placeholder="partner@example.com"
              />
            </div>

            {error && <p className="text-sm text-red-400">{error}</p>}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-md bg-white px-4 py-2 text-sm font-medium text-black transition-colors hover:bg-zinc-200 disabled:opacity-50"
            >
              {loading ? "Generating…" : "Generate invite link"}
            </button>
          </form>
        ) : (
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-zinc-300 mb-1">
                Invite link
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={inviteLink}
                  readOnly
                  className="flex-1 rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-white"
                />
                <button
                  onClick={handleCopy}
                  className="rounded-md bg-zinc-800 px-3 py-2 text-sm text-white hover:bg-zinc-700"
                >
                  {copied ? "Copied!" : "Copy"}
                </button>
              </div>
            </div>

            <p className="text-xs text-zinc-500">
              This link expires in 7 days. Share it with your partner — they&apos;ll
              need to create an account and open this link to join.
            </p>

            <button
              onClick={() => router.push("/dashboard")}
              className="w-full rounded-md border border-zinc-700 px-4 py-2 text-sm text-zinc-300 hover:border-zinc-500"
            >
              Go to dashboard
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
