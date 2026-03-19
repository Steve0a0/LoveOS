"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { getPushPermission, subscribeToPush, registerServiceWorker } from "@/lib/push";
import Link from "next/link";

export default function PairingSuccessPage() {
  const { user } = useAuth();
  const [showNotifPrompt, setShowNotifPrompt] = useState(false);
  const [subscribed, setSubscribed] = useState(false);

  useEffect(() => {
    // Register SW eagerly, then show prompt if permission not yet decided
    registerServiceWorker();
    const perm = getPushPermission();
    if (perm === "default") {
      setShowNotifPrompt(true);
    }
  }, []);

  const handleEnable = async () => {
    const ok = await subscribeToPush();
    setSubscribed(ok);
    setShowNotifPrompt(false);
  };

  return (
    <div className="flex flex-1 items-center justify-center bg-black">
      <div className="w-full max-w-sm space-y-6 px-4 text-center">
        <div className="text-5xl">🎉</div>
        <h1 className="text-2xl font-semibold text-white">You&apos;re paired!</h1>
        <p className="text-zinc-400">
          Welcome to your shared space.
          {user?.display_name ? ` Hi, ${user.display_name}!` : ""}
        </p>

        {showNotifPrompt && !subscribed && (
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 space-y-3">
            <p className="text-sm text-white">
              🔔 Enable notifications so you never miss a message from your partner.
            </p>
            <div className="flex gap-2 justify-center">
              <button
                onClick={handleEnable}
                className="rounded-md bg-pink-600 px-4 py-2 text-sm font-medium text-white hover:bg-pink-500"
              >
                Enable notifications
              </button>
              <button
                onClick={() => setShowNotifPrompt(false)}
                className="rounded-md border border-zinc-700 px-4 py-2 text-sm text-zinc-400 hover:text-white"
              >
                Maybe later
              </button>
            </div>
          </div>
        )}

        {subscribed && (
          <p className="text-sm text-emerald-400">✓ Notifications enabled!</p>
        )}

        <Link
          href="/dashboard"
          className="inline-block w-full rounded-md bg-white px-4 py-2 text-sm font-medium text-black transition-colors hover:bg-zinc-200"
        >
          Go to dashboard
        </Link>
      </div>
    </div>
  );
}
