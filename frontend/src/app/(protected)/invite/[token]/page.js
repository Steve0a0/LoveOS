"use client";

import { useAuth } from "@/lib/auth-context";
import { apiFetch } from "@/lib/api";
import { useRouter, useParams } from "next/navigation";
import { useEffect, useState } from "react";

export default function AcceptInvitePage() {
  const { user, refetchUser } = useAuth();
  const router = useRouter();
  const params = useParams();
  const token = params.token;

  const [inviteInfo, setInviteInfo] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [accepting, setAccepting] = useState(false);

  useEffect(() => {
    if (!token) return;

    async function validate() {
      try {
        const res = await apiFetch(`/invites/${token}/`);
        const data = await res.json();
        if (!res.ok) {
          setError(data.detail || "This invite is not valid.");
        } else {
          setInviteInfo(data);
        }
      } catch {
        setError("Failed to validate invite.");
      } finally {
        setLoading(false);
      }
    }

    validate();
  }, [token]);

  async function handleAccept() {
    setError("");
    setAccepting(true);

    try {
      const res = await apiFetch(`/invites/${token}/accept/`, {
        method: "POST",
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to accept invite.");
      await refetchUser();
      router.push("/pair/success");
    } catch (err) {
      setError(err.message);
    } finally {
      setAccepting(false);
    }
  }

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center bg-black">
        <p className="text-zinc-400">Checking invite…</p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 items-center justify-center bg-black">
      <div className="w-full max-w-sm space-y-6 px-4 text-center">
        {error ? (
          <>
            <div>
              <h1 className="text-2xl font-semibold text-white">
                Invite not valid
              </h1>
              <p className="mt-2 text-sm text-red-400">{error}</p>
            </div>
            <button
              onClick={() => router.push("/dashboard")}
              className="w-full rounded-md border border-zinc-700 px-4 py-2 text-sm text-zinc-300 hover:border-zinc-500"
            >
              Go to dashboard
            </button>
          </>
        ) : (
          <>
            <div>
              <h1 className="text-2xl font-semibold text-white">
                You&apos;re invited!
              </h1>
              <p className="mt-2 text-zinc-400">
                <span className="text-white font-medium">
                  {inviteInfo.invited_by}
                </span>{" "}
                wants you to join
                {inviteInfo.couple_name
                  ? ` "${inviteInfo.couple_name}"`
                  : " their couple"}
                .
              </p>
            </div>

            <button
              onClick={handleAccept}
              disabled={accepting}
              className="w-full rounded-md bg-white px-4 py-2 text-sm font-medium text-black transition-colors hover:bg-zinc-200 disabled:opacity-50"
            >
              {accepting ? "Joining…" : "Accept & join"}
            </button>

            <button
              onClick={() => router.push("/dashboard")}
              className="w-full rounded-md border border-zinc-700 px-4 py-2 text-sm text-zinc-300 hover:border-zinc-500"
            >
              Not now
            </button>
          </>
        )}
      </div>
    </div>
  );
}
