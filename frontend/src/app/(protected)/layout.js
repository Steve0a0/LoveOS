"use client";

import { useAuth } from "@/lib/auth-context";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { memo, useEffect, useMemo } from "react";
import {
  HomeIcon,
  PencilIcon,
  PhotoIcon,
  CalendarIcon,
  ShieldCheckIcon,
  MapPinIcon,
  CogIcon,
  HeartIcon,
} from "@/components/icons";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Home", icon: HomeIcon },
  { href: "/notes", label: "Notes", icon: PencilIcon },
  { href: "/timeline", label: "Timeline", icon: PhotoIcon },
  { href: "/dates", label: "Dates", icon: CalendarIcon },
  { href: "/safe-check", label: "Safety", icon: ShieldCheckIcon },
  { href: "/live-location", label: "Location", icon: MapPinIcon },
  { href: "/settings", label: "Settings", icon: CogIcon },
];

const MOBILE_NAV = [
  NAV_ITEMS[0], // Home
  NAV_ITEMS[1], // Notes
  NAV_ITEMS[2], // Timeline
  NAV_ITEMS[3], // Dates
  NAV_ITEMS[6], // Settings
];

function getIsActive(href, pathname) {
  if (href === "/dashboard") return pathname === "/dashboard";
  return pathname.startsWith(href);
}

const TopBar = memo(function TopBar({ displayName, pathname, onLogout }) {
  return (
    <header className="flex items-center justify-between border-b border-zinc-800 px-4 py-3">
      <Link href="/dashboard" className="flex items-center gap-2">
        <HeartIcon className="h-5 w-5 text-purple-400" />
        <span className="text-lg font-semibold">LoveOS</span>
      </Link>

      <nav className="hidden items-center gap-1 md:flex">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const active = getIsActive(item.href, pathname);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm transition-colors ${
                active
                  ? "bg-zinc-800 text-white"
                  : "text-zinc-400 hover:bg-zinc-900 hover:text-white"
              }`}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="flex items-center gap-3">
        <span className="hidden text-sm text-zinc-400 sm:inline">
          {displayName}
        </span>
        <button
          onClick={onLogout}
          className="text-sm text-zinc-500 hover:text-white"
        >
          Log out
        </button>
      </div>
    </header>
  );
});

const BottomNav = memo(function BottomNav({ pathname }) {
  return (
    <nav className="fixed inset-x-0 bottom-0 z-50 border-t border-zinc-800 bg-zinc-950/95 backdrop-blur-sm md:hidden">
      <div className="flex items-center justify-around py-2">
        {MOBILE_NAV.map((item) => {
          const Icon = item.icon;
          const active = getIsActive(item.href, pathname);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex flex-col items-center gap-0.5 px-3 py-1 ${
                active ? "text-white" : "text-zinc-500"
              }`}
            >
              <Icon className="h-5 w-5" />
              <span className="text-[10px]">{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
});

export default function ProtectedLayout({ children }) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center bg-zinc-950">
        <p className="text-zinc-400">Loading…</p>
      </div>
    );
  }

  if (!user) return null;

  const paired = user.couple_id !== null;

  return (
    <div className="flex flex-1 flex-col bg-zinc-950 text-white">
      <TopBar
        displayName={user.display_name}
        pathname={pathname}
        onLogout={logout}
      />

      {!paired && (
        <div className="border-b border-yellow-800 bg-yellow-950 px-4 py-2 text-center text-sm text-yellow-300">
          You&apos;re not paired yet.{" "}
          <Link href="/pair" className="underline">
            Pair with your partner
          </Link>{" "}
          to get started.
        </div>
      )}

      <main className="flex flex-1 flex-col overflow-y-auto p-4 pb-20 md:p-8 md:pb-8">
        {children}
      </main>

      <BottomNav pathname={pathname} />
    </div>
  );
}
