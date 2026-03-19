import { memo } from "react";
import Link from "next/link";

const EmptyState = memo(function EmptyState({ icon, title, description, actionLabel, actionHref, onAction }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center py-16 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-zinc-900 text-zinc-500">
        {icon}
      </div>
      <h2 className="mt-4 text-lg font-medium text-white">{title}</h2>
      <p className="mt-1 max-w-xs text-sm text-zinc-400">{description}</p>
      {actionLabel && actionHref && (
        <Link
          href={actionHref}
          className="mt-5 inline-flex items-center rounded-md bg-white px-4 py-2 text-sm font-medium text-black transition-colors hover:bg-zinc-200"
        >
          {actionLabel}
        </Link>
      )}
      {actionLabel && onAction && !actionHref && (
        <button
          onClick={onAction}
          className="mt-5 inline-flex items-center rounded-md bg-white px-4 py-2 text-sm font-medium text-black transition-colors hover:bg-zinc-200"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
});

export default EmptyState;
