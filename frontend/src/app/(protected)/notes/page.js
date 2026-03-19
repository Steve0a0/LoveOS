"use client";

import { useAuth } from "@/lib/auth-context";
import { apiFetch } from "@/lib/api";
import { useEffect, useState, useCallback } from "react";
import EmptyState from "@/components/empty-state";
import { PencilIcon, PlusIcon, TrashIcon, ArrowLeftIcon } from "@/components/icons";

const OPEN_WHEN_OPTIONS = [
  { value: "normal", label: "Normal" },
  { value: "open_when_sad", label: "Open when sad" },
  { value: "open_when_happy", label: "Open when happy" },
  { value: "open_when_miss_me", label: "Open when you miss me" },
];

const OPEN_WHEN_LABELS = Object.fromEntries(
  OPEN_WHEN_OPTIONS.map((o) => [o.value, o.label])
);

const QUICK_EMOJIS = ["❤️", "😍", "🥺", "😂", "🤗", "💋", "🥰", "😘", "💕", "👏", "🔥", "✨"];

// ---------------------------------------------------------------------------
// Note composer (create + edit)
// ---------------------------------------------------------------------------
function NoteComposer({ initial, onSaved, onCancel }) {
  const [title, setTitle] = useState(initial?.title || "");
  const [body, setBody] = useState(initial?.body || "");
  const [openWhen, setOpenWhen] = useState(initial?.open_when_type || "normal");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const isEdit = !!initial?.id;

  async function handleSubmit(e) {
    e.preventDefault();
    if (!body.trim()) return;
    setSubmitting(true);
    setError("");
    try {
      const url = isEdit ? `/notes/${initial.id}/` : "/notes/";
      const method = isEdit ? "PATCH" : "POST";
      const res = await apiFetch(url, {
        method,
        body: JSON.stringify({ title, body, open_when_type: openWhen }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Failed to save note.");
      }
      const note = await res.json();
      onSaved(note);
    } catch (err) {
      setError(err.message);
    } finally {
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
        placeholder="Title (optional)"
        className="w-full bg-transparent text-white text-sm placeholder-zinc-500 outline-none"
        autoFocus={isEdit}
      />
      <textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder="Write something for your partner…"
        rows={4}
        className="w-full bg-transparent text-white text-sm placeholder-zinc-500 outline-none resize-none"
        autoFocus={!isEdit}
      />
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={openWhen}
          onChange={(e) => setOpenWhen(e.target.value)}
          className="rounded-md border border-zinc-700 bg-zinc-800 px-2 py-1 text-xs text-zinc-300"
        >
          {OPEN_WHEN_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <div className="ml-auto flex gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-md px-3 py-1.5 text-xs text-zinc-400 hover:text-white"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting || !body.trim()}
            className="rounded-md bg-white px-3 py-1.5 text-xs font-medium text-black hover:bg-zinc-200 disabled:opacity-50"
          >
            {submitting ? "Saving…" : isEdit ? "Update" : "Save note"}
          </button>
        </div>
      </div>
      {error && <p className="text-xs text-red-400">{error}</p>}
    </form>
  );
}

// ---------------------------------------------------------------------------
// Comment composer (text + emoji + GIF)
// ---------------------------------------------------------------------------
function CommentComposer({ noteId, onCreated }) {
  const [body, setBody] = useState("");
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  const [showGifInput, setShowGifInput] = useState(false);
  const [gifUrl, setGifUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function submitComment(type, text, gif) {
    setSubmitting(true);
    setError("");
    try {
      const res = await apiFetch(`/notes/${noteId}/comments/`, {
        method: "POST",
        body: JSON.stringify({
          content_type: type,
          body: text,
          gif_url: gif || "",
        }),
      });
      if (!res.ok) {
        const d = await res.json();
        throw new Error(d.detail || d.body?.[0] || "Failed to post comment.");
      }
      const comment = await res.json();
      onCreated(comment);
      setBody("");
      setGifUrl("");
      setShowGifInput(false);
      setShowEmojiPicker(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  function handleSendEmoji(emoji) {
    submitComment("emoji", emoji, "");
  }

  function handleInsertEmoji(emoji) {
    setBody((prev) => prev + emoji);
    setShowEmojiPicker(false);
  }

  async function handleSubmitText(e) {
    e.preventDefault();
    if (!body.trim()) return;
    await submitComment("text", body, "");
  }

  async function handleSubmitGif() {
    if (!gifUrl.trim()) return;
    await submitComment("gif", "GIF", gifUrl.trim());
  }

  return (
    <div className="space-y-2">
      <form onSubmit={handleSubmitText} className="flex items-end gap-2">
        <div className="flex-1 relative">
          <input
            type="text"
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Reply to this note…"
            className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-white placeholder-zinc-500 outline-none focus:border-zinc-500 pr-20"
            disabled={submitting}
          />
          <div className="absolute right-2 top-1/2 -translate-y-1/2 flex gap-1">
            <button
              type="button"
              onClick={() => {
                setShowEmojiPicker(!showEmojiPicker);
                setShowGifInput(false);
              }}
              className="text-zinc-500 hover:text-yellow-400 text-sm px-1"
              title="Emoji"
            >
              😊
            </button>
            <button
              type="button"
              onClick={() => {
                setShowGifInput(!showGifInput);
                setShowEmojiPicker(false);
              }}
              className="text-[10px] font-bold text-zinc-500 hover:text-purple-400 px-1 border border-zinc-600 rounded"
              title="GIF"
            >
              GIF
            </button>
          </div>
        </div>
        <button
          type="submit"
          disabled={submitting || !body.trim()}
          className="rounded-lg bg-white px-3 py-2 text-xs font-medium text-black hover:bg-zinc-200 disabled:opacity-50 shrink-0"
        >
          {submitting ? "…" : "Send"}
        </button>
      </form>

      {/* Quick emoji picker */}
      {showEmojiPicker && (
        <div className="rounded-lg bg-zinc-800 border border-zinc-700 p-3 space-y-2">
          <p className="text-[10px] text-zinc-500 uppercase tracking-wider">Quick react (sends immediately)</p>
          <div className="flex flex-wrap gap-2">
            {QUICK_EMOJIS.map((emoji) => (
              <button
                key={emoji}
                onClick={() => handleSendEmoji(emoji)}
                className="text-xl hover:scale-125 transition-transform"
              >
                {emoji}
              </button>
            ))}
          </div>
          <p className="text-[10px] text-zinc-500 uppercase tracking-wider pt-1">Insert into text</p>
          <div className="flex flex-wrap gap-2">
            {QUICK_EMOJIS.map((emoji) => (
              <button
                key={`i-${emoji}`}
                onClick={() => handleInsertEmoji(emoji)}
                className="text-lg hover:scale-110 transition-transform opacity-60 hover:opacity-100"
              >
                {emoji}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* GIF input */}
      {showGifInput && (
        <div className="rounded-lg bg-zinc-800 border border-zinc-700 p-3 space-y-3">
          <p className="text-xs font-medium text-zinc-300">Send a GIF</p>
          <p className="text-[10px] text-zinc-500">
            Copy a GIF URL from Giphy, Tenor, or any image URL
          </p>
          <input
            type="url"
            value={gifUrl}
            onChange={(e) => setGifUrl(e.target.value)}
            placeholder="Paste a GIF URL here…"
            className="w-full rounded-md bg-zinc-900 border border-zinc-700 px-3 py-1.5 text-xs text-white placeholder-zinc-500 outline-none focus:border-zinc-500"
          />
          {gifUrl.trim().startsWith("http") && (
            <div className="space-y-2">
              <img
                src={gifUrl.trim()}
                alt="GIF preview"
                className="max-h-32 rounded-md"
                onError={(e) => (e.target.style.display = "none")}
              />
              <button
                onClick={handleSubmitGif}
                disabled={submitting}
                className="rounded-md bg-white px-3 py-1.5 text-xs font-medium text-black hover:bg-zinc-200 disabled:opacity-50"
              >
                {submitting ? "Sending…" : "Send GIF"}
              </button>
            </div>
          )}
          <button
            onClick={() => setShowGifInput(false)}
            className="text-[10px] text-zinc-500 hover:text-white"
          >
            Cancel
          </button>
        </div>
      )}

      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Comment display
// ---------------------------------------------------------------------------
function CommentItem({ comment, onDelete }) {
  const [deleting, setDeleting] = useState(false);

  if (comment.content_type === "emoji") {
    return (
      <div className="group flex items-center gap-2 py-1.5">
        <span className="text-2xl">{comment.body}</span>
        <span className="text-[10px] text-zinc-600">
          {comment.author_name} · {new Date(comment.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </span>
        <button
          onClick={() => { setDeleting(true); onDelete(comment.id); }}
          disabled={deleting}
          className="text-zinc-700 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
        >
          <TrashIcon className="h-3 w-3" />
        </button>
      </div>
    );
  }

  if (comment.content_type === "gif") {
    return (
      <div className="group space-y-1 py-1.5">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-medium text-zinc-400">{comment.author_name}</span>
          <span className="text-[10px] text-zinc-600">
            {new Date(comment.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </span>
          <button
            onClick={() => { setDeleting(true); onDelete(comment.id); }}
            disabled={deleting}
            className="text-zinc-700 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <TrashIcon className="h-3 w-3" />
          </button>
        </div>
        {comment.gif_url && (
          <img
            src={comment.gif_url}
            alt="GIF"
            className="max-h-40 rounded-lg"
            loading="lazy"
          />
        )}
      </div>
    );
  }

  // Text comment
  return (
    <div className="group flex items-start gap-2 py-1.5">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-medium text-zinc-400">{comment.author_name}</span>
          <span className="text-[10px] text-zinc-600">
            {new Date(comment.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </span>
        </div>
        <p className="text-sm text-zinc-300 whitespace-pre-wrap">{comment.body}</p>
      </div>
      <button
        onClick={() => { setDeleting(true); onDelete(comment.id); }}
        disabled={deleting}
        className="shrink-0 text-zinc-700 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity mt-1"
      >
        <TrashIcon className="h-3 w-3" />
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Note detail view (expanded note with edit + comments)
// ---------------------------------------------------------------------------
function NoteDetailView({ noteId, onBack, onNoteUpdated, onNoteDeleted }) {
  const [note, setNote] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const loadNote = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiFetch(`/notes/${noteId}/`);
      if (res.ok) setNote(await res.json());
    } catch { /* ignore */ }
    setLoading(false);
  }, [noteId]);

  useEffect(() => { loadNote(); }, [loadNote]);

  async function handlePin() {
    const res = await apiFetch(`/notes/${noteId}/`, {
      method: "PATCH",
      body: JSON.stringify({ is_pinned: !note.is_pinned }),
    });
    if (res.ok) {
      const updated = await res.json();
      setNote(updated);
      onNoteUpdated(updated);
    }
  }

  async function handleDelete() {
    setDeleting(true);
    const res = await apiFetch(`/notes/${noteId}/`, { method: "DELETE" });
    if (res.ok || res.status === 204) {
      onNoteDeleted(noteId);
      onBack();
    } else {
      setDeleting(false);
    }
  }

  function handleEditSaved(updated) {
    setNote((prev) => ({ ...prev, ...updated }));
    onNoteUpdated(updated);
    setEditing(false);
  }

  function handleCommentCreated(comment) {
    setNote((prev) => ({
      ...prev,
      comments: [...(prev.comments || []), comment],
      comment_count: (prev.comment_count || 0) + 1,
    }));
  }

  async function handleDeleteComment(commentId) {
    const res = await apiFetch(`/notes/${noteId}/comments/${commentId}/`, { method: "DELETE" });
    if (res.ok || res.status === 204) {
      setNote((prev) => ({
        ...prev,
        comments: (prev.comments || []).filter((c) => c.id !== commentId),
        comment_count: Math.max(0, (prev.comment_count || 0) - 1),
      }));
    }
  }

  if (loading) return <p className="text-sm text-zinc-500">Loading note…</p>;
  if (!note) return <p className="text-sm text-zinc-500">Note not found.</p>;

  const isOpenWhen = note.open_when_type && note.open_when_type !== "normal";

  return (
    <div className="flex flex-1 flex-col space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={onBack}
          className="flex items-center justify-center rounded-md border border-zinc-700 p-1.5 text-zinc-400 hover:text-white hover:border-zinc-500"
        >
          <ArrowLeftIcon className="h-4 w-4" />
        </button>
        <div className="flex-1 min-w-0">
          <h1 className="text-lg font-semibold text-white truncate">
            {note.title || "Note"}
          </h1>
          <p className="text-[10px] text-zinc-500">
            by {note.author_name} · {new Date(note.created_at).toLocaleDateString()}
          </p>
        </div>
        <div className="flex gap-1">
          <button
            onClick={() => setEditing(true)}
            title="Edit"
            className="rounded-md border border-zinc-700 p-1.5 text-zinc-400 hover:text-white hover:border-zinc-500"
          >
            <PencilIcon className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={handlePin}
            title={note.is_pinned ? "Unpin" : "Pin"}
            className={`rounded-md border border-zinc-700 px-2 py-1.5 text-xs transition-colors ${
              note.is_pinned
                ? "text-yellow-400 border-yellow-800/50 hover:text-yellow-300"
                : "text-zinc-400 hover:text-white hover:border-zinc-500"
            }`}
          >
            {note.is_pinned ? "📌" : "Pin"}
          </button>
          <button
            onClick={handleDelete}
            disabled={deleting}
            title="Delete"
            className="rounded-md border border-red-800/50 p-1.5 text-red-400 hover:text-red-300 hover:border-red-600 disabled:opacity-50"
          >
            <TrashIcon className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Edit mode */}
      {editing ? (
        <NoteComposer
          initial={note}
          onSaved={handleEditSaved}
          onCancel={() => setEditing(false)}
        />
      ) : (
        <>
          {/* Note body */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 space-y-2">
            {isOpenWhen && (
              <span className="inline-block rounded-full bg-zinc-800 px-2 py-0.5 text-[10px] text-zinc-400">
                {OPEN_WHEN_LABELS[note.open_when_type]}
              </span>
            )}
            <p className="text-sm text-zinc-200 whitespace-pre-wrap leading-relaxed">{note.body}</p>
            {note.updated_at !== note.created_at && (
              <p className="text-[10px] text-zinc-600 italic">
                edited {new Date(note.updated_at).toLocaleDateString()}
              </p>
            )}
          </div>

          {/* Comments / replies */}
          <div className="space-y-3">
            <h3 className="text-xs font-medium text-zinc-400 uppercase tracking-wider">
              Replies {note.comments?.length > 0 && `(${note.comments.length})`}
            </h3>

            {note.comments && note.comments.length > 0 && (
              <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-3 space-y-0.5 divide-y divide-zinc-800/50">
                {note.comments.map((comment) => (
                  <CommentItem
                    key={comment.id}
                    comment={comment}
                    onDelete={handleDeleteComment}
                  />
                ))}
              </div>
            )}

            <CommentComposer noteId={noteId} onCreated={handleCommentCreated} />
          </div>
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Note card (list view — click to open detail)
// ---------------------------------------------------------------------------
function NoteCard({ note, onClick }) {
  const isOpenWhen = note.open_when_type && note.open_when_type !== "normal";

  return (
    <button
      onClick={onClick}
      className="w-full text-left rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 space-y-2 transition-colors hover:border-zinc-600"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          {note.title && (
            <p className="text-sm font-medium text-white truncate">{note.title}</p>
          )}
          {isOpenWhen && (
            <span className="inline-block mt-0.5 rounded-full bg-zinc-800 px-2 py-0.5 text-[10px] text-zinc-400">
              {OPEN_WHEN_LABELS[note.open_when_type]}
            </span>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {note.is_pinned && <span className="text-xs">📌</span>}
          {(note.comment_count || 0) > 0 && (
            <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-[10px] text-zinc-400">
              💬 {note.comment_count}
            </span>
          )}
        </div>
      </div>
      <p className="text-sm text-zinc-300 whitespace-pre-wrap line-clamp-3">{note.body}</p>
      <p className="text-[10px] text-zinc-600">
        {note.author_name} · {new Date(note.created_at).toLocaleDateString()}
      </p>
    </button>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function NotesPage() {
  const { user } = useAuth();
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [composing, setComposing] = useState(false);
  const [activeNoteId, setActiveNoteId] = useState(null);

  useEffect(() => {
    async function load() {
      try {
        const res = await apiFetch("/notes/");
        if (res.ok) setNotes(await res.json());
      } catch { /* ignore */ }
      finally { setLoading(false); }
    }
    load();
  }, []);

  function sortNotes(list) {
    return [...list].sort((a, b) => {
      if (a.is_pinned !== b.is_pinned) return b.is_pinned ? 1 : -1;
      return new Date(b.created_at) - new Date(a.created_at);
    });
  }

  function handleCreated(note) {
    setNotes((prev) => sortNotes([note, ...prev.filter((n) => n.id !== note.id)]));
    setComposing(false);
  }

  function handleNoteUpdated(updated) {
    setNotes((prev) =>
      sortNotes(prev.map((n) => (n.id === updated.id ? { ...n, ...updated } : n)))
    );
  }

  function handleNoteDeleted(id) {
    setNotes((prev) => prev.filter((n) => n.id !== id));
  }

  // Detail view
  if (activeNoteId) {
    return (
      <NoteDetailView
        noteId={activeNoteId}
        onBack={() => setActiveNoteId(null)}
        onNoteUpdated={handleNoteUpdated}
        onNoteDeleted={handleNoteDeleted}
      />
    );
  }

  return (
    <div className="flex flex-1 flex-col space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Notes</h1>
          <p className="mt-1 text-sm text-zinc-400">Shared notes with your partner</p>
        </div>
        {user?.couple_id && !composing && (
          <button
            onClick={() => setComposing(true)}
            className="flex items-center gap-1.5 rounded-md bg-white px-3 py-1.5 text-sm font-medium text-black hover:bg-zinc-200"
          >
            <PlusIcon className="h-4 w-4" />
            New note
          </button>
        )}
      </div>

      {/* Composer */}
      {composing && (
        <NoteComposer onSaved={handleCreated} onCancel={() => setComposing(false)} />
      )}

      {/* Notes list */}
      {loading ? (
        <p className="text-sm text-zinc-500">Loading notes…</p>
      ) : notes.length === 0 && !composing ? (
        <EmptyState
          icon={<PencilIcon className="h-7 w-7" />}
          title="Leave your first note"
          description="Write little notes for your partner — sweet nothings, reminders, or just a hello."
        />
      ) : (
        <div className="space-y-3">
          {notes.map((note) => (
            <NoteCard
              key={note.id}
              note={note}
              onClick={() => setActiveNoteId(note.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
